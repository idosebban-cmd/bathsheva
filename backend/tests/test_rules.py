import shutil
from pathlib import Path

import pytest
import yaml

from app.ai.provider import Explanation, MockProvider
from app.cad import faro
from app.config import SEED_DIR
from app.rules.data import RulesDataError, load_rules, load_rules_from
from app.rules.engine import Context, recommend
from app.rules.match import match_finishes, match_material, match_process
from app.services.templates import load_template

RULES = load_rules()
TEMPLATE = load_template("faro")
PARAMS = TEMPLATE["cad_parameters"]
PARTS = {p["cad_key"]: p for p in TEMPLATE["parts"]}


def faro_part(key, **overrides):
    part = {**PARTS[key], "id": 1, "derived_traits": faro.derived_traits(key, PARAMS), **overrides}
    return part


def ctx(**kw):
    return Context(**{"cad_parameters": PARAMS, "joints": TEMPLATE["joints"], **kw})


# --- seed data provenance -------------------------------------------------


def test_every_seed_entry_has_provenance():
    for path in (SEED_DIR / "rules").glob("*.yaml"):
        doc = yaml.safe_load(path.read_text())
        (entries,) = doc.values()
        for entry in entries:
            assert entry.get("source"), (path.name, entry)
            assert entry.get("confidence") in ("low", "medium", "high"), (path.name, entry)
            assert "verified" in entry, (path.name, entry)


def test_model_generated_data_is_not_marked_verified():
    for coll in (RULES.processes, RULES.materials, RULES.finishes, RULES.fasteners, RULES.planning):
        for entry in coll.values():
            if entry.source == "model-generated":
                assert entry.verified is False


def _copy_rules(tmp_path: Path) -> Path:
    d = tmp_path / "rules"
    shutil.copytree(SEED_DIR / "rules", d)
    return d


def test_loader_rejects_missing_provenance(tmp_path):
    d = _copy_rules(tmp_path)
    doc = yaml.safe_load((d / "processes.yaml").read_text())
    del doc["processes"][0]["source"]
    (d / "processes.yaml").write_text(yaml.safe_dump(doc))
    with pytest.raises(RulesDataError, match="source"):
        load_rules_from(d)


def test_loader_defaults_verified_false(tmp_path):
    d = _copy_rules(tmp_path)
    doc = yaml.safe_load((d / "fasteners.yaml").read_text())
    del doc["fasteners"][0]["verified"]
    (d / "fasteners.yaml").write_text(yaml.safe_dump(doc))
    assert load_rules_from(d).fasteners[doc["fasteners"][0]["key"]].verified is False


def test_loader_rejects_dangling_references(tmp_path):
    d = _copy_rules(tmp_path)
    doc = yaml.safe_load((d / "materials.yaml").read_text())
    doc["materials"][0]["processes"].append("teleportation")
    (d / "materials.yaml").write_text(yaml.safe_dump(doc))
    with pytest.raises(RulesDataError, match="teleportation"):
        load_rules_from(d)


# --- matching ---------------------------------------------------------------


def test_text_matching():
    assert match_process(RULES, "Metal spinning") == "metal_spinning"
    assert match_process(RULES, "cnc machining") == "cnc_machining"
    assert match_process(RULES, "") is None
    assert match_material(RULES, "Aluminium 6061 (T6)") == "al_6061"
    assert match_finishes(RULES, "Coloured lacquer or brass-plated") == ["wet_lacquer", "brass_plating"]


# --- recommendations --------------------------------------------------------


def test_every_faro_part_gets_a_complete_card():
    for key in PARTS:
        rec = recommend(RULES, faro_part(key), ctx())
        assert rec["status"] == "ok", key
        for field in ("summary", "reason", "assumptions", "confidence", "alternatives", "open_questions", "sources"):
            assert field in rec, (key, field)
        assert rec["confidence"] in ("low", "medium", "high")
        assert rec["reason"] and rec["assumptions"]
        assert rec["uses_unverified_data"] is True  # all seed data is model-generated


def test_tapered_spun_body_and_no_extrusion():
    rec = recommend(RULES, faro_part("main_body"), ctx())
    assert rec["recommendation"]["process_key"] == "metal_spinning"
    assert any(e["process_key"] == "extrusion" for e in rec["excluded"])


def test_straight_body_makes_extrusion_viable_at_volume():
    straight = {**PARAMS, "body_top_diameter": PARAMS["body_diameter"]}
    part = faro_part("main_body", derived_traits=faro.derived_traits("main_body", straight))
    rec = recommend(RULES, part, ctx(cad_parameters=straight, production_volume=20000))
    assert rec["recommendation"]["process_key"] == "extrusion"
    assert rec["recommendation"]["material_key"] in ("al_6063", "al_6061")


def test_volume_changes_base_recommendation():
    low = recommend(RULES, faro_part("base"), ctx(production_volume=100))
    high = recommend(RULES, faro_part("base"), ctx(production_volume=50000))
    assert low["recommendation"]["process_key"] == "cnc_machining"
    assert high["recommendation"]["process_key"] == "die_casting"
    assert high["recommendation"]["material_key"] == "al_a380"


def test_unknown_volume_is_an_explicit_assumption_and_lowers_confidence():
    rec = recommend(RULES, faro_part("base"), ctx(production_volume=None))
    assert rec["inputs"]["volume_assumed"]
    assert any("assumes about 500 units" in a for a in rec["assumptions"])
    assert rec["confidence"] == "low"
    assert any("production volume" in q.lower() for q in rec["open_questions"])


def test_volume_insensitive_parts_do_not_lean_on_assumed_volume():
    rec = recommend(RULES, faro_part("led_module"), ctx())
    assert rec["recommendation"]["process_key"] == "bought_in"
    assert not any(s["key"] == "assumed_volume_when_unknown" for s in rec["sources"])
    assert rec["confidence"] == "medium"  # capped: unverified data


def test_wall_thickness_outside_process_range_penalised():
    thick = {**PARAMS, "wall_thickness": 8}
    rec = recommend(RULES, faro_part("main_body"), ctx(cad_parameters=thick))
    assert rec["recommendation"]["process_key"] != "metal_spinning"


def test_confidence_never_high_on_unverified_data():
    for key in PARTS:
        rec = recommend(RULES, faro_part(key), ctx(production_volume=1000))
        assert rec["confidence"] != "high"


def test_technical_details_present():
    body = recommend(RULES, faro_part("main_body"), ctx())
    assert "wall_thickness" in body["technical"] and "tolerances" in body["technical"]
    assert any("base" in f for f in body["technical"]["fastening"])
    cast = recommend(RULES, faro_part("base"), ctx(production_volume=50000))
    assert "draft_angles" in cast["technical"]


# --- safety -----------------------------------------------------------------


def flags(rec):
    return {f["key"] for f in rec["safety_flags"]}


def test_safety_flags():
    assert {"electrical_component", "cable_anchorage"} <= flags(recommend(RULES, faro_part("cable"), ctx()))
    assert "exposed_metal_mains" in flags(recommend(RULES, faro_part("main_body"), ctx(power_type="mains")))
    assert "exposed_metal_mains" in flags(recommend(RULES, faro_part("main_body"), ctx(power_type="undecided")))
    assert "exposed_metal_mains" not in flags(recommend(RULES, faro_part("main_body"), ctx(power_type="battery")))
    assert "battery" in flags(recommend(RULES, faro_part("led_module"), ctx(power_type="battery")))
    assert "battery" not in flags(recommend(RULES, faro_part("led_module"), ctx(power_type="mains")))
    assert "stability" in flags(recommend(RULES, faro_part("base"), ctx()))


def test_polymer_lantern_flagged_glass_lantern_flagged_differently():
    rec = recommend(RULES, faro_part("lantern"), ctx(production_volume=200))
    if rec["recommendation"]["material_key"] in ("pmma", "pc"):
        assert "polymer_near_heat" in flags(rec)
    glass = recommend(RULES, faro_part("lantern"), ctx(production_volume=50000))
    assert glass["recommendation"]["material_key"] == "borosilicate"
    assert "glass_breakage" in flags(glass) and "polymer_near_heat" not in flags(glass)


def test_no_match_for_unknown_category():
    rec = recommend(RULES, {"id": 9, "name": "Mystery", "material_category": "unobtainium", "traits": []}, Context())
    assert rec["status"] == "no_match" and rec["recommendation"] is None


# --- LLM layer --------------------------------------------------------------


def test_mock_provider_explains_without_changing_recommendation():
    rec = recommend(RULES, faro_part("cable"), ctx())
    exp = MockProvider().explain(rec)
    assert isinstance(exp, Explanation)
    assert rec["recommendation"]["process_name"] in exp.plain_summary
    assert any("Safety" in c for c in exp.caveats)


# --- API --------------------------------------------------------------------


def test_recommendations_and_decisions_api(client, faro_project):
    pid = faro_project["id"]
    data = client.get(f"/api/projects/{pid}/recommendations").json()
    assert len(data["recommendations"]) == 7
    assert data["open_decisions"][0]["topic"] == "power_type" and data["open_decisions"][0]["open"]
    body = next(r for r in data["recommendations"] if r["part_key"] == "main_body")

    r = client.post(f"/api/projects/{pid}/decisions", json={"part_id": body["part_id"], "status": "accepted", "recommendation": body})
    assert r.status_code == 201
    part = next(p for p in client.get(f"/api/projects/{pid}/parts").json() if p["id"] == body["part_id"])
    assert part["process"] == "Metal spinning"

    r = client.post(f"/api/projects/{pid}/decisions", json={
        "part_id": body["part_id"], "status": "edited", "recommendation": body,
        "chosen": {"material": "Aluminium 3003 (H14)", "process": "Metal spinning"}, "note": "supplier preference",
    })
    assert r.json()["status"] == "edited"
    rec = next(r for r in client.get(f"/api/projects/{pid}/recommendations").json()["recommendations"] if r["part_id"] == body["part_id"])
    assert rec["decision"]["status"] == "edited"
    # Accepting spinning now applies spinning wall limits in CAD validation.
    assert client.get(f"/api/projects/{pid}/cad").json()["wall_limits"]["main_body"]["process_name"] == "Metal spinning"

    r = client.post(f"/api/projects/{pid}/decisions", json={"topic": "power_type", "status": "accepted", "chosen": {"value": "mains"}})
    assert r.status_code == 201
    assert client.get(f"/api/projects/{pid}").json()["requirements"]["power_type"] == "mains"


def test_explain_endpoint_uses_mock_provider(client, faro_project):
    pid = faro_project["id"]
    recs = client.get(f"/api/projects/{pid}/recommendations").json()
    assert recs["llm"] == {"enabled": True, "provider": "mock"}
    r = client.post(f"/api/projects/{pid}/recommendations/{recs['recommendations'][0]['part_id']}/explain")
    assert r.status_code == 200 and r.json()["provider"] == "mock"


def test_app_works_with_llm_disabled(client, faro_project, monkeypatch):
    from app.ai import provider as prov
    from app.api import engineering

    disabled = prov.settings.__class__(**{**prov.settings.__dict__, "llm_provider": "none"})
    monkeypatch.setattr(prov, "settings", disabled)
    monkeypatch.setattr(engineering, "settings", disabled)
    pid = faro_project["id"]
    recs = client.get(f"/api/projects/{pid}/recommendations").json()
    assert recs["llm"]["enabled"] is False and len(recs["recommendations"]) == 7
    r = client.post(f"/api/projects/{pid}/recommendations/{recs['recommendations'][0]['part_id']}/explain")
    assert r.status_code == 503
