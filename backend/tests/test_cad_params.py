import pytest

from app.cad import faro
from app.services.templates import load_template

DEFAULTS = load_template("faro")["cad_parameters"]


def with_(**changes):
    return {**DEFAULTS, **changes}


def errors_for(params, **kw):
    return {e.param for e in faro.validate(params, **kw).errors}


def test_defaults_are_valid():
    res = faro.validate(DEFAULTS)
    assert res.ok, res.as_dict()


def test_all_parameters_have_sane_definitions():
    assert set(DEFAULTS) == set(faro.PARAM_KEYS)
    for d in faro.PARAMS:
        assert d.min < d.max
        assert d.min <= DEFAULTS[d.key] <= d.max, d.key


@pytest.mark.parametrize("key", faro.PARAM_KEYS)
def test_missing_parameter_is_an_error(key):
    params = dict(DEFAULTS)
    del params[key]
    assert key in errors_for(params)


@pytest.mark.parametrize("value", ["abc", None, float("nan"), float("inf")])
def test_non_numeric_rejected(value):
    assert "overall_height" in errors_for(with_(overall_height=value))


def test_range_limits():
    assert "overall_height" in errors_for(with_(overall_height=50))
    assert "overall_height" in errors_for(with_(overall_height=5000))
    assert "mounting_hole_count" in errors_for(with_(mounting_hole_count=3.5))


def test_unknown_parameter_rejected():
    assert "colour" in errors_for(with_(colour=3))


def test_lantern_must_fit_body():
    assert "lantern_diameter" in errors_for(with_(lantern_diameter=140, top_cap_diameter=150))  # > body_diameter
    assert "lantern_diameter" in errors_for(with_(lantern_diameter=105, top_cap_diameter=120))  # > body top
    assert "lantern_diameter" in errors_for(with_(lantern_diameter=100, top_cap_diameter=110))  # no room for the gasket
    assert faro.validate(with_(lantern_diameter=96, top_cap_diameter=110)).ok


def test_body_taper_and_base_relationships():
    assert "body_top_diameter" in errors_for(with_(body_top_diameter=140))
    assert "base_diameter" in errors_for(with_(base_diameter=135))
    assert "top_cap_diameter" in errors_for(with_(top_cap_diameter=91))


def test_body_height_must_remain():
    # base 30 + lantern 80 + cap 45 leaves too little body at 200 mm overall.
    assert "overall_height" in errors_for(with_(overall_height=200))


def test_band_must_fit_on_body():
    assert "band_position" in errors_for(with_(band_position=0.9, band_height=60))


def test_mounting_holes_inside_body_and_clear_of_centre():
    assert "mounting_hole_pcd" in errors_for(with_(mounting_hole_pcd=200))
    assert "mounting_hole_pcd" in errors_for(with_(mounting_hole_pcd=20))
    assert "mounting_hole_count" in errors_for(with_(mounting_hole_count=8, mounting_hole_pcd=30, mounting_hole_diameter=10))


def test_cable_hole_must_fit_base():
    assert "cable_hole_diameter" in errors_for(with_(base_height=12, cable_hole_diameter=10))


def test_wall_thickness_process_limits():
    spinning = faro.WallLimit("Metal spinning", 0.5, 3.0, 1.0, 2.0, verified=False)
    res = faro.validate(with_(wall_thickness=4.0), wall_limits={"main_body": spinning})
    assert any(e.param == "wall_thickness" and "unverified" in e.message for e in res.errors)
    res = faro.validate(with_(wall_thickness=2.5), wall_limits={"main_body": spinning})
    assert res.ok and any(w.param == "wall_thickness" for w in res.warnings)
    assert faro.validate(with_(wall_thickness=1.5), wall_limits={"main_body": spinning}).warnings == []


def test_stability_warning():
    res = faro.validate(with_(overall_height=600), min_stability_ratio=0.35)
    assert res.ok
    assert any(w.param == "base_diameter" for w in res.warnings)


def test_derived_traits_follow_taper():
    assert faro.derived_traits("main_body", DEFAULTS) == ["tapered"]
    assert faro.derived_traits("main_body", with_(body_top_diameter=130)) == ["constant_section"]
    assert faro.derived_traits("lantern", DEFAULTS) == ["constant_section"]


def test_api_validate_and_reject_generation(client, faro_project):
    pid = faro_project["id"]
    state = client.get(f"/api/projects/{pid}/cad").json()
    assert state["validation"]["ok"]
    bad = {**state["parameters"], "lantern_diameter": 200}
    r = client.post(f"/api/projects/{pid}/cad/validate", json={"parameters": bad})
    assert not r.json()["ok"]
    r = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": bad})
    assert r.status_code == 422
    assert r.json()["detail"]["errors"]


def test_process_on_part_sets_wall_limits(client, faro_project):
    pid = faro_project["id"]
    body = next(p for p in client.get(f"/api/projects/{pid}/parts").json() if p["cad_key"] == "main_body")
    client.patch(f"/api/projects/{pid}/parts/{body['id']}", json={"process": "Metal spinning"})
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    r = client.post(f"/api/projects/{pid}/cad/validate", json={"parameters": {**params, "wall_thickness": 5}})
    assert any("Metal spinning" in e["message"] for e in r.json()["errors"])


def test_blank_project_has_no_generator(client):
    pid = client.post("/api/projects", json={"name": "Blank"}).json()["id"]
    assert client.get(f"/api/projects/{pid}/cad").status_code == 404


# --- new construction parameters ------------------------------------------------


def test_new_construction_parameters_are_validated():
    assert "weight_plate_diameter" in errors_for(with_(weight_plate_diameter=178))  # doesn't fit the shell
    assert "weight_plate_diameter" in errors_for(with_(weight_plate_diameter=100))  # misses the rivet-nut screws
    assert "weight_plate_thickness" in errors_for(with_(weight_plate_thickness=22))  # no room for the lamp nut
    assert "dimmer_hole_diameter" in errors_for(with_(dimmer_hole_diameter=3))
    assert "dimmer_hole_diameter" in errors_for(with_(weight_plate_thickness=12))  # dimmer no longer fits below
    assert faro.validate(with_(dimmer_hole_diameter=0, weight_plate_thickness=12)).ok  # touch / inline dimmer
    assert "tube_diameter" in errors_for(with_(tube_diameter=16, body_top_diameter=40, lantern_diameter=30, top_cap_diameter=40))
    assert "target_mass_kg" in errors_for(with_(target_mass_kg=20))
    assert "step_depth" in errors_for(with_(step_depth=8))


def test_derived_construction_dimensions():
    d = faro.derived({k: float(v) for k, v in DEFAULTS.items()})
    assert d["band_inner_diameter"] < DEFAULTS["body_diameter"]
    assert d["glass_in_cap"] >= faro.MIN_GLASS_IN_CAP
    assert d["tube_bottom_z"] > 0 and d["tube_top_z"] > d["cap_top_z"]
    assert d["cap_top_z"] + faro.CAP_NUT_H == pytest.approx(DEFAULTS["overall_height"])


def test_band_is_a_straight_ring_and_mismatch_changes_are_implemented():
    assert faro.derived_traits("band", DEFAULTS) == ["constant_section"]
    bodies = set(faro.PART_KEYS)
    assert faro.implements("thin_shell_needs_mass", "base", bodies)
    assert faro.implements("thin_wall_inserts", "base", bodies)
    assert not faro.implements("casting_draft", "base", bodies)
    assert not faro.implements("thin_shell_needs_mass", "base", {"base", "main_body"})


def test_old_parameters_upgrade_with_new_defaults():
    old = {k: v for k, v in DEFAULTS.items() if k not in ("weight_plate_diameter", "step_depth", "target_mass_kg")}
    old["colour"] = 1
    up = faro.upgrade(old, DEFAULTS)
    assert set(up) == set(faro.PARAM_KEYS) and faro.validate(up).ok


def test_mass_estimate_and_target(client, faro_project):
    pid = faro_project["id"]
    mass = client.get(f"/api/projects/{pid}/cad").json()["mass"]
    assert mass["target_kg"] == DEFAULTS["target_mass_kg"]
    assert 1.0 < mass["total_kg"] < 4.0 and mass["parts_kg"]["weight_plate"] > 0.5
    assert mass["status"] == "ok"
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": {**params, "weight_plate_thickness": 3, "target_mass_kg": 3}})
    assert client.get(f"/api/projects/{pid}/cad").json()["mass"]["status"] == "low"
