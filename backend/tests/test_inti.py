"""INTI: the template carries only the concept's design facts (the rest is TBD), the placeholder CAD builds every
part, and every tab's endpoints work on a project whose dimensions and electronics are still TBD."""

import pytest

from app.cad import inti
from app.products import get_product
from app.rules.data import load_rules
from app.rules.engine import Context, recommend
from app.rules.match import match_finishes
from app.schemas import Requirements
from app.services.templates import load_template

RULES = load_rules()
TPL = load_template("inti")
PARTS = {p["cad_key"]: p for p in TPL["parts"]}
PARAMS = dict(TPL["cad_parameters"])
METAL = ["brow_nose", "eye", "grille", "dial", "top_rim", "base_ring"]


def test_registered_with_speaker_wording():
    p = get_product("inti")
    assert p is not None and p.label == "INTI" and p.noun == "speaker" and p.generator is inti


def test_requirements_leave_unstated_values_tbd():
    """Nothing the concept doesn't give is filled in: dimensions, price, volume, markets and runtime are null."""
    req = Requirements.model_validate(TPL["requirements"])
    assert req.approx_dimensions.height_mm is None and req.approx_dimensions.width_mm is None
    assert req.approx_dimensions.depth_mm is None
    assert req.target_retail_price.amount is None and req.target_unit_cost.amount is None
    assert req.production_volume is None and req.intended_markets == [] and req.battery_runtime_h is None
    assert req.power_type == "battery"  # USB-C is "power and charging"
    text = " ".join(req.functional_requirements)
    for fact in ("Front grille only", "USB-C (power and charging)", "3.5 mm aux", "no separate power jack",
                 "volume control", "real metal"):
        assert fact in text, fact
    assert "battery" not in TPL["electrical"] and "audio" not in TPL  # no invented battery or driver values
    assert TPL["cost_items"] == [] and TPL["joints"] == [] and not TPL.get("scenarios")


def test_parts_follow_the_concept():
    assert set(PARTS) == set(inti.PART_KEYS) and len(PARTS) == len(TPL["parts"])
    assert PARTS["body"]["material_category"] == "composite" and "Jesmonite" in PARTS["body"]["material"]
    assert "non_metallic_look" in PARTS["body"]["traits"]
    assert match_finishes(RULES, PARTS["body"]["finish"])[0] == "wet_lacquer"
    for key in METAL:
        assert PARTS[key]["material_category"] == "brass" and "cosmetic" in PARTS[key]["traits"], key
        # the finish is TBD: nothing that would imply plating, PVD or polish yet
        assert match_finishes(RULES, PARTS[key]["finish"]) == [], key
    assert PARTS["eye"]["quantity"] == 2 and PARTS["dial"]["quantity"] == 2
    assert "rear_grille" not in PARTS


def test_decisions_reference_real_parts_processes_and_materials():
    for d in TPL["decisions"]:
        if "part" in d:
            assert d["part"] in PARTS and d["process"] in RULES.processes and d["material"] in RULES.materials
            assert d["process"] in RULES.materials[d["material"]].processes
    assert [d["part"] for d in TPL["decisions"] if "part" in d] == ["body"]  # metal processes are TBD


@pytest.mark.parametrize("key", METAL)
def test_metal_parts_get_a_real_metal_route(key):
    """The solid-metal constraint applies to every brass/gold part and a metal route exists for each."""
    part = {**PARTS[key], "id": 1, "derived_traits": [], "open_questions": []}
    rec = recommend(RULES, part, Context(power_type="battery", production_volume=None, cad_parameters={}, joints=[]))
    assert rec["viable"], key
    assert not any(c["violations"] for c in rec["constraints"]), key
    assert any(c["key"] == "visible_parts_solid_metal" for c in rec["constraints"])


def test_tbd_list_covers_the_open_points():
    topics = {t["topic"] for t in TPL["tbd"]}
    assert {"Dimensions", "Body", "Metal", "Grille", "Controls", "Rear panel", "Electronics", "Commercial"} <= topics
    assert all(t["item"] and t["why"] for t in TPL["tbd"])
    assert set(inti.TBD_PARAMS) == {d.key for d in inti.PARAMS}  # every CAD default is a placeholder
    assert all(d.help.startswith("TBD") for d in inti.PARAMS)


def test_placeholder_model_builds_every_part():
    assert inti.validate(PARAMS).ok
    parts = inti.build(PARAMS)
    assert set(parts) == set(inti.PART_KEYS)
    for key, s in parts.items():
        assert s.is_valid and s.volume > 0, key
    assert abs(parts["base_ring"].bounding_box().min.Z) < 1e-6
    assert abs(parts["top_rim"].bounding_box().max.Z - PARAMS["overall_height"]) < 0.01
    assert all(c["ok"] for c in inti.production_change_checks(PARAMS)), inti.production_change_checks(PARAMS)
    asm = inti.assembly(parts)
    assert {c.label for c in asm.children} >= {"eye_2", "dial_2"}
    mass = inti.estimate_mass({k: {"volume_mm3": s.volume} for k, s in parts.items()}, {"body": 1.745})
    assert mass["excluded"] == ["driver", "battery", "main_board"]


def test_validation_catches_clashes():
    assert not inti.validate({**PARAMS, "nose_length": 80}).ok  # nose into the grille
    assert not inti.validate({**PARAMS, "eye_spacing": 30}).ok  # eyes into the nose
    assert not inti.validate({**PARAMS, "grille_diameter": 200}).ok
    assert not inti.validate({k: v for k, v in PARAMS.items() if k != "body_width"}).ok


def test_every_tab_works_with_tbd_values(client):
    r = client.post("/api/projects", json={"name": "INTI", "template": "inti"})
    assert r.status_code == 201, r.text
    proj = r.json()
    assert proj["product"]["label"] == "INTI" and proj["product"]["noun"] == "speaker"
    assert "TBD" in proj["product"]["runtime_basis"]
    pid = proj["id"]
    for path in ("/parts", "/runtime", "/audio", "/template-upgrade", "/cad", "/recommendations", "/bom",
                 "/bom.csv", "/costs", "/cost-items", "/cost-settings", "/pricing", "/routes", "/scenarios",
                 "/dfm", "/dfm.md", "/revisions"):
        assert client.get(f"/api/projects/{pid}{path}").status_code == 200, path
    assert client.get(f"/api/projects/{pid}/runtime").json()["applicable"] is False
    summary = client.get(f"/api/projects/{pid}/cost-down/summary")  # needs a retail price, which is TBD
    assert summary.status_code == 409 and "retail price" in summary.text
    pack = client.get(f"/api/projects/{pid}/factory-pack")  # no pack until the dimensions and spec are given
    assert pack.status_code == 409 and "INTI has no Factory Pack yet" in pack.text
    dfm = client.get(f"/api/projects/{pid}/dfm").json()
    titles = [c["title"] for c in dfm["checks"]]
    assert "Placeholder dimensions" in titles and sum(t.startswith("TBD: ") for t in titles) == len(TPL["tbd"])
    assert client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": PARAMS}).status_code in (200, 201)
