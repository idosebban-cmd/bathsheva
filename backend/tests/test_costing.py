import math
import shutil

import pytest
import yaml
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.config import SEED_DIR
from app.costing.data import load_cost_data, load_cost_data_from
from app.costing.model import (
    Assumption,
    CostInputs,
    ItemSpec,
    PartGeometry,
    PartSpec,
    breakdown,
    evaluate,
    sensitivity,
    total,
    unit_cost_range,
)
from app.migrate import alembic_config
from app.rules.data import RulesDataError

# --- seed loader -----------------------------------------------------------------


def test_every_cost_seed_entry_has_provenance_and_is_unverified():
    for path in (SEED_DIR / "cost").glob("*.yaml"):
        (entries,) = yaml.safe_load(path.read_text()).values()
        for e in entries:
            assert e.get("source") and e.get("confidence") in ("low", "medium", "high"), (path.name, e)
            assert e.get("verified") is False, (path.name, e)
    data = load_cost_data()
    assert {"al_1050", "al_6061", "pmma"} <= set(data.material_prices)
    assert {"metal_spinning", "cnc_machining", "polymer_tube_cut"} <= set(data.process_rates)
    assert data.value("volume_table") == [100, 500, 2000]


def _copy(tmp_path):
    d = tmp_path / "cost"
    shutil.copytree(SEED_DIR / "cost", d)
    return d


def _edit(d, filename, fn):
    doc = yaml.safe_load((d / filename).read_text())
    fn(doc)
    (d / filename).write_text(yaml.safe_dump(doc))


def test_loader_rejects_missing_provenance(tmp_path):
    d = _copy(tmp_path)
    _edit(d, "material_prices.yaml", lambda doc: doc["material_prices"][0].pop("source"))
    with pytest.raises(RulesDataError, match="source"):
        load_cost_data_from(d)


def test_loader_rejects_inverted_range(tmp_path):
    d = _copy(tmp_path)
    _edit(d, "process_rates.yaml", lambda doc: doc["process_rates"][0].update(machine_gbp_per_hr={"low": 90, "high": 10}))
    with pytest.raises(RulesDataError, match="invalid range"):
        load_cost_data_from(d)


def test_loader_rejects_unknown_material(tmp_path):
    d = _copy(tmp_path)
    _edit(d, "material_prices.yaml", lambda doc: doc["material_prices"][0].update(material="unobtainium"))
    with pytest.raises(RulesDataError, match="unobtainium"):
        load_cost_data_from(d)


def test_loader_defaults_verified_false(tmp_path):
    d = _copy(tmp_path)
    _edit(d, "bought_in.yaml", lambda doc: doc["bought_in"][0].pop("verified"))
    assert load_cost_data_from(d).bought_in["led_module"].verified is False


# --- model arithmetic ------------------------------------------------------------


def A(key, low, high=None, confidence="high", verified=False):
    return Assumption(key, key, "", low, low if high is None else high, confidence, verified)


def simple_inputs(confidence="high", tooling=(1000, 1000), cnc=False):
    """One spun part: 100 cm3 of aluminium (2.7 g/cm3) = 0.27 kg, plus one bought-in item."""
    part = PartSpec(
        part_id=1, name="Cap", quantity=2, process_key="spin", process_name="Spinning", material_key="al",
        material_name="Al", density_g_cm3=2.7, geometry=PartGeometry(100_000, (100, 100, 50), True),
        finish_key="paint", finish_name="Paint", basis="recommended",
        cnc_allowance_mm=5 if cnc else None,
    )
    c = confidence
    assumptions = {a.key: a for a in [
        A("mat_price:al", 5, confidence=c), A("rate:spin", 60, confidence=c), A("setup:spin", 2, confidence=c),
        A("cycle:spin", 6, confidence=c), A("cycle_kg:spin", 10, confidence=c), A("util:spin", 1.5, confidence=c),
        A("removal:spin", 0.02, confidence=c),
        A("finish_m2:paint", 50, confidence=c), A("finish_min:paint", 1, confidence=c),
        A("tooling:1", *tooling, confidence=c), A("item:9", 4, confidence=c),
    ]}
    items = [ItemSpec(9, "bought_in", "LED", 1, "pcs", "item:9")]
    return CostInputs(assumptions=assumptions, parts=[part], items=items)


def by_cat(lines):
    out = {}
    for ln in lines:
        out[ln.category] = out.get(ln.category, 0) + ln.amount
    return out


def test_part_cost_lines_by_hand():
    inp = simple_inputs()
    cats = by_cat(evaluate(inp, inp.mids(), 100))
    kg = 100 * 2.7 / 1000  # 0.27 kg finished
    assert cats["material"] == pytest.approx(2 * kg * 1.5 * 5)  # x2 per product, 1.5 utilisation, £5/kg
    assert cats["process"] == pytest.approx(2 * (6 + kg * 10) * 60 / 60)
    assert cats["setup"] == pytest.approx(2 * 60 / 100)  # 2 h x £60 shared across 100
    area = (math.pi * 100 * 50 + math.pi * 50**2) / 1e6
    assert cats["finishing"] == pytest.approx(2 * max(1, area * 50))
    assert cats["tooling"] == pytest.approx(1000 / 100)  # one tool per design, not per piece
    assert cats["bought_in"] == pytest.approx(4)


def test_cnc_material_uses_stock_not_part_volume():
    inp = simple_inputs(cnc=True)
    lines = evaluate(inp, inp.mids(), 100)
    stock_cm3 = math.pi / 4 * 105**2 * 55 / 1000
    assert by_cat(lines)["material"] == pytest.approx(2 * stock_cm3 * 2.7 / 1000 * 5)
    removed = stock_cm3 - 100
    assert by_cat(lines)["process"] == pytest.approx(2 * (6 + removed * 0.02) * 60 / 60)


def test_tooling_and_setup_amortise_over_quantity():
    inp = simple_inputs(tooling=(5000, 5000))
    t100 = total(evaluate(inp, inp.mids(), 100))
    t1000 = total(evaluate(inp, inp.mids(), 1000))
    one_off = 5000 + 2 * 60  # tooling + setup (2 h x £60)
    assert t100 - t1000 == pytest.approx(one_off * (1 / 100 - 1 / 1000))
    cats = by_cat(evaluate(inp, inp.mids(), 2000))
    assert cats["tooling"] == pytest.approx(2.5) and cats["setup"] == pytest.approx(0.06)
    # Per-unit cost falls with volume; material/process do not.
    mids = [unit_cost_range(inp, q)["mid"] for q in (100, 500, 2000)]
    assert mids[0] > mids[1] > mids[2]


def test_ranges_widen_with_lower_confidence():
    widths = {}
    for conf in ("high", "medium", "low"):
        r = unit_cost_range(simple_inputs(confidence=conf, tooling=(800, 1200)), 500)
        assert r["low"] <= r["mid"] <= r["high"]
        assert r["worst_low"] <= r["low"] and r["high"] <= r["worst_high"]
        widths[conf] = r["high"] - r["low"]
    assert widths["high"] < widths["medium"] < widths["low"]
    # With point values and high confidence there is no uncertainty at all.
    point = unit_cost_range(simple_inputs(confidence="high"), 500)
    assert point["low"] == point["mid"] == point["high"]


def test_verified_inputs_are_not_widened():
    a = Assumption("x", "x", "", 10, 20, "low", verified=False)
    b = Assumption("x", "x", "", 10, 20, "low", verified=True)
    spread = {"high": 0.0, "medium": 0.1, "low": 0.25}
    assert a.widened(spread) == (7.5, 25.0)
    assert b.widened(spread) == (10, 20)


def test_breakdown_lines_line_up_with_total():
    inp = simple_inputs(confidence="low")
    rows = breakdown(inp, 200)
    assert sum(r["mid"] for r in rows) == pytest.approx(unit_cost_range(inp, 200)["mid"], abs=0.05)
    assert all(r["low"] <= r["mid"] <= r["high"] for r in rows)


# --- sensitivity -----------------------------------------------------------------


def test_sensitivity_ranks_the_biggest_driver_first():
    inp = simple_inputs(tooling=(20000, 20000))  # tooling dominates at low volume
    ranked = sensitivity(inp, 100, step=0.25)
    assert ranked[0]["key"] == "tooling:1"
    assert ranked[0]["swing"] == pytest.approx(20000 / 100 * 0.25)  # linear: ±25% of £200/unit
    swings = [abs(r["swing"]) for r in ranked]
    assert swings == sorted(swings, reverse=True)
    # At high volume tooling stops mattering and the LED price outranks it.
    ranked_hi = sensitivity(inp, 1_000_000, step=0.25)
    keys = [r["key"] for r in ranked_hi]
    assert keys.index("item:9") < keys.index("tooling:1")
    assert len(sensitivity(inp, 100, top=5)) == 5
    assert all(r["swing_pct"] > 0 for r in ranked[:3])


def test_sensitivity_ignores_unused_assumptions():
    inp = simple_inputs()  # spin is not CNC, so removal rate is unused
    assert "removal:spin" not in {r["key"] for r in sensitivity(inp, 100)}


# --- service / API -----------------------------------------------------------------


def test_faro_cost_report(client, faro_project):
    pid = faro_project["id"]
    r = client.get(f"/api/projects/{pid}/costs").json()
    assert r["reference_quantity"] == 500 and "assumed" in r["reference_basis"]
    assert [v["quantity"] for v in r["volumes"]] == [100, 500, 2000]
    mids = [v["mid"] for v in r["volumes"]]
    assert mids[0] > mids[1] > mids[2]
    assert all(v["low"] < v["mid"] < v["high"] for v in r["volumes"])
    assert {p["name"] for p in r["parts"]} == {"Base", "Main body", "Decorative band", "Lantern", "Top cap"}
    assert {s["name"] for s in r["skipped"]} == {"LED module and mounting", "Cable / power entry"}
    assert len(r["sensitivity"]["top"]) == 5
    assert r["uses_unverified_data"] and all(not a["verified"] for a in r["assumptions"])
    for p in r["parts"]:
        assert {ln["category"] for ln in p["lines"]} >= {"material", "process", "setup", "tooling"}
        assert all(ln["explanation"] and ln["unverified"] for ln in p["lines"])
    names = {ln["label"] for ln in r["product_lines"]}
    assert any("driver (mains)" in n for n in names)  # undecided power -> mains set
    assert not any("battery" in n.lower() for n in names)
    assert {"assembly", "packaging", "bought_in"} <= {ln["category"] for ln in r["product_lines"]}


def test_project_volume_added_to_table(client, faro_project):
    pid = faro_project["id"]
    req = client.get(f"/api/projects/{pid}").json()["requirements"]
    client.patch(f"/api/projects/{pid}", json={"requirements": {**req, "production_volume": 1200}})
    r = client.get(f"/api/projects/{pid}/costs").json()
    assert [v["quantity"] for v in r["volumes"]] == [100, 500, 1200, 2000]
    assert [v["is_project_volume"] for v in r["volumes"]] == [False, False, True, False]
    assert r["reference_quantity"] == 1200 and r["reference_basis"] == "project production volume"


def test_cost_items_crud_and_reset(client, faro_project):
    pid = faro_project["id"]
    items = client.get(f"/api/projects/{pid}/cost-items").json()
    led = next(i for i in items if i["price_key"] == "led_module")
    before = client.get(f"/api/projects/{pid}/costs").json()["unit_cost"]["mid"]

    r = client.patch(f"/api/projects/{pid}/cost-items/{led['id']}", json={"unit_cost_low": 20, "unit_cost_high": 20})
    assert r.json()["source"] == "user"
    after = client.get(f"/api/projects/{pid}/costs").json()["unit_cost"]["mid"]
    # The seeded LED price is a distributor price, discounted to 40–60% at 500; a typed price is not.
    assert after - before == pytest.approx(20 - (2.53 + 3.74) / 2 * 0.5, abs=0.02)

    assert client.patch(f"/api/projects/{pid}/cost-items/{led['id']}", json={"unit_cost_high": 1}).status_code == 422
    r = client.post(f"/api/projects/{pid}/cost-items", json={"name": "Brass finial", "quantity": 1, "unit_cost_low": 3, "unit_cost_high": 5})
    assert r.status_code == 201
    assert client.post(f"/api/projects/{pid}/cost-items", json={"name": "No price"}).status_code == 422
    assert client.delete(f"/api/projects/{pid}/cost-items/{r.json()['id']}").status_code == 204

    # Battery power: reset loads the battery set instead of the mains set.
    req = client.get(f"/api/projects/{pid}").json()["requirements"]
    client.patch(f"/api/projects/{pid}", json={"requirements": {**req, "power_type": "battery"}})
    keys = {i["price_key"] for i in client.post(f"/api/projects/{pid}/cost-items/reset").json()}
    assert {"battery_pack", "charge_control_board"} <= keys and "led_driver_mains" not in keys


def test_quote_comparison_uses_model_when_manual_blank(client, faro_project):
    pid = faro_project["id"]
    body = next(p for p in client.get(f"/api/projects/{pid}/parts").json() if p["cad_key"] == "main_body")

    def add(qty, price):
        return client.post(f"/api/projects/{pid}/parts/{body['id']}/quotes", data={
            "source": "Spinner", "quote_date": "2026-10-01", "quantity": str(qty), "unit_price": str(price)}).json()

    small, big = add(10, 30), add(5000, 30)
    listing = client.get(f"/api/projects/{pid}/parts/{body['id']}/quotes").json()
    assert listing["estimate"]["source"] == "model"
    by_qty = {q["quantity"]: q for q in listing["quotes"]}
    assert by_qty[10]["comparison"]["status"] != "no_estimate"
    # Setup and tooling are shared over fewer pieces, so the model expects a higher price at 10 pcs
    # and the same £30 quote compares differently at the two quantities.
    assert small["comparison"]["text"] != big["comparison"]["text"]

    # Manual values take priority over the model.
    client.patch(f"/api/projects/{pid}/parts/{body['id']}", json={"cost_low": 25, "cost_high": 35})
    listing = client.get(f"/api/projects/{pid}/parts/{body['id']}/quotes").json()
    assert listing["estimate"]["source"] == "manual"
    assert all(q["comparison"]["status"] == "within" for q in listing["quotes"])


def test_model_part_estimate_falls_with_quantity(client, faro_project):
    from app.db import new_session
    from app.models import Project
    from app.services.costing import build_inputs, model_part_estimate

    session = new_session()
    project = session.get(Project, faro_project["id"])
    inputs, _ = build_inputs(session, project)
    cap = next(p for p in project.parts if p.cad_key == "top_cap")
    e10, e5000 = model_part_estimate(inputs, cap, 10), model_part_estimate(inputs, cap, 5000)
    assert e10["low"] > e5000["low"] and e10["high"] > e5000["high"]
    session.close()


# --- migration ---------------------------------------------------------------------


def test_cost_items_migration(tmp_path):
    url = f"sqlite:///{tmp_path / 'c.db'}"
    engine = create_engine(url)
    cfg = alembic_config(url)
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0002")
        conn.execute(text(
            "insert into projects (id, name, slug, description, template, requirements, assumed_fields, created_at, updated_at) "
            "values (1, 'Faro', 'faro', '', 'faro', '{}', '[]', '2026-01-01', '2026-01-01')"
        ))
    assert "cost_items" not in inspect(engine).get_table_names()
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0003")
    cols = {c["name"] for c in inspect(engine).get_columns("cost_items")}
    assert {"kind", "name", "quantity", "unit", "unit_cost_low", "unit_cost_high", "source", "confidence", "verified"} <= cols
    with engine.begin() as conn:
        assert conn.execute(text("select name from projects")).scalar() == "Faro"
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "0002")
    assert "cost_items" not in inspect(engine).get_table_names()
