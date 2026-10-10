"""Atelier cost items, compliance one-offs, scenarios and the cost-down summary (no Faro assumptions)."""

import pytest

from app.costing.data import load_cost_data
from app.services.templates import load_template

TPL = load_template("atelier")
PLAIN = {**TPL["cad_parameters"], "grille_perforated": 0}


def test_every_cost_item_and_scenario_item_has_a_price():
    cost = load_cost_data()
    keys = {it["price_key"] for it in TPL["cost_items"] if it.get("price_key")}
    for sc in TPL["scenarios"]:
        eff = sc["effect"]
        keys |= {a["price_key"] for a in eff.get("add_items", [])} | set(eff.get("remove_items", []))
    missing = sorted(k for k in keys if k not in cost.bought_in)
    assert missing == []
    one_offs = {it["price_key"] for it in TPL["cost_items"] if it["kind"] == "one_off"}
    assert {"speaker_radio_emc_safety_testing", "bluetooth_sig_listing"} <= one_offs
    parts = {p["cad_key"] for p in TPL["parts"]}
    for sc in TPL["scenarios"]:
        rp = sc["effect"].get("remove_part", [])
        assert set([rp] if isinstance(rp, str) else rp) <= parts


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    from fastapi.testclient import TestClient

    from app.db import init_db
    from app.main import create_app

    app = create_app()
    init_db(f"sqlite:///{tmp_path_factory.mktemp('db') / 'costs.db'}")
    with TestClient(app) as c:
        pid = c.post("/api/projects", json={"name": "Atelier", "template": "atelier"}).json()["id"]
        assert c.post(f"/api/projects/{pid}/cad/generate", json={"parameters": PLAIN}).status_code == 201
        yield c, pid


def test_cost_items_seeded_from_the_template(project):
    c, pid = project
    items = c.get(f"/api/projects/{pid}/cost-items").json()
    keys = {it["price_key"] for it in items if it.get("price_key")}
    assert {"speaker_driver_57", "speaker_main_board", "battery_pack_1s2p", "knob_logo_engrave", "collar_lettering_etch"} <= keys
    assert any(it["kind"] == "assembly" and it["quantity"] == 30 for it in items)


def test_cost_report_counts_three_fins(project):
    c, pid = project
    rep = c.get(f"/api/projects/{pid}/costs").json()
    fin = next(p for p in rep["parts"] if p["name"] == "Fin")
    assert fin["quantity"] == 3
    assert rep["unit_cost"]["mid"] > 0 and rep["uses_unverified_data"]
    one_off = [ln for ln in rep["product_lines"] if "one-off" in ln.get("explanation", "").lower() or ln.get("category") == "one_off"]
    assert one_off  # testing and the SIG listing, shared over the batch
    assert c.get(f"/api/projects/{pid}/cost-audit?quantity=500").status_code == 200


def test_cost_down_summary_has_no_faro_assumptions(project):
    c, pid = project
    s = c.get(f"/api/projects/{pid}/cost-down/summary").json()
    assert {r["power"] for r in s["rows"]} == {"A"}
    assert s["premium"]["rows"] == []  # no brass edition for Atelier
    assert any("cordless (2 x 18650 1S2P" in n for n in s["notes"])
    assert not any("touch dimmer" in n for n in s["notes"])
    scen = {d["key"] for d in c.get(f"/api/projects/{pid}/scenarios").json()["scenarios"]}
    assert {"nose_cone_spun", "custom_battery_pack", "sealed_no_radiator"} <= scen
    best = next(r for r in s["rows"] if r["quantity"] == 2000 and r["tier"] == "strict")
    cur = next(r for r in s["rows"] if r["quantity"] == 2000 and r["tier"] == "current")
    assert best["cost"]["mid"] <= cur["cost"]["mid"]
    assert "sealed_no_radiator" not in [x["key"] for x in best["selection"]]  # slight compromise: not in "strict"


def test_cad_tab_mass_matches_the_stability_mass(project):
    """The CAD tab's estimate (rules densities) and the DFM mass check (stability) count the same things."""
    from app.cad import atelier

    c, pid = project
    est = c.get(f"/api/projects/{pid}/cad").json()["mass"]["total_kg"]
    assert est == pytest.approx(atelier.stability(PLAIN)["total_g"] / 1000, abs=0.01)


def test_low_tooling_first_batch_seed_is_unverified():
    """The scenario's new rates are model-generated and unverified (shown with the Unverified badge)."""
    from app.rules.data import load_rules

    rules, cost = load_rules(), load_cost_data()
    proc, mat = rules.processes["pu_vacuum_casting"], rules.materials["pu_casting_resin"]
    entries = [proc, mat, cost.process_rates["pu_vacuum_casting"], cost.bought_in["pu_silicone_mould_share"]]
    assert all(not e.verified and e.source == "model-generated" for e in entries)
    sc = next(d for d in TPL["scenarios"] if d["key"] == "low_tooling_first_batch")
    assert sc["effect"]["reroute"]["parts"] == ["fin", "collar", "foot"]
    assert [o["material"] for o in sc["effect"]["reroute"]["options"]] == ["brass", "brass"]  # aluminium: too light


def test_low_tooling_first_batch_costs(project):
    """Soft tooling wins at 300 and 500 and loses at 2,000, where the steel mould and dies pay back."""
    c, pid = project
    cat = {d["key"]: d for d in c.get(f"/api/projects/{pid}/scenarios").json()["scenarios"]}
    t = cat["low_tooling_first_batch"]
    assert t["premium_impact"] == "slight" and [o["label"] for o in t["options"]] == ["CNC-machined brass", "Investment-cast brass"]
    assert all(o["allowed"] for o in t["options"])  # brass on visible parts, plastic only on the lacquered body
    r = c.post(f"/api/projects/{pid}/scenarios/evaluate", json={"changes": [{"key": "low_tooling_first_batch", "option": 0}]})
    assert r.status_code == 200, r.text

    from app.costing.assemble import assemble
    from app.costing.data import load_cost_data as lcd
    from app.costing.model import evaluate
    from app.db import new_session
    from app.models import Project
    from app.rules.data import load_rules
    from app.services import costdown
    from app.services.costing import snapshot

    with new_session() as s:
        proj = s.get(Project, pid)
        snap = snapshot(s, proj)
        defs = {d["key"]: d for d in costdown.scenario_defs(proj)}
        rules, cost = load_rules(), lcd()
        current, _ = assemble(snap, costdown.CostConfig(), rules, cost)
        for opt in (0, 1):
            alt, _ = assemble(snap, costdown.selection_config(defs, [("low_tooling_first_batch", opt)], "uk", snap.params),
                              rules, cost)
            for q in (300, 500):
                assert costdown._mid(alt, q) < costdown._mid(current, q), (opt, q)
            assert costdown._mid(alt, 2000) > costdown._mid(current, 2000), opt
        cfg = costdown.selection_config(defs, [("low_tooling_first_batch", 1)], "uk", snap.params)
        assert {k: (r.process_key, r.material_key) for k, r in cfg.routes.items()} == {
            "body": ("pu_vacuum_casting", "pu_casting_resin"), "fin": ("investment_casting", "brass"),
            "collar": ("investment_casting", "brass"), "foot": ("investment_casting", "brass")}
        inputs, _ = assemble(snap, cfg, load_rules(), lcd())
        lines = evaluate(inputs, inputs.mids(), 500)
        mould = [ln for ln in lines if ln.label.startswith("Silicone mould share")]
        assert len(mould) == 1 and mould[0].category == "tooling" and mould[0].amount > 10  # per unit, not shared


def test_jesmonite_seed_is_unverified():
    from app.rules.data import load_rules

    rules, cost = load_rules(), load_cost_data()
    mat = rules.materials["jesmonite_ac100"]
    assert mat.density_g_cm3 == 1.745 and mat.material_kind == "composite"
    entries = [rules.processes["jesmonite_casting"], mat, cost.process_rates["jesmonite_casting"],
               cost.material_prices["jesmonite_ac100"]] + [
        cost.bought_in[k] for k in ("jesmonite_silicone_mould_share", "jesmonite_cast_in_inserts", "jesmonite_sealer_primer")]
    assert all(not e.verified for e in entries)
    sc = next(d for d in TPL["scenarios"] if d["key"] == "jesmonite_body")
    texts = " ".join(f["message"] for f in sc["flags"])
    for item in ("drop test", "lacquer adhesion", "Bluetooth range"):
        assert item in texts, item
    # every scenario that replaces the body excludes the others
    bodies = {"low_tooling_first_batch", "jesmonite_body", "all_jesmonite"}
    for d in TPL["scenarios"]:
        if d["key"] in bodies:
            assert bodies - {d["key"]} <= set(d["conflicts"]), d["key"]


def test_jesmonite_body_costs(project):
    """Soft-tooled Jesmonite body: cheaper than the steel mould at 300 and 500, dearer at 2,000."""
    c, pid = project
    cat = {d["key"]: d for d in c.get(f"/api/projects/{pid}/scenarios").json()["scenarios"]}
    j = cat["jesmonite_body"]
    assert [o["label"] for o in j["options"]] == ["Die-cast Zamak (as now)", "CNC-machined brass"]
    assert all(o["allowed"] for o in j["options"])

    from app.costing.assemble import assemble
    from app.costing.data import load_cost_data as lcd
    from app.costing.model import evaluate
    from app.db import new_session
    from app.models import Project
    from app.rules.data import load_rules
    from app.services import costdown
    from app.services.costing import snapshot

    with new_session() as s:
        proj = s.get(Project, pid)
        snap = snapshot(s, proj)
        defs = {d["key"]: d for d in costdown.scenario_defs(proj)}
        rules, cost = load_rules(), lcd()
        current, _ = assemble(snap, costdown.CostConfig(), rules, cost)
        die, _ = assemble(snap, costdown.selection_config(defs, [("jesmonite_body", 0)], "uk", snap.params), rules, cost)
        cnc, _ = assemble(snap, costdown.selection_config(defs, [("jesmonite_body", 1)], "uk", snap.params), rules, cost)
        for q in (300, 500):
            assert costdown._mid(cnc, q) < costdown._mid(die, q) < costdown._mid(current, q), q
        assert costdown._mid(die, 2000) > costdown._mid(current, 2000)
        body_mat = next(ln for ln in evaluate(die, die.mids(), 500) if ln.label == "Body" and ln.category == "material")
        base_mat = next(ln for ln in evaluate(current, current.mids(), 500) if ln.label == "Body" and ln.category == "material")
        assert body_mat.amount > base_mat.amount  # 5 mm wall (volume_scale) and the heavier, dearer material
        labels = {ln.label.split(" ")[0] + ln.category for ln in evaluate(die, die.mids(), 500)}
        assert {"Silicone" + "tooling", "Sealer" + "finishing", "Cast-in" + "bought_in"} <= labels


def test_all_jesmonite_costs(project):
    """Option A is allowed (coloured, no metal look); option B (metal-powder skin) breaks the solid-metal rule."""
    c, pid = project
    cat = {d["key"]: d for d in c.get(f"/api/projects/{pid}/scenarios").json()["scenarios"]}
    m = cat["all_jesmonite"]
    a, b = m["options"]
    assert a["label"].startswith("A") and a["allowed"]
    assert b["label"].startswith("B") and not b["allowed"] and "solid metal" in b["excluded_reason"].lower()
    assert "mass and balance" in m["reference_only"].lower()  # not recommended: kept for reference
    summary = c.get(f"/api/projects/{pid}/cost-down/summary").json()
    assert not any(x["key"] == "all_jesmonite" for r in summary["rows"] for x in r["selection"])
    texts = " ".join(f["message"] for f in m["flags"])
    for item in ("fin-tip chipping", "USB-C fit", "gel-coat wear"):
        assert item in texts, item

    from app.costing.assemble import assemble
    from app.costing.data import load_cost_data as lcd
    from app.costing.model import evaluate
    from app.db import new_session
    from app.models import Project
    from app.rules.data import load_rules
    from app.services import costdown
    from app.services.costing import snapshot

    with new_session() as s:
        proj = s.get(Project, pid)
        snap = snapshot(s, proj)
        defs = {d["key"]: d for d in costdown.scenario_defs(proj)}
        rules, cost = load_rules(), lcd()
        current, _ = assemble(snap, costdown.CostConfig(), rules, cost)
        for opt, finish in ((0, "Coloured"), (1, "Brass Flex Metal")):
            inputs, ctx = assemble(snap, costdown.selection_config(defs, [("all_jesmonite", opt)], "uk", snap.params), rules, cost)
            for q in (300, 500):
                assert costdown._mid(inputs, q) < costdown._mid(current, q), (opt, q)
            fin = next(p for p in inputs.parts if p.name == "Fin")
            assert fin.process_key == "jesmonite_casting" and fin.finish_name.startswith(finish)
            labels = [ln.label for ln in evaluate(inputs, inputs.mids(), 500)]
            assert not any(lb.startswith("Laser-etch") for lb in labels)  # lettering cast in from the pattern
    from app.rules.data import load_rules as lr

    rules = lr()
    assert not rules.finishes["flex_metal_brass_gelcoat"].verified and not rules.finishes["pigmented_jesmonite_sealed"].verified
    costs = lcd()
    assert all(not costs.bought_in[k].verified for k in ("jesmonite_small_moulds_share", "jesmonite_part_inserts"))
    assert all(not costs.finish_rates[k].verified for k in ("flex_metal_brass_gelcoat", "pigmented_jesmonite_sealed"))


# Runs last: the `client` fixture re-points the database, which the module's project fixture shares.
def test_faro_summary_notes_still_name_its_power_options(client, faro_project):
    notes = client.get(f"/api/projects/{faro_project['id']}/cost-down/summary").json()["notes"]
    assert any("Power options are costed side by side" in n for n in notes)

