"""Price basis, volume discounts and the trade-basis aluminium price."""

import pytest
import yaml

from app.config import SEED_DIR
from app.costing.assemble import CostConfig, assemble
from app.costing.data import load_cost_data, load_cost_data_from
from app.costing.model import Assumption, CostInputs, ItemSpec, PartGeometry, PartSpec, evaluate, raw_mid, total
from app.db import new_session
from app.models import Project
from app.rules.data import RulesDataError, load_rules
from app.services.costing import snapshot

COST = load_cost_data()


def A(key, low, high=None):
    return Assumption(key, key, "", low, low if high is None else high, "high")


def test_researched_seed_entries_carry_a_basis_and_quantity():
    for key, e in {**COST.bought_in, **{f"mat:{k}": v for k, v in COST.material_prices.items()}}.items():
        if e.source.startswith("http") or "http" in e.source:
            assert e.price_basis != "model_estimate", key
        if e.price_basis in ("distributor_small_qty", "retail"):
            assert e.basis_quantity, key
    assert COST.bought_in["led_module"].price_basis == "distributor_small_qty"
    assert COST.material_prices["al_1050"].price_basis == "retail"
    assert COST.bought_in["screw_m4"].price_basis == "model_estimate"


def test_loader_rejects_distributor_price_without_quantity(tmp_path):
    import shutil

    d = tmp_path / "cost"
    shutil.copytree(SEED_DIR / "cost", d)
    doc = yaml.safe_load((d / "bought_in.yaml").read_text())
    doc["bought_in"][0].pop("basis_quantity")
    (d / "bought_in.yaml").write_text(yaml.safe_dump(doc))
    with pytest.raises(RulesDataError):
        load_cost_data_from(d)


def test_discount_applies_only_from_its_quantity():
    item = ItemSpec(1, "bought_in", "LED", 1, "pcs", "item:1", discount_key="discount:electronics", discount_from=500)
    inp = CostInputs(assumptions={"item:1": A("item:1", 4.0), "discount:electronics": A("discount:electronics", 0.4, 0.6)},
                     items=[item])
    assert total(evaluate(inp, inp.mids(), 100)) == pytest.approx(4.0)  # small quantity: researched price
    assert total(evaluate(inp, inp.mids(), 500)) == pytest.approx(2.0)  # 50% at 500+
    assert raw_mid(inp, 2000) == pytest.approx(4.0)  # raw = researched price, side by side


def test_trade_basis_material_price():
    geo = PartGeometry(100_000, (100, 100, 50))
    keys = {"lme": "lme", "premium": "prem", "fx": "fx", "conversion": "conv"}
    p = PartSpec(1, "Base", 1, "spin", "Spin", "al", "Al", 2.7, geo, None, None, "x", trade_keys=keys)
    a = {k.key: k for k in [A("mat_price:al", 8.45), A("rate:spin", 0), A("setup:spin", 0), A("cycle:spin", 0),
                            A("cycle_kg:spin", 0), A("util:spin", 1), A("tooling:1", 0), A("lme", 3120), A("prem", 400),
                            A("fx", 1.32), A("conv", 1.5)]}
    inp = CostInputs(assumptions=a, parts=[p])
    per_kg = (3120 + 400) / 1.32 / 1000 + 1.5
    mat = next(ln for ln in evaluate(inp, inp.mids(), 500) if ln.category == "material")
    assert mat.amount == pytest.approx(0.27 * per_kg, rel=1e-6)
    raw = next(ln for ln in evaluate(inp, inp.mids(), 500, raw=True) if ln.category == "material")
    assert raw.amount == pytest.approx(0.27 * 8.45, rel=1e-6)  # raw keeps the researched merchant price


def test_region_decides_material_basis(client, faro_project):
    session = new_session()
    project = session.get(Project, faro_project["id"])
    snap = snapshot(session, project)
    rules = load_rules()
    uk, _ = assemble(snap, CostConfig(region="uk"), rules, COST)
    cn, ctx = assemble(snap, CostConfig(region="china"), rules, COST)
    base_uk = next(p for p in uk.parts if p.name == "Base")
    base_cn = next(p for p in cn.parts if p.name == "Base")
    assert base_uk.trade_keys is None and base_uk.price_discount_key == "discount:merchant_material"
    assert base_cn.trade_keys and "commodity:lme_aluminium_cash" in cn.assumptions
    assert cn.assumptions["commodity:lme_aluminium_cash"].confidence == "high"
    assert "trade basis" in ctx["details"][base_cn.part_id]["form"]
    session.close()


def test_cost_settings_api_edits_discounts(client, faro_project):
    pid = faro_project["id"]
    s = client.get(f"/api/projects/{pid}/cost-settings").json()["volume_discounts"]
    assert s["electronics"]["low"] == 0.4 and s["electronics"]["high"] == 0.6 and not s["electronics"]["verified"]
    assert s["merchant_material"]["low"] == 0.5 and s["merchant_material"]["confidence"] == "medium"
    before = client.get(f"/api/projects/{pid}/costs").json()["unit_cost"]["mid"]
    r = client.put(f"/api/projects/{pid}/cost-settings", json={"volume_discounts": {"electronics": {"low": 0.9, "high": 1.0}}})
    assert r.status_code == 200 and r.json()["volume_discounts"]["electronics"]["edited"]
    after = client.get(f"/api/projects/{pid}/costs").json()["unit_cost"]["mid"]
    assert after > before  # less discount -> dearer electronics
    assert client.put(f"/api/projects/{pid}/cost-settings", json={"volume_discounts": {"electronics": {"low": 0, "high": 1}}}).status_code == 422
    assert client.put(f"/api/projects/{pid}/cost-settings", json={"volume_discounts": {"nope": {"low": 0.5, "high": 0.6}}}).status_code == 422
    client.put(f"/api/projects/{pid}/cost-settings", json={"volume_discounts": {"electronics": None}})
    assert client.get(f"/api/projects/{pid}/costs").json()["unit_cost"]["mid"] == pytest.approx(before)


def test_cost_items_carry_basis_and_user_prices_are_volume_prices(client, faro_project):
    pid = faro_project["id"]
    items = client.get(f"/api/projects/{pid}/cost-items").json()
    led = next(i for i in items if i["price_key"] == "led_module")
    assert led["price_basis"] == "distributor_small_qty" and led["basis_quantity"] == 100 and led["discount_class"] == "electronics"
    r = client.patch(f"/api/projects/{pid}/cost-items/{led['id']}", json={"unit_cost_low": 2.0, "unit_cost_high": 2.2})
    assert r.json()["price_basis"] == "trade_volume" and r.json()["discount_class"] is None


def test_audit_shows_raw_and_adjusted_prices(client, faro_project):
    a = client.get(f"/api/projects/{faro_project['id']}/cost-audit").json()
    assert a["unit_cost_raw_mid"] > a["unit_cost_mid"]
    led = next(p for p in a["prices"] if p["label"].startswith("LED module"))
    assert led["adjustment"] == "volume discount" and led["adjusted"]["500"] < led["raw_mid"]
    keys = {r["key"] for r in a["rows"]}
    assert "discount:electronics" in keys
    md = client.get(f"/api/projects/{faro_project['id']}/cost-audit.md").text
    assert "Researched prices vs volume-adjusted prices" in md
