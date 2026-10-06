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
    assert named["Tower"]["status"] == "decided" and named["Tower"]["process"] == "Metal spinning"  # accepted decision
    assert named["Lantern LED"]["status"] == "recommended" and "unverified rule data" in named["Lantern LED"]["flags"]
    assert bom["cad_version"] is None and named["Base"]["size_mm"] == ""
    # Hardware listed on the joints: band screws, bottom-plate screws, standoffs, magnets, diffuser rings.
    screws = next(r for r in rows if r["name"].startswith("M3 x 25"))
    assert screws["quantity"] == 3 and screws["derived"] and "assumption" in screws["flags"]
    assert {"M2.5 hex standoff, aluminium", "N52 magnet 6 x 2 mm", "Silicone ring, diffuser"} <= set(named)
    assert {"Weight plate", "Battery pack", "Control board", "Cap bayonet spigot", "Gallery railing"} <= set(named)
    assert bom["total"]["low"] == 10 and not bom["total"]["complete"]

    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": client.get(f"/api/projects/{pid}/cad").json()["parameters"]})
    bom = client.get(f"/api/projects/{pid}/bom").json()
    assert bom["cad_version"] == 1
    assert next(r for r in bom["rows"] if r["name"] == "Base")["size_mm"].startswith("113")

    r = client.get(f"/api/projects/{pid}/bom.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "faro_bom.csv" in r.headers["content-disposition"]
    table = list(csv.reader(io.StringIO(r.text)))
    assert table[0][:4] == ["Item", "Level", "Part", "Qty"]
    body = [row for row in table[1:] if row and row[0]]
    assert len(body) == len(bom["rows"])
    assert any(row[2] == "Base" and row[9] == "10.0" for row in body)
    assert any(row[9] == "TBD" for row in body)
