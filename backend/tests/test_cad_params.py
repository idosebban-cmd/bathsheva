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
    assert "window_count" in errors_for(with_(window_count=3.5))


def test_unknown_parameter_rejected():
    assert "colour" in errors_for(with_(colour=3))


def test_lantern_gallery_and_cap_relationships():
    assert "gallery_diameter" in errors_for(with_(gallery_diameter=60))  # lantern + railing don't fit
    assert "lantern_diameter" in errors_for(with_(lantern_diameter=36))  # LED ledge / LED access
    assert "cap_rim_diameter" in errors_for(with_(cap_rim_diameter=56))  # no overhang over the lantern
    assert "cap_dome_diameter" in errors_for(with_(cap_dome_diameter=70))  # wider than the rim allows
    assert "cap_dome_diameter" in errors_for(with_(cap_dome_diameter=50))  # bayonet spigot can't fit inside
    assert "glass_wall_thickness" in errors_for(with_(glass_wall_thickness=4.5))  # glass inside the gallery bore
    assert faro.validate(with_(lantern_diameter=60, cap_rim_diameter=76, cap_dome_diameter=63)).ok


def test_tower_and_base_relationships():
    assert "tower_top_diameter" in errors_for(with_(tower_top_diameter=95))
    assert "band_diameter" in errors_for(with_(band_diameter=93))  # band must show around the tower foot
    assert "band_diameter" in errors_for(with_(band_diameter=110))  # beyond the base's flat top
    assert "base_height" in errors_for(with_(base_height=20))  # the battery no longer fits
    assert "weight_plate_thickness" in errors_for(with_(weight_plate_thickness=14))  # clashes with the USB-C board
    assert "red_section_height" in errors_for(with_(red_section_height=160))


def test_tower_height_must_remain():
    assert "overall_height" in errors_for(with_(overall_height=200, lantern_height=60))


def test_windows_validated():
    assert "window_last_z" in errors_for(with_(window_last_z=200))  # above the diffuser top
    assert "window_first_z" in errors_for(with_(window_first_z=40))  # below the tower foot
    assert "window_width" in errors_for(with_(window_width=25))  # wider than tall
    assert "knob_z" in errors_for(with_(knob_z=113))  # overlaps the first (front) window
    assert faro.validate(with_(window_count=0)).ok
    assert faro.validate(with_(window_count=3, window_turn_deg=120)).ok


def test_dimmer_needs_room_behind_the_knob():
    assert "knob_z" in errors_for(with_(knob_z=180, window_count=0))  # the tower is too narrow up there


def test_wall_thickness_process_limits():
    spinning = faro.WallLimit("Metal spinning", 0.5, 3.0, 1.0, 2.0, verified=False)
    res = faro.validate(with_(wall_thickness=3.0), wall_limits={"tower": faro.WallLimit("Metal spinning", 0.5, 2.5, 1.0, 2.0)})
    assert any(e.param == "wall_thickness" for e in res.errors)
    res = faro.validate(with_(wall_thickness=0.4), wall_limits={"tower": spinning})
    assert any(e.param == "wall_thickness" for e in res.errors)  # also below the parameter minimum
    res = faro.validate(with_(wall_thickness=2.5), wall_limits={"tower": spinning})
    assert res.ok and any(w.param == "wall_thickness" and "unverified" in w.message for w in res.warnings)
    assert faro.validate(with_(wall_thickness=1.5), wall_limits={"tower": spinning}).warnings == []


def test_stability_warning():
    res = faro.validate(with_(overall_height=450), min_stability_ratio=0.35)
    assert res.ok
    assert any(w.param == "base_diameter" for w in res.warnings)


def test_derived_traits_follow_taper():
    assert faro.derived_traits("tower", DEFAULTS) == ["tapered", "side_hole"]
    assert faro.derived_traits("tower", with_(tower_top_diameter=92, window_count=0)) == ["constant_section"]
    assert faro.derived_traits("lantern_glass", DEFAULTS) == ["constant_section"]


def test_api_validate_and_reject_generation(client, faro_project):
    pid = faro_project["id"]
    state = client.get(f"/api/projects/{pid}/cad").json()
    assert state["validation"]["ok"]
    bad = {**state["parameters"], "lantern_diameter": 150}
    r = client.post(f"/api/projects/{pid}/cad/validate", json={"parameters": bad})
    assert not r.json()["ok"]
    r = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": bad})
    assert r.status_code == 422
    assert r.json()["detail"]["errors"]


def test_process_on_part_sets_wall_limits(client, faro_project):
    pid = faro_project["id"]
    tower = next(p for p in client.get(f"/api/projects/{pid}/parts").json() if p["cad_key"] == "tower")
    assert tower["process"] == "Metal spinning"  # accepted template decision
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    r = client.post(f"/api/projects/{pid}/cad/validate", json={"parameters": {**params, "wall_thickness": 2.5}})
    assert any("Metal spinning" in w["message"] for w in r.json()["warnings"])
    r = client.post(f"/api/projects/{pid}/cad/validate", json={"parameters": {**params, "glass_wall_thickness": 1.2}})
    assert any("glass tube" in e["message"].lower() for e in r.json()["errors"])


def test_blank_project_has_no_generator(client):
    pid = client.post("/api/projects", json={"name": "Blank"}).json()["id"]
    assert client.get(f"/api/projects/{pid}/cad").status_code == 404


# --- construction -------------------------------------------------------------------


def test_derived_construction_dimensions():
    d = faro.derived({k: float(v) for k, v in DEFAULTS.items()})
    assert d["tower_bottom_z"] == pytest.approx(33) and d["tower_top_z"] == pytest.approx(197)
    assert d["cap_top_z"] + DEFAULTS["finial_height"] == pytest.approx(DEFAULTS["overall_height"])
    assert d["glass_od"] < DEFAULTS["lantern_diameter"] and d["glass_inner_r"] > d["gallery_bore_r"] - 1
    assert d["led_access_dia"] > faro.LED_BOARD_D  # the LED lifts out with the cap off
    assert d["diffuser_top_z"] > DEFAULTS["window_last_z"] + DEFAULTS["window_height"] / 2
    assert d["base_inner_height"] > faro.BATTERY[2]


def test_production_changes_listed_and_mismatch_changes_are_implemented():
    features = {c["feature"] for c in faro.PRODUCTION_CHANGES}
    assert {"Window diffusers", "Railing", "Cap twist-lock", "Shell walls", "Nameplate"} <= features
    bodies = set(faro.PART_KEYS)
    assert faro.implements("thin_shell_needs_mass", "base", bodies)
    assert faro.implements("thin_wall_inserts", "base", bodies)
    assert not faro.implements("casting_draft", "base", bodies)
    assert not faro.implements("thin_shell_needs_mass", "base", {"base", "tower"})


def test_old_parameters_upgrade_with_new_defaults():
    old = {k: v for k, v in DEFAULTS.items() if k not in ("railing_posts", "target_mass_kg")}
    old["colour"] = 1
    up = faro.upgrade(old, DEFAULTS)
    assert set(up) == set(faro.PARAM_KEYS) and faro.validate(up).ok


def test_pre_prototype_parameters_are_replaced_by_the_defaults():
    old_faro = {"overall_height": 420, "base_diameter": 180, "body_diameter": 130, "body_top_diameter": 100,
                "lantern_diameter": 90, "top_cap_diameter": 110, "wall_thickness": 2.0}
    assert faro.upgrade(old_faro, DEFAULTS) == {k: DEFAULTS[k] for k in faro.PARAM_KEYS}


def test_mass_estimate_and_target(client, faro_project):
    pid = faro_project["id"]
    mass = client.get(f"/api/projects/{pid}/cad").json()["mass"]
    assert mass["target_kg"] == DEFAULTS["target_mass_kg"]
    assert 1.2 < mass["total_kg"] < 2.0
    assert mass["parts_kg"]["weight_plate"] > 0.3 and mass["parts_kg"]["gallery"] > 0.3  # the two heavy parts
    assert mass["status"] == "high"  # above the 1.2 kg target: reported, not hidden
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": {**params, "target_mass_kg": 1.5}})
    assert client.get(f"/api/projects/{pid}/cad").json()["mass"]["status"] == "ok"
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": {**params, "weight_plate_thickness": 2, "target_mass_kg": 3}})
    assert client.get(f"/api/projects/{pid}/cad").json()["mass"]["status"] == "low"
