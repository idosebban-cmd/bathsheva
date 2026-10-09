"""Atelier CAD: parameters, geometry against the Technical Specification, stability, the API and the DFM report.

The model takes about two minutes to build (one build per parameter set, cached), so most tests share the
plain-grille build; one test builds the honeycomb grilles.
"""

import json

import pytest

from app.cad import atelier
from app.services.templates import load_template

DEFAULTS = dict(load_template("atelier")["cad_parameters"])
PLAIN = {**DEFAULTS, "grille_perforated": 0}


def with_(**kw):
    return {**PLAIN, **kw}


def errors(params):
    return {e.param for e in atelier.validate(params).errors}


def test_defaults_validate_without_spec_warnings():
    res = atelier.validate(DEFAULTS)
    assert res.ok and res.warnings == []


def test_validation_ranges_and_rules():
    assert "overall_height" in errors(with_(overall_height=500))
    assert "grille_thickness" in errors(with_(grille_thickness=0.8))  # webs 0.7: photo-etch limit
    assert "grille_diameter" in errors(with_(grille_diameter=60))  # the driver can't pass the sound opening
    assert "fin_tip_radius" in errors(with_(fin_tip_radius=65, body_max_diameter=100))
    assert "grille_perforated" in errors(with_(grille_perforated=0.5))
    warned = {w.param for w in atelier.validate(with_(overall_height=285, body_max_diameter=97)).warnings}
    assert {"overall_height", "body_max_diameter"} <= warned


def test_normalise_upgrade_and_scaling_sets():
    assert atelier.normalise(PLAIN)["grille_perforated"] == 0
    old = {k: v for k, v in DEFAULTS.items() if k != "pr_width"}
    assert atelier.upgrade(old, DEFAULTS)["pr_width"] == DEFAULTS["pr_width"]
    assert atelier.UNSCALED_PARAMS <= set(atelier.PARAM_KEYS)


@pytest.fixture(scope="module")
def built():
    return atelier.model(PLAIN), atelier.stability(PLAIN)


def test_one_valid_body_per_part(built):
    m, _ = built
    assert set(m.parts) == set(atelier.PART_KEYS)
    for key, shape in m.parts.items():
        assert shape.is_valid and shape.volume > 0, key
    assert len(m.instances["fin"]) == 2 and len(m.instances["fin_pad"]) == 2
    tpl = load_template("atelier")
    assert {p["cad_key"] for p in tpl["parts"]} == set(atelier.PART_KEYS)


def test_meets_the_technical_specification(built):
    m, s = built
    assert 279 <= s["height_mm"] <= 281
    assert abs(m.parts["body"].bounding_box().size.X - 95) < 0.3
    assert 1700 <= s["total_g"] <= 1900
    assert s["com_mm"][2] <= 98
    assert s["tip_deg"] >= 18
    assert 130 <= s["footprint_mm"][0] <= 145  # fin span about 140
    assert 0.70 <= s["air_l"] <= 0.80
    assert abs(m.parts["foot"].bounding_box().min.Z - 2.0) < 0.05  # foot 2 mm off the ground
    assert m.parts["fin_pad"].bounding_box().min.Z < 0.01 and abs(m.parts["fin"].bounding_box().min.Z - 1.0) < 0.05


def test_every_production_change_check_passes(built):
    checks = atelier.production_change_checks(PLAIN)
    assert [c["feature"] for c in checks if not c["ok"]] == []
    assert {"Mass", "Centre of mass", "Stability", "Passive radiator", "Knob", "Name", "Base collar"} <= {c["feature"] for c in checks}


def test_collar_fixings_hidden_under_the_foot_and_lettering_round_it(built):
    m, _ = built
    I = m.info
    foot_r = I["foot_dia"] / 2
    for x, y in I["collar_screw_xy"]:
        assert (x * x + y * y) ** 0.5 + atelier.COLLAR_SCREW_HEAD / 2 < foot_r
    assert foot_r < I["collar_lettering_radius"] < I["collar_bottom_dia"] / 2
    assert I["collar_lettering_mm3"] > 0.3
    # the tray plate's two screws sit outside the battery's footprint, so the plate drops out with the battery
    bat = m.parts["battery"].bounding_box()
    assert len(I["tray_screw_xy"]) == 2
    for x, y in I["tray_screw_xy"]:
        outside_x = abs(x) - atelier.COLLAR_SCREW_HEAD / 2 > bat.size.X / 2
        outside_y = abs(y) - atelier.COLLAR_SCREW_HEAD / 2 > bat.size.Y / 2
        assert outside_x or outside_y
        assert (x * x + y * y) ** 0.5 + atelier.COLLAR_SCREW_HEAD / 2 < m.info["ballast_dia"] / 2
    assert "collar_etch_floor" in m.preview and "knob_logo_floor" in m.preview


def test_assembly_and_preview_have_all_three_fins(built):
    m, _ = built
    asm = atelier.assembly(m.parts)
    labels = {c.label for c in asm.children}
    assert {"fin", "fin_2", "fin_3", "fin_pad", "fin_pad_2", "fin_pad_3"} <= labels
    extras = atelier.preview_extras(PLAIN)
    assert {"fin_2", "fin_3", "knob_logo_floor", "collar_etch_floor", "led"} <= set(extras)
    est = atelier.estimate_mass({"fin": {"volume_mm3": 1000.0}}, {"fin": 6.7})
    assert est["parts_kg"]["fin"] == pytest.approx(3 * 0.0067, abs=0.001)  # rounded to grams
    assert "damping_pads_and_usb" not in est["parts_kg"]
    with_body = atelier.estimate_mass({"body": {"volume_mm3": 1000.0}}, {"body": 1.15})
    assert with_body["parts_kg"]["damping_pads_and_usb"] == pytest.approx(0.053)  # as stability() counts them


def test_collar_lettering_matches_the_font():
    from app.factory import nameplate as art

    stored = json.loads(atelier.COLLAR_LETTERING_FILE.read_text())
    assert stored["text"] == "ATELIER"
    fresh = art._loops_of(art.letters_from_font("ATELIER"))
    assert len(fresh) == len(stored["letters"])
    for a, b in zip(fresh, stored["letters"]):
        assert len(a) == len(b) and all(len(la) == len(lb) for la, lb in zip(a, b))


def test_honeycomb_grilles():
    m = atelier.model(DEFAULTS)
    plain = atelier.model(PLAIN)
    for key in ("grille", "rear_grille"):
        assert m.parts[key].is_valid
        assert m.parts[key].volume < 0.75 * plain.parts[key].volume  # holes cut
    assert [c["feature"] for c in atelier.production_change_checks(DEFAULTS) if not c["ok"]] == []


def test_atelier_project_api_and_dfm(client):
    r = client.post("/api/projects", json={"name": "Atelier", "template": "atelier"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    state = client.get(f"/api/projects/{pid}/cad").json()
    assert state["product"]["label"] == "Atelier" and state["generator"] == "atelier"
    assert state["validation"]["ok"] and len(state["production_changes"]) == len(atelier.PRODUCTION_CHANGES)
    assert state["wall_limits"]["body"]["process_name"].startswith("Injection moulding")
    r = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": PLAIN})
    assert r.status_code == 201, r.text
    assert {"fin", "collar", "knob", "body"} <= set(r.json()["part_info"])
    dfm = client.get(f"/api/projects/{pid}/dfm").json()
    titles = {c["title"]: c for c in dfm["checks"]}
    for t in ("Mass vs target", "Centre of mass", "Stability (static tip-over)", "Air volume"):
        assert titles[t]["level"] == "pass", (t, titles[t])
    assert titles["Playback time at 50% volume"]["level"] == "pass"
    assert any(c["title"] == "Open item" for c in dfm["checks"])
    assert titles["Battery replacement (standard tools)"]["level"] == "pass"
    assert "1.5 mm hex key" in titles["Battery replacement (standard tools)"]["detail"]
    risk = titles["Risk: mass margin"]  # the ballast is at its largest size: flagged until supplier weights arrive
    assert risk["level"] == "warning" and "Recheck once supplier part weights arrive" in risk["detail"]
    mass = client.get(f"/api/projects/{pid}/cad").json()["mass"]
    assert 1.6 <= mass["total_kg"] <= 2.0
    au = client.get(f"/api/projects/{pid}/audio").json()
    assert au["applicable"] and 0.70 <= au["box_l"] <= 0.80 and au["spl_ok"] and au["charge_ok"] and au["current_ok"]
    for t in ("Loudness (amplifier-limited)", "20 W from a 1S battery", "Charge time"):
        assert titles[t]["level"] == "pass", (t, titles[t])
    assert {"Bass at full volume (excursion)", "Box and radiator tuning"} <= set(titles)
    rt = client.get(f"/api/projects/{pid}/runtime").json()
    assert rt["hours"] >= 15 and rt["without_tower_light_h"] is None
    # Atelier has its own factory pack (tests/test_atelier_factory_pack.py), never Faro's
    pack = client.get(f"/api/projects/{pid}/factory-pack")
    assert pack.status_code == 200 and all(pt["part_no"].startswith("A-") for pt in pack.json()["parts"])


def test_jesmonite_body_variant_keeps_the_mass():
    """A 5 mm Jesmonite body: the ballast is re-sized to keep 1.8 kg, and the cost model's volume scale matches."""
    base = atelier.stability(PLAIN)
    jes = atelier.stability(PLAIN, ("jesmonite_body",))
    both = atelier.stability(PLAIN, ("jesmonite_body", "brass_metalwork"))
    for s in (jes, both):
        assert abs(s["total_g"] - 1800) < 15, s["total_g"]
        assert 0 < s["ballast_g"] <= s["ballast_max_g"]
        lo, hi = atelier.SPEC["mass_g"]
        assert lo <= s["total_g"] <= hi and s["tip_deg"] >= atelier.SPEC["tip_min_deg"]
        assert s["com_mm"][2] <= atelier.SPEC["com_max_mm"]
    rows = {r["part"]: r["mass_g"] for r in jes["parts"]}
    assert rows["cast-in brass inserts"] == atelier.JESMONITE_INSERTS_G
    assert jes["ballast_g"] < base["ballast_g"] and jes["com_mm"][2] > base["com_mm"][2]  # heavier body, higher CoM
    # volume_scale in atelier.yaml = body volume at 5 mm / at 3 mm
    from app.services.templates import load_template

    sc = next(d for d in load_template("atelier")["scenarios"] if d["key"] == "jesmonite_body")
    v3 = {r["part"]: r["mass_g"] for r in base["parts"]}["body"] / atelier.DENSITY["pc_abs"]
    v5 = rows["body"] / atelier.DENSITY["jesmonite_ac100"]
    assert sc["effect"]["volume_scale"]["body"] == pytest.approx(v5 / v3, rel=0.01)
