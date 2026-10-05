def _checks(client, pid):
    return client.get(f"/api/projects/{pid}/dfm").json()


def titles(report):
    return {c["title"]: c for c in report["checks"]}


def test_dfm_report_for_new_faro(client, faro_project):
    pid = faro_project["id"]
    r = _checks(client, pid)
    t = titles(r)
    assert t["Production volume not set"]["level"] == "warning"
    assert any(c["title"].startswith("Open decision") for c in r["checks"])
    assert t["No CAD generated yet"]["level"] == "info"
    assert t["Stability (heuristic)"]["unverified"]
    assert t["Body wall too thin to tap for base screws"]["level"] == "warning"
    assert r["summary"]["safety_items"] > 0
    assert len(r["parts"]) == 7
    assert "not a substitute" in r["disclaimer"].lower()


def test_dfm_reacts_to_parameters_and_decisions(client, faro_project):
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": {**params, "overall_height": 600}})
    t = titles(_checks(client, pid))
    assert t["CAD v1 solids valid"]["level"] == "pass"
    assert t["Stability (heuristic)"]["level"] == "warning"  # 180 / 600 < 35 %

    base = next(p for p in client.get(f"/api/projects/{pid}/parts").json() if p["cad_key"] == "base")
    client.patch(f"/api/projects/{pid}/parts/{base['id']}", json={"process": "High-pressure die casting"})
    r = _checks(client, pid)
    assert "Base: no draft in CAD" in titles(r)
    assert next(p for p in r["parts"] if p["name"] == "Base")["basis"] == "decided"


def test_dfm_markdown(client, faro_project):
    r = client.get(f"/api/projects/{faro_project['id']}/dfm.md")
    assert r.status_code == 200
    assert r.text.startswith("# DFM report: Faro")
    assert "## Safety items" in r.text and "## Assumptions" in r.text
