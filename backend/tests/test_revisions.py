from app.config import settings


def test_revisions_are_immutable_snapshots(client, faro_project):
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params})
    r1 = client.post(f"/api/projects/{pid}/revisions", json={"note": "Initial concept"})
    assert r1.status_code == 201 and r1.json()["number"] == 1

    # Change things after the revision.
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": {**params, "overall_height": 320}})
    body = next(p for p in client.get(f"/api/projects/{pid}/parts").json() if p["cad_key"] == "tower")
    client.patch(f"/api/projects/{pid}/parts/{body['id']}", json={"material": "Aluminium 3003 (H14)"})
    req = client.get(f"/api/projects/{pid}").json()["requirements"]
    client.patch(f"/api/projects/{pid}", json={"requirements": {**req, "production_volume": 2000}})
    client.post(f"/api/projects/{pid}/revisions", json={"note": "Taller"})

    revs = client.get(f"/api/projects/{pid}/revisions").json()
    assert [r["number"] for r in revs] == [2, 1]

    old = client.get(f"/api/projects/{pid}/revisions/1").json()["snapshot"]
    new = client.get(f"/api/projects/{pid}/revisions/2").json()["snapshot"]
    assert old["cad_parameters"]["overall_height"] == 300 and new["cad_parameters"]["overall_height"] == 320
    assert old["cad_model"]["version"] == 1 and new["cad_model"]["version"] == 2
    assert old["requirements"]["production_volume"] is None and new["requirements"]["production_volume"] == 2000
    old_body = next(p for p in old["parts"] if p["cad_key"] == "tower")
    assert old_body["material"] == "Aluminium 1050A (H14)"  # accepted template decision, before the edit
    assert len(old["recommendations"]) == 21

    # Old revision's CAD files are still downloadable.
    step = next(o["path"] for o in old["cad_model"]["outputs"] if o["part_key"] is None and o["format"] == "step")
    assert (settings.data_dir / step).exists()
    assert client.get(f"/files/{step}").status_code == 200

    # No way to modify or delete a revision.
    assert client.patch(f"/api/projects/{pid}/revisions/1", json={"note": "x"}).status_code == 405
    assert client.delete(f"/api/projects/{pid}/revisions/1").status_code == 405
    assert client.get(f"/api/projects/{pid}/revisions/99").status_code == 404


def test_revision_without_cad(client):
    pid = client.post("/api/projects", json={"name": "Blank"}).json()["id"]
    snap = client.post(f"/api/projects/{pid}/revisions", json={}).json()["snapshot"]
    assert snap["cad_model"] is None and snap["cad_parameters"] is None and snap["parts"] == []
