import pytest
from sqlalchemy.exc import IntegrityError

from app.models import CadModel, Part, Project, Revision
from app.schemas import Requirements
from app.services.projects import create_project


def test_create_faro_from_template(db):
    p = create_project(db, "Faro", template="faro")
    assert p.slug == "faro"
    assert [part.cad_key for part in p.parts] == [
        "base", "main_body", "band", "lantern", "top_cap", "led_module", "cable"
    ]
    req = Requirements.model_validate(p.requirements)
    assert req.power_type == "undecided"
    assert req.production_volume is None
    assert req.intended_markets == ["UK", "EU"]
    assert {"production_volume", "target_retail_price", "target_unit_cost", "approx_dimensions"} <= set(p.assumed_fields)


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


def test_project_api_roundtrip(client, faro):
    pid = faro["id"]
    req = faro["requirements"]
    req["production_volume"] = 1000
    r = client.patch(f"/api/projects/{pid}", json={
        "requirements": req,
        "assumed_fields": [f for f in faro["assumed_fields"] if f != "production_volume"],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["requirements"]["production_volume"] == 1000
    assert "production_volume" not in body["assumed_fields"]
    assert client.patch(f"/api/projects/{pid}", json={"assumed_fields": ["bogus"]}).status_code == 422


def test_image_upload(client, faro):
    pid = faro["id"]
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 20
    r = client.post(f"/api/projects/{pid}/images", files={"file": ("render.png", png, "image/png")}, data={"kind": "concept"})
    assert r.status_code == 201, r.text
    img = r.json()
    assert client.get(f"/files/{img['path']}").content == png
    assert client.post(f"/api/projects/{pid}/images", files={"file": ("x.exe", b"x")}).status_code == 422
    assert client.delete(f"/api/projects/{pid}/images/{img['id']}").status_code == 204
