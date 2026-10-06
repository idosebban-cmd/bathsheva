"""Battery runtime estimate and the template upgrade for projects made from the old Faro."""

import pytest

from app import electrical
from app.models import Part, Project
from app.services.templates import load_template

SPEC = load_template("faro")["electrical"]


def test_runtime_formula():
    spec = {"battery": {"cells": 2, "cell_capacity_mah": 3000, "cell_voltage": 3.6, "usable_fraction": 1.0},
            "driver_efficiency": 1.0, "loads": [{"name": "LED", "part": "a", "watts": 2.16}]}
    est = electrical.estimate(spec, target_h=10)
    assert est["battery_wh"] == pytest.approx(21.6)
    assert est["hours"] == pytest.approx(10.0) and est["status"] == "pass"
    assert electrical.estimate(spec, target_h=10.5)["status"] == "close"  # within 10 %
    assert electrical.estimate(spec, target_h=20)["status"] == "fail"
    assert electrical.estimate(spec, removed_parts={"a"})["hours"] is None  # nothing to power
    assert electrical.estimate(spec)["status"] == "unknown"  # no target


def test_faro_runtime_meets_the_8_hour_target():
    est = electrical.estimate(SPEC, target_h=8)
    assert est["load_w"] == pytest.approx(2.3)  # lantern 1.5 W + tower light 0.8 W
    assert 8.0 <= est["hours"] < 9 and est["status"] == "pass"
    assert est["unverified"]
    lantern_only = electrical.estimate(SPEC, target_h=8, removed_parts={"tower_light"})
    assert lantern_only["hours"] > est["hours"]


def test_runtime_api_and_compliance(client, faro_project):
    pid = faro_project["id"]
    rt = client.get(f"/api/projects/{pid}/runtime").json()
    assert rt["applicable"] and rt["target_h"] == 8 and rt["status"] == "pass"
    assert rt["without_tower_light_h"] > rt["hours"]
    text = " ".join(rt["compliance"])
    for needle in ("protection circuit", "UN38.3", "IEC 62133", "2023/1542", "replaceable"):
        assert needle in text, needle
    # The runtime target is an editable requirement.
    req = client.get(f"/api/projects/{pid}").json()["requirements"]
    client.patch(f"/api/projects/{pid}", json={"requirements": {**req, "battery_runtime_h": 12}})
    assert client.get(f"/api/projects/{pid}/runtime").json()["status"] == "fail"
    client.patch(f"/api/projects/{pid}", json={"requirements": {**req, "power_type": "mains"}})
    assert client.get(f"/api/projects/{pid}/runtime").json()["applicable"] is False


def test_template_upgrade_replaces_old_faro_parts(client, faro_project):
    from app.db import new_session

    pid = faro_project["id"]
    assert client.get(f"/api/projects/{pid}/template-upgrade").json()["needed"] is False
    # Make it look like a project created from the pre-prototype template.
    session = new_session()
    project = session.get(Project, pid)
    for part in list(project.parts):
        if part.cad_key in ("tower", "gallery", "cap"):
            session.delete(part)
    project.parts.append(Part(cad_key="main_body", name="Main body", material_category="aluminium", sort_order=99))
    project.requirements = {**project.requirements, "power_type": "undecided", "approx_dimensions": {}}
    project.assumed_fields = [*project.assumed_fields, "approx_dimensions"]
    session.commit()
    body_id = next(p.id for p in project.parts if p.cad_key == "main_body")
    session.close()
    client.post(f"/api/projects/{pid}/parts/{body_id}/quotes", data={
        "source": "Spinner", "quote_date": "2026-10-01", "quantity": "100", "unit_price": "30"})

    plan = client.get(f"/api/projects/{pid}/template-upgrade").json()
    assert plan["needed"]
    assert plan["remove"] == [{"cad_key": "main_body", "name": "Main body", "quotes": 1}]
    assert {a["cad_key"] for a in plan["add"]} == {"tower", "gallery", "cap"}
    assert {"approx_dimensions", "power_type"} <= set(plan["requirements"])

    r = client.post(f"/api/projects/{pid}/template-upgrade")
    assert r.status_code == 200 and r.json()["done"]
    parts = client.get(f"/api/projects/{pid}/parts").json()
    from app.cad import faro

    assert [p["cad_key"] for p in sorted(parts, key=lambda p: p["sort_order"])] == faro.PART_KEYS
    assert next(p for p in parts if p["cad_key"] == "tower")["process"] == "Metal spinning"  # decision re-applied
    proj = client.get(f"/api/projects/{pid}").json()
    assert proj["requirements"]["power_type"] == "battery" and proj["requirements"]["approx_dimensions"]["height_mm"] == 300
    assert "approx_dimensions" not in proj["assumed_fields"]
    assert client.get(f"/api/projects/{pid}/template-upgrade").json()["needed"] is False
    assert any(i["price_key"] == "battery_pack" for i in client.get(f"/api/projects/{pid}/cost-items").json())


def test_template_upgrade_offered_when_only_decisions_changed(client, faro_project):
    """A project made before the near-net and spun-gallery decisions gets them through the same upgrade."""
    from app.db import new_session
    from app.models import EngineeringDecision

    pid = faro_project["id"]
    session = new_session()
    project = session.get(Project, pid)
    gallery = next(p for p in project.parts if p.cad_key == "gallery")
    for d in list(project.decisions):
        if d.part_id == gallery.id:
            session.delete(d)
    session.commit()
    session.close()
    client.delete(f"/api/projects/{pid}/cost-items/" + str(next(
        i["id"] for i in client.get(f"/api/projects/{pid}/cost-items").json() if i["price_key"] == "lamp_safety_emc_testing")))

    plan = client.get(f"/api/projects/{pid}/template-upgrade").json()
    assert plan["needed"] and not plan["remove"] and not plan["add"]
    assert plan["decisions"] == ["Gallery: metal spinning (brass)"]
    assert client.post(f"/api/projects/{pid}/template-upgrade").json()["done"]
    assert client.get(f"/api/projects/{pid}/template-upgrade").json()["needed"] is False
    session = new_session()
    ds = session.query(EngineeringDecision).filter_by(project_id=pid, part_id=gallery.id).all()
    assert [d.chosen["process_key"] for d in ds] == ["metal_spinning"]
    session.close()
    assert any(i["price_key"] == "lamp_safety_emc_testing" for i in client.get(f"/api/projects/{pid}/cost-items").json())


def test_template_upgrade_updates_old_default_finishes_only(client, faro_project):
    from app.db import new_session

    pid = faro_project["id"]
    session = new_session()
    project = session.get(Project, pid)
    by = {p.cad_key: p for p in project.parts}
    by["finial"].finish = "Tumble-polished, clear lacquer"  # an old template default
    by["base"].finish = "Gloss black lacquer, clear-coated"
    by["knob"].finish = "Hand-polished mirror, clear lacquer"  # the user's own choice: never overwritten
    session.commit()
    session.close()
    plan = client.get(f"/api/projects/{pid}/template-upgrade").json()
    assert plan["needed"] and {f["cad_key"] for f in plan["finishes"]} == {"finial", "base"}
    assert client.post(f"/api/projects/{pid}/template-upgrade").json()["done"]
    parts = {p["cad_key"]: p for p in client.get(f"/api/projects/{pid}/parts").json()}
    assert parts["finial"]["finish"] == "Brushed (satin), clear lacquer"
    assert parts["base"]["finish"].startswith("Satin black lacquer")
    assert parts["knob"]["finish"] == "Hand-polished mirror, clear lacquer"
    assert client.get(f"/api/projects/{pid}/template-upgrade").json()["needed"] is False


def test_brushed_brass_matches_its_own_finish_and_cost():
    from app.costing.data import load_cost_data
    from app.rules.data import load_rules
    from app.rules.match import match_finishes

    rules = load_rules()
    assert match_finishes(rules, "Brushed (satin), clear lacquer")[0] == "brushed_lacquer"
    assert match_finishes(rules, "Satin black lacquer (30–50 GU), clear-coated")[0] == "wet_lacquer"
    assert "brushed_lacquer" in load_cost_data().finish_rates
    assert rules.materials["brass"].finish_compat["brushed_lacquer"] == "good"
