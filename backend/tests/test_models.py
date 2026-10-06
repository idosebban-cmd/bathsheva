import pytest
from sqlalchemy.exc import IntegrityError

from app.models import CadModel, Part, Project, Revision
from app.schemas import Requirements
from app.services.projects import create_project


def test_create_faro_from_template(db):
    p = create_project(db, "Faro", template="faro")
    assert p.slug == "faro"
    from app.cad import faro

    assert [part.cad_key for part in p.parts] == faro.PART_KEYS  # one part per CAD body
    # Hidden functional parts are marked hidden; visible brass details are made parts in solid brass.
    by = {part.cad_key: part for part in p.parts}
    assert all("hidden" in by[k].traits for k in ("weight_plate", "base_plate", "felt_pad", "cap_spigot"))
    assert all(by[k].material_category == "brass" for k in ("gallery", "railing", "lantern_frame", "finial", "knob"))
    req = Requirements.model_validate(p.requirements)
    assert req.power_type == "battery" and req.battery_runtime_h == 8
    assert req.production_volume is None
    assert req.intended_markets == ["UK", "EU"]
    # Dimensions follow the approved prototype: confirmed, not a placeholder.
    assert req.approx_dimensions.height_mm == 300 and "approx_dimensions" not in p.assumed_fields
    assert {"production_volume", "target_unit_cost"} <= set(p.assumed_fields)
    # Target retail price was given by the user (Oct 2026), so it is no longer a placeholder.
    assert "target_retail_price" not in p.assumed_fields and req.target_retail_price.amount == 275


def test_multiple_projects_get_unique_slugs(db):
    a = create_project(db, "Faro", template="faro")
    b = create_project(db, "Faro", template="faro")
    c = create_project(db, "Atelier")
    assert len({a.slug, b.slug, c.slug}) == 3
    assert c.parts == []


def test_part_hierarchy_and_cascade_delete(db):
    p = create_project(db, "Thing")
    parent = Part(project_id=p.id, name="Assembly")
    db.add(parent)
    db.commit()
    child = Part(project_id=p.id, name="Child", parent_id=parent.id)
    db.add(child)
    db.commit()
    assert child.parent_id == parent.id
    db.delete(p)
    db.commit()
    assert db.query(Part).count() == 0


def test_cad_version_and_revision_numbers_unique_per_project(db):
    p = create_project(db, "Thing")
    db.add(CadModel(project_id=p.id, version=1, generator="faro", parameters={}))
    db.add(Revision(project_id=p.id, number=1, snapshot={}))
    db.commit()
    db.add(CadModel(project_id=p.id, version=1, generator="faro", parameters={}))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_requirements_schema_rejects_bad_power_type():
    with pytest.raises(ValueError):
        Requirements.model_validate({"power_type": "nuclear"})


def test_project_api_roundtrip(client, faro_project):
    pid = faro_project["id"]
    req = faro_project["requirements"]
    req["production_volume"] = 1000
    r = client.patch(f"/api/projects/{pid}", json={
        "requirements": req,
        "assumed_fields": [f for f in faro_project["assumed_fields"] if f != "production_volume"],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["requirements"]["production_volume"] == 1000
    assert "production_volume" not in body["assumed_fields"]
    assert client.patch(f"/api/projects/{pid}", json={"assumed_fields": ["bogus"]}).status_code == 422


def test_image_upload(client, faro_project):
    pid = faro_project["id"]
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 20
    r = client.post(f"/api/projects/{pid}/images", files={"file": ("render.png", png, "image/png")}, data={"kind": "concept"})
    assert r.status_code == 201, r.text
    img = r.json()
    assert client.get(f"/files/{img['path']}").content == png
    assert client.post(f"/api/projects/{pid}/images", files={"file": ("x.exe", b"x")}).status_code == 422
    assert client.delete(f"/api/projects/{pid}/images/{img['id']}").status_code == 204


def test_parts_api_crud_and_hierarchy(client, faro_project):
    pid = faro_project["id"]
    parts = client.get(f"/api/projects/{pid}/parts").json()
    assert len(parts) == 21
    led = next(p for p in parts if p["cad_key"] == "led_module")

    r = client.post(f"/api/projects/{pid}/parts", json={"name": "LED driver", "parent_id": led["id"], "material_category": "electrical"})
    assert r.status_code == 201
    child = r.json()
    assert child["parent_id"] == led["id"]
    assert child["sort_order"] == 21

    # Cycles are rejected.
    assert client.patch(f"/api/projects/{pid}/parts/{led['id']}", json={"parent_id": child["id"]}).status_code == 422

    r = client.patch(f"/api/projects/{pid}/parts/{child['id']}", json={"quantity": 2, "supplier_notes": "off-the-shelf"})
    assert r.json()["quantity"] == 2
    assert client.patch(f"/api/projects/{pid}/parts/{child['id']}", json={"quantity": 0}).status_code == 422

    assert client.delete(f"/api/projects/{pid}/parts/{child['id']}").status_code == 204
    assert len(client.get(f"/api/projects/{pid}/parts").json()) == 21
