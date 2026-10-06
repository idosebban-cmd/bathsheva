import csv
import io


def test_bom_rows_and_csv(client, faro_project):
    pid = faro_project["id"]
    parts = client.get(f"/api/projects/{pid}/parts").json()
    base = next(p for p in parts if p["cad_key"] == "base")
    client.patch(f"/api/projects/{pid}/parts/{base['id']}", json={"material": "Aluminium 6061 (T6)", "process": "CNC machining", "cost_low": 10, "cost_high": 15})

    bom = client.get(f"/api/projects/{pid}/bom").json()
    rows = bom["rows"]
    named = {r["name"]: r for r in rows}
    assert named["Base"]["status"] == "decided"
    assert named["Main body"]["status"] == "recommended" and named["Main body"]["process"] == "Metal spinning"
    assert "unverified rule data" in named["Main body"]["flags"]
    assert bom["cad_version"] is None and named["Base"]["size_mm"] == ""
    # Hardware derived from joints: weight-plate screws, one per rivet nut.
    screws = next(r for r in rows if "weight plate to rivet nuts" in r["name"])
    assert screws["name"].startswith("M4") and screws["quantity"] == 3 and screws["derived"]
    # New construction parts are their own BOM rows; gaskets are not duplicated as hardware.
    assert {"Weight plate", "Lamp tube", "Lamp nut and washer", "Cap nut (finial)", "Dimmer (in base)"} <= set(named)
    assert not any("Silicone gasket ring" in r["name"] for r in rows)
    assert bom["total"]["low"] == 10 and not bom["total"]["complete"]

    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": {**client.get(f"/api/projects/{pid}/cad").json()["parameters"], "mounting_hole_count": 4}})
    bom = client.get(f"/api/projects/{pid}/bom").json()
    assert bom["cad_version"] == 1
    assert next(r for r in bom["rows"] if r["name"] == "Base")["size_mm"].startswith("180")
    assert next(r for r in bom["rows"] if "weight plate to rivet nuts" in r["name"])["quantity"] == 4

    r = client.get(f"/api/projects/{pid}/bom.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "faro_bom.csv" in r.headers["content-disposition"]
    table = list(csv.reader(io.StringIO(r.text)))
    assert table[0][:4] == ["Item", "Level", "Part", "Qty"]
    body = [row for row in table[1:] if row and row[0]]
    assert len(body) == len(bom["rows"])
    assert any(row[2] == "Base" and row[9] == "10.0" for row in body)
    assert any(row[9] == "TBD" for row in body)
