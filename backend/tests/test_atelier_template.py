"""The Atelier template against the rules data and the Technical Specification's key values."""

import pytest

from app.rules.data import load_rules
from app.rules.engine import Context, recommend
from app.rules.match import match_finishes
from app.schemas import Requirements
from app.services.templates import load_template

RULES = load_rules()
TPL = load_template("atelier")
PARTS = {p["cad_key"]: p for p in TPL["parts"]}
KNOWN_CATEGORIES = {m.category for m in RULES.materials.values()} | {"bought_in", "electrical"}


def test_requirements_validate_and_carry_the_spec_values():
    req = Requirements.model_validate(TPL["requirements"])
    assert req.approx_dimensions.height_mm == 280
    assert req.target_retail_price.amount == 199
    assert req.power_type == "battery" and req.battery_runtime_h == 15
    assert set(TPL["assumed_fields"]) <= set(Requirements.model_fields)
    assert TPL["cad_parameters"]["body_max_diameter"] == 95 and TPL["cad_parameters"]["wall_thickness"] == 3.0
    assert TPL["cad_parameters"]["target_mass_kg"] == 1.8 and TPL["cad_parameters"]["grille_thickness"] == 0.5
    assert any("Battery replaceable after removing the base collar" in r for r in req.functional_requirements)
    assert not any("doubles as the battery tray" in p.get("function", "") for p in TPL["parts"])


def test_parts_use_known_categories_and_multiples_have_quantities():
    for p in TPL["parts"]:
        assert p["material_category"] in KNOWN_CATEGORIES, p["cad_key"]
    assert PARTS["fin"]["quantity"] == 3 and PARTS["fin_pad"]["quantity"] == 3
    assert len(PARTS) == len(TPL["parts"])  # cad_keys are unique


def test_finishes_follow_the_spec():
    """Every visible metal part is gold PVD; the body is polished gloss lacquer."""
    for key, p in PARTS.items():
        if p["material_category"] in ("aluminium", "brass", "zinc", "stainless"):
            assert match_finishes(RULES, p["finish"])[0] == "gold_pvd", key
    assert match_finishes(RULES, PARTS["body"]["finish"])[0] == "gloss_lacquer_polished"


def test_decisions_reference_real_parts_processes_and_materials():
    for d in TPL["decisions"]:
        if "part" in d:
            assert d["part"] in PARTS
            assert d["process"] in RULES.processes and d["material"] in RULES.materials
            assert RULES.materials[d["material"]].category == PARTS[d["part"]]["material_category"], d["part"]
            assert d["process"] in RULES.materials[d["material"]].processes, d["part"]
    for j in TPL["joints"]:
        assert j["method"] in RULES.fasteners
        assert set(j["between"]) <= set(PARTS)


@pytest.mark.parametrize("key", [k for k, p in PARTS.items() if p["material_category"] not in ("bought_in", "electrical")])
def test_every_made_part_gets_a_route_and_breaks_no_constraint(key):
    part = {**PARTS[key], "id": 1, "derived_traits": [], "open_questions": []}
    rec = recommend(RULES, part, Context(power_type="battery", production_volume=500, cad_parameters={},
                                         joints=TPL["joints"]))
    decided = next(d for d in TPL["decisions"] if d.get("part") == key)
    viable = {v["process_key"] for v in rec["viable"]} | {rec["recommendation"]["process_key"]}
    assert decided["process"] in viable, (key, viable)
    assert not any(c["violations"] for c in rec["constraints"]), key
