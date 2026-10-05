import itertools

import pytest
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.costing.assemble import CostConfig, RouteChoice, assemble
from app.costing.data import load_cost_data
from app.costing.model import (
    Assumption,
    CostInputs,
    ItemSpec,
    PartGeometry,
    PartSpec,
    crossover,
    effective_volume_cm3,
    fixed_and_variable,
)
from app.costing.pricing import assess, factory_targets, status, targets
from app.db import new_session
from app.migrate import alembic_config
from app.models import EngineeringDecision, Project
from app.rules.data import load_rules
from app.services import costdown
from app.services.costing import snapshot


@pytest.fixture()
def ctx(client, faro_project):
    session = new_session()
    project = session.get(Project, faro_project["id"])
    snap = snapshot(session, project)
    defs = {d["key"]: d for d in costdown.scenario_defs(project)}
    yield {"client": client, "pid": faro_project["id"], "session": session, "project": project, "snap": snap, "defs": defs,
           "rules": load_rules(), "cost": load_cost_data()}
    session.close()


def mid(c, cfg, q=500):
    return costdown._cost(c["snap"], cfg, q, c["rules"], c["cost"])


# --- pricing -----------------------------------------------------------------------


def test_factory_targets_from_retail_price():
    p = {"vat_rate": 0.2, "dtc_factory_share": 0.33, "retailer_margin": 0.5, "wholesale_factory_share": 0.48}
    t = factory_targets(275, p)
    assert t["retail_ex_vat"] == pytest.approx(229.17, abs=0.01)
    assert t["dtc"] == pytest.approx(75.63, abs=0.01) and t["retail"] == pytest.approx(55.0, abs=0.01)
    full = targets({**p, "retail_price": 275, "retail_low": 249, "retail_high": 295, "premium_retail": 395})
    assert full["bands"]["dtc"]["low"] < full["bands"]["dtc"]["target"] < full["bands"]["dtc"]["high"]
    assert full["premium"]["dtc"] == pytest.approx(108.63, abs=0.01)


def test_pass_close_fail():
    assert status(70, 75, 0.15) == "pass" and status(75, 75, 0.15) == "pass"
    assert status(80, 75, 0.15) == "close" and status(90, 75, 0.15) == "fail"
    a = assess(60, {"dtc": 75, "retail": 55}, 0.15)
    assert a["dtc"]["status"] == "pass" and a["retail"]["status"] == "close" and a["retail"]["gap"] == 5


def test_pricing_api_defaults_edit_and_validation(ctx):
    c, pid = ctx["client"], ctx["pid"]
    r = c.get(f"/api/projects/{pid}/pricing").json()
    assert r["values"]["retail_price"] == 275 and r["values"]["premium_retail"] == 395
    assert r["targets"]["bands"]["dtc"]["target"] == pytest.approx(75.63, abs=0.01)
    assert r["targets"]["bands"]["retail"]["target"] == pytest.approx(55.0, abs=0.01)
    assert not r["meta"]["dtc_factory_share"]["verified"] and r["meta"]["dtc_factory_share"]["source"] == "model-generated"

    r = c.put(f"/api/projects/{pid}/pricing", json={"retail_price": 289, "dtc_factory_share": 0.30})
    assert r.status_code == 200
    body = r.json()
    assert body["values"]["retail_price"] == 289 and body["meta"]["retail_price"]["edited"]
    assert body["targets"]["standard"]["dtc"] == pytest.approx(289 / 1.2 * 0.30, abs=0.01)
    assert c.get(f"/api/projects/{pid}").json()["requirements"]["target_retail_price"]["amount"] == 289
    assert c.put(f"/api/projects/{pid}/pricing", json={"retail_price": 400}).status_code == 422  # above range
    assert c.put(f"/api/projects/{pid}/pricing", json={"retailer_margin": 1.5}).status_code == 422
    assert c.put(f"/api/projects/{pid}/pricing", json={"bogus": 1}).status_code == 422


# --- process routes ----------------------------------------------------------------


def test_routes_only_include_viable_processes(ctx):
    data = costdown.part_routes(ctx["session"], ctx["project"], ctx["snap"])
    parts = {p["name"]: p for p in data["parts"]}
    assert set(parts) == {"Base", "Main body", "Decorative band", "Lantern", "Top cap"}  # bought-in parts excluded
    body = {r["process_key"] for r in parts["Main body"]["routes"]}
    assert "extrusion" not in body  # tapered body: rules engine excludes extrusion
    assert {"metal_spinning", "sheet_forming"} <= body
    lantern = {r["process_key"] for r in parts["Lantern"]["routes"]}
    assert lantern <= {"polymer_tube_cut", "glass_tube_cut", "injection_moulding_clear", "cnc_machining"}
    assert "metal_spinning" not in lantern
    for p in data["parts"]:
        assert sum(r["is_current"] for r in p["routes"]) == 1
        assert all(r["viable"] or r["is_current"] for r in p["routes"])
        for r in p["routes"]:
            assert set(r["costs"]) == {"100", "500", "2000"}
            assert set(r["tradeoffs"]) == {"cost", "finish", "weight", "premium", "lead_time", "tooling"}


def test_route_design_changes_and_extra_parts(ctx):
    data = costdown.part_routes(ctx["session"], ctx["project"], ctx["snap"])
    base = next(p for p in data["parts"] if p["name"] == "Base")
    spun = next(r for r in base["routes"] if r["process_key"] == "metal_spinning")
    assert any("weight plate" in t for t in spun["design_changes"])
    assert any("weight plate" in e for e in spun["extra_items"])
    assert any(f["kind"] == "safety" for f in spun["flags"])
    cast = next(r for r in base["routes"] if r["process_key"] == "die_casting")
    assert any("draft" in t for t in cast["design_changes"])
    cnc = next(r for r in base["routes"] if r["process_key"] == "cnc_machining")
    assert cnc["design_changes"] == [] and cnc["tooling"]["high"] == 0
    # Die casting: huge tooling makes it dearest at 100 units but it crosses CNC at some volume.
    assert cast["costs"]["100"]["mid"] > cnc["costs"]["100"]["mid"]
    assert any(x["vs"] == "CNC machining" for x in cast["crossovers"])


def test_crossover_maths():
    # Route A: £1,000 tooling, £10/unit. Route B: no tooling, £20/unit. Equal at 100 units.
    assert crossover((1000, 10), (0, 20)) == pytest.approx(100)
    assert crossover((0, 20), (1000, 10)) == pytest.approx(100)
    assert crossover((500, 10), (100, 10)) is None  # parallel: never cross
    assert crossover((0, 10), (1000, 20)) is None  # A is cheaper at every volume

    part = PartSpec(1, "P", 1, "spin", "Spin", "al", "Al", 2.7, PartGeometry(100_000, (100, 100, 50)), None, None, "x")
    def A(key, v):
        return Assumption(key, key, "", v, v, "high")

    a = {x.key: x for x in [
        A("mat_price:al", 5), A("rate:spin", 60), A("setup:spin", 2), A("cycle:spin", 6), A("cycle_kg:spin", 0),
        A("util:spin", 1), A("tooling:1", 1000),
    ]}
    f, v = fixed_and_variable(CostInputs(assumptions=a, parts=[part]))
    assert f == pytest.approx(1000 + 2 * 60)  # tooling + setup
    assert v == pytest.approx(0.27 * 5 + 6 * 60 / 60, abs=1e-4)


def test_sheet_formed_parts_costed_as_shells():
    solid = PartGeometry(300_000, (110, 110, 45))  # solid dome in CAD
    p = PartSpec(1, "Cap", 1, "metal_spinning", "Spinning", "al", "Al", 2.7, solid, None, None, "x", formed_shell_mm=2.0)
    shell_cm3 = solid.visible_area_m2 * 1e4 * 0.2
    assert effective_volume_cm3(p) == pytest.approx(shell_cm3) and shell_cm3 < 300
    q = PartSpec(1, "Cap", 1, "cnc_machining", "CNC", "al", "Al", 2.7, solid, None, None, "x")
    assert effective_volume_cm3(q) == pytest.approx(300)


def test_select_route_records_decision_and_updates_everything(ctx):
    c, pid = ctx["client"], ctx["pid"]
    base = next(p for p in c.get(f"/api/projects/{pid}/parts").json() if p["cad_key"] == "base")
    before = c.get(f"/api/projects/{pid}/costs").json()["unit_cost"]["mid"]
    assert c.post(f"/api/projects/{pid}/parts/{base['id']}/route",
                  json={"process_key": "metal_spinning", "material_key": "al_1050", "reason": " "}).status_code == 422
    assert c.post(f"/api/projects/{pid}/parts/{base['id']}/route",
                  json={"process_key": "extrusion", "material_key": "al_6063", "reason": "x"}).status_code == 422  # not viable

    r = c.post(f"/api/projects/{pid}/parts/{base['id']}/route",
               json={"process_key": "metal_spinning", "material_key": "al_1050", "reason": "Cut cost; quotes from spinners"})
    assert r.status_code == 200, r.text
    assert r.json()["chosen"]["cad_mismatch"] is True

    session = new_session()
    d = session.query(EngineeringDecision).filter_by(project_id=pid, part_id=base["id"], topic="process_route").one()
    assert d.note == "Cut cost; quotes from spinners" and d.chosen["process"] == "Metal spinning"
    assert d.chosen["previous_process"] == "cnc_machining" and d.status == "edited"
    session.close()

    part = next(p for p in c.get(f"/api/projects/{pid}/parts").json() if p["id"] == base["id"])
    assert part["process"] == "Metal spinning" and part["material"] == "Aluminium 1050A (H14)"
    cost = c.get(f"/api/projects/{pid}/costs").json()
    assert next(p for p in cost["parts"] if p["name"] == "Base")["process"] == "Metal spinning"
    assert any("weight plate" in ln["label"].lower() for ln in cost["product_lines"])
    assert cost["unit_cost"]["mid"] < before
    bom = c.get(f"/api/projects/{pid}/bom").json()
    assert "CAD mismatch" in next(r for r in bom["rows"] if r["name"] == "Base")["flags"]
    assert any(r["item"].startswith("R") and "weight plate" in r["name"].lower() for r in bom["rows"])
    dfm = c.get(f"/api/projects/{pid}/dfm").json()
    assert any(ch["title"] == "Base: CAD does not match the chosen route" for ch in dfm["checks"])
    rec = next(r for r in c.get(f"/api/projects/{pid}/recommendations").json()["recommendations"] if r["part_id"] == base["id"])
    assert rec["decision"]["status"] == "edited"
    # CAD itself is untouched.
    assert c.get(f"/api/projects/{pid}/cad").json()["latest"] is None


# --- scenarios ---------------------------------------------------------------------


def cfg_for(c, *keys, region="uk", option=0):
    return costdown.selection_config(c["defs"], [(k, option) for k in keys], region, c["snap"].params)


def test_band_stripe_removes_band_and_adds_stripe(ctx):
    inputs, actx = assemble(ctx["snap"], cfg_for(ctx, "band_stripe"), ctx["rules"], ctx["cost"])
    assert "Decorative band" not in {p.name for p in inputs.parts}
    assert any("Removed" in s["reason"] for s in actx["skipped"] if s["name"] == "Decorative band")
    assert any(i.kind == "finishing" and "stripe" in i.name.lower() for i in inputs.items)
    assert mid(ctx, cfg_for(ctx, "band_stripe")) < mid(ctx, CostConfig())


def test_external_adapter_swaps_electrics_and_flags_compliance(ctx):
    inputs, _ = assemble(ctx["snap"], cfg_for(ctx, "external_adapter"), ctx["rules"], ctx["cost"])
    names = " | ".join(i.name for i in inputs.items)
    assert "driver (mains)" not in names and "Mains cable" not in names
    assert "12 V adapter" in names and "12 V LED module" in names
    ev = costdown.evaluate_selection(ctx["session"], ctx["project"], [{"key": "external_adapter"}], "uk")
    assert any(f["kind"] == "compliance" for f in ev["flags"])


def test_lamp_tube_removes_screws_and_shortens_assembly(ctx):
    base_inputs, _ = assemble(ctx["snap"], CostConfig(), ctx["rules"], ctx["cost"])
    inputs, _ = assemble(ctx["snap"], cfg_for(ctx, "lamp_tube"), ctx["rules"], ctx["cost"])
    names = [i.name for i in inputs.items]
    assert not any("machine screw" in n for n in names) and any("lamp tube" in n for n in names)
    qkey = next(i.qty_key for i in inputs.items if i.qty_key)
    assert inputs.assumptions[qkey].mid < base_inputs.assumptions[qkey].mid


def test_base_sheet_uses_route_change_extras_and_lamp_tube_removes_rivet_nuts(ctx):
    inputs, actx = assemble(ctx["snap"], cfg_for(ctx, "base_sheet"), ctx["rules"], ctx["cost"])
    names = [i.name.lower() for i in inputs.items]
    assert any("weight plate" in n for n in names) and any("rivet nut" in n for n in names)
    assert any(f["kind"] == "safety" for f in actx["flags"])
    inputs2, _ = assemble(ctx["snap"], cfg_for(ctx, "base_sheet", "lamp_tube"), ctx["rules"], ctx["cost"])
    assert not any("rivet nut" in i.name.lower() for i in inputs2.items)  # one nut clamps the stack instead


def test_height_reduction_scales_geometry_and_cost(ctx):
    inputs, _ = assemble(ctx["snap"], cfg_for(ctx, "height_350"), ctx["rules"], ctx["cost"])
    body = next(p for p in inputs.parts if p.name == "Main body")
    assert body.geometry.size_mm[2] < ctx["snap"].geometry["main_body"]["size_mm"][2]
    assert mid(ctx, cfg_for(ctx, "height_350")) < mid(ctx, CostConfig())


def test_region_multipliers_and_freight(ctx):
    uk, _ = assemble(ctx["snap"], CostConfig(), ctx["rules"], ctx["cost"])
    cn, _ = assemble(ctx["snap"], CostConfig(region="china"), ctx["rules"], ctx["cost"])
    assert cn.assumptions["rate:metal_spinning"].high < uk.assumptions["rate:metal_spinning"].high
    assert cn.assumptions["labour_rate"].mid < uk.assumptions["labour_rate"].mid
    assert uk.overhead_key is None and cn.overhead_key == "region_freight_duty"
    assert not cn.assumptions["region_freight_duty"].verified


def test_conflicting_scenarios_rejected(ctx):
    r = ctx["client"].post(f"/api/projects/{ctx['pid']}/scenarios/evaluate",
                           json={"changes": [{"key": "band_tube"}, {"key": "band_stripe"}]})
    assert r.status_code == 422
    r = ctx["client"].post(f"/api/projects/{ctx['pid']}/scenarios/evaluate", json={"changes": [{"key": "nope"}]})
    assert r.status_code == 422


def test_evaluate_selection_reports_marginal_savings_and_targets(ctx):
    ev = ctx["client"].post(f"/api/projects/{ctx['pid']}/scenarios/evaluate",
                            json={"changes": [{"key": "base_sheet", "option": None}, {"key": "band_tube"}], "region": "portugal"}).json()
    assert [s["key"] for s in ev["selection"]] == ["base_sheet", "band_tube"]
    assert ev["selection"][0]["option_label"] in ("Spun", "Pressed (deep drawn)")
    assert {m["key"] for m in ev["marginal"]} == {"base_sheet", "band_tube", "region"}
    assert all(m["saving"]["500"] > 0 for m in ev["marginal"])
    row = next(v for v in ev["volumes"] if v["quantity"] == 500)
    assert row["saving"] > 0 and set(row["targets"]) == {"dtc", "retail"}


def test_scenario_catalog(ctx):
    cat = ctx["client"].get(f"/api/projects/{ctx['pid']}/scenarios").json()
    assert [s["letter"] for s in cat["scenarios"]] == list("abcdefgh")
    assert {r["key"] for r in cat["regions"]} == {"uk", "portugal", "turkey", "china"}
    assert all(not r["verified"] for r in cat["regions"])
    for s in cat["scenarios"]:
        assert set(s["tradeoffs"]) == {"finish", "weight", "premium", "lead_time", "tooling"}


# --- product-level optimum -----------------------------------------------------------


def test_optimiser_matches_brute_force(ctx):
    c = ctx
    best = costdown.optimise(c["snap"], c["defs"], 500, c["rules"], c["cost"], tier="strict")
    keys = [k for k, d in c["defs"].items() if d.get("premium_impact", "none") == "none"]
    assert set(k for k, _ in best["selection"]) <= set(keys)
    brute = []
    for region in c["cost"].regions:
        for r in range(len(keys) + 1):
            for combo in itertools.combinations(keys, r):
                if costdown._conflict(combo, c["defs"]):
                    continue
                for opts in itertools.product(*[range(costdown.n_options(c["defs"][k])) for k in combo]):
                    brute.append(mid(c, costdown.selection_config(c["defs"], list(zip(combo, opts)), region, c["snap"].params)))
    assert best["mid"] == pytest.approx(min(brute), abs=0.01)


def test_tiers_are_ordered_and_summary_complete(ctx):
    c = ctx
    costs = {t: costdown.optimise(c["snap"], c["defs"], 500, c["rules"], c["cost"], tier=t)["mid"] for t in ("strict", "premium", "any")}
    current = mid(c, CostConfig())
    assert costs["any"] <= costs["premium"] <= costs["strict"] < current
    strict = costdown.optimise(c["snap"], c["defs"], 500, c["rules"], c["cost"], tier="strict")
    assert not any(c["defs"][k]["premium_impact"] != "none" for k, _ in strict["selection"])

    sm = c["client"].get(f"/api/projects/{c['pid']}/cost-down/summary").json()
    for q in (500, 2000):
        labels = [r["label"] for r in sm["rows"] if r["quantity"] == q]
        assert labels[0] == "Current configuration" and len(labels) == 4
    for r in sm["rows"]:
        assert {r["targets"]["dtc"]["status"], r["targets"]["retail"]["status"]} <= {"pass", "close", "fail"}
    cur = next(r for r in sm["rows"] if r["quantity"] == 500 and r["tier"] == "current")
    assert cur["targets"]["dtc"]["status"] == "fail"  # ~£150 vs ~£76 target
    prem = sm["premium"]
    assert prem["retail"] == 395 and len(prem["rows"]) == 8
    assert all(not any(s["key"] == "band_stripe" for s in r["selection"]) for r in prem["rows"])  # brass band needs a band


def test_scenario_sets_crud(ctx):
    c, pid = ctx["client"], ctx["pid"]
    r = c.post(f"/api/projects/{pid}/scenario-sets", json={"name": "Lean", "changes": [{"key": "lamp_tube"}], "region": "turkey"})
    assert r.status_code == 201
    assert c.post(f"/api/projects/{pid}/scenario-sets", json={"name": "Bad", "region": "mars"}).status_code == 422
    assert [s["name"] for s in c.get(f"/api/projects/{pid}/scenario-sets").json()] == ["Lean"]
    assert c.delete(f"/api/projects/{pid}/scenario-sets/{r.json()['id']}").status_code == 204


# --- migration -----------------------------------------------------------------------


def test_pricing_and_scenarios_migration(tmp_path):
    url = f"sqlite:///{tmp_path / 'p.db'}"
    engine = create_engine(url)
    cfg = alembic_config(url)
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0003")
    assert "cost_scenarios" not in inspect(engine).get_table_names()
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0004")
    assert "cost_scenarios" in inspect(engine).get_table_names()
    assert "pricing" in {c["name"] for c in inspect(engine).get_columns("projects")}
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "0003")
    assert "cost_scenarios" not in inspect(engine).get_table_names()
    assert "pricing" not in {c["name"] for c in inspect(engine).get_columns("projects")}
