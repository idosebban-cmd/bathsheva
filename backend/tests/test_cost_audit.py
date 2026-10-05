import csv
import io

import pytest

from app.costing.data import load_cost_data
from app.db import new_session
from app.models import Project
from app.rules.data import load_rules
from app.services import costdown
from app.services.cost_audit import TOP_N, cost_audit
from app.services.costing import snapshot


def test_audit_covers_best_configuration_and_ranks_by_impact(client, faro_project):
    session = new_session()
    project = session.get(Project, faro_project["id"])
    audit = cost_audit(session, project)

    snap = snapshot(session, project)
    defs = {d["key"]: d for d in costdown.scenario_defs(project)}
    best = costdown.optimise(snap, defs, 500, load_rules(), load_cost_data(), tier="strict")
    assert audit["unit_cost_mid"] == pytest.approx(best["mid"], abs=0.01)
    assert audit["configuration"]["region"] == best["region"]

    rows = audit["rows"]
    swings = [abs(r["swing"]) for r in rows]
    assert swings == sorted(swings, reverse=True)
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    for r in rows:
        assert r["seed_file"] != "?" and "?" not in r["seed_entry"], r
        assert r["source"] and r["confidence"] in ("low", "medium", "high")
        assert r["low"] <= r["high"]
    assert all(r["how_to_verify"] for r in rows[:TOP_N])
    assert not any(r["how_to_verify"] for r in rows[TOP_N:])
    keys = {r["key"] for r in rows}
    # Region multipliers and densities are included alongside ordinary assumptions.
    if audit["configuration"]["region"] != "uk":
        assert any(k.startswith("region_mult:") for k in keys)
    assert any(k.startswith("density:") for k in keys)
    assert "labour_rate" in keys and any(k.startswith("mat_price:") for k in keys)
    # Seed value is the seed's own figure, not the region-scaled one.
    rate = next(r for r in rows if r["key"] == "rate:metal_spinning")
    assert (rate["low"], rate["high"]) == (35, 60)
    session.close()


def test_audit_downloads(client, faro_project):
    pid = faro_project["id"]
    md = client.get(f"/api/projects/{pid}/cost-audit.md")
    assert md.status_code == 200 and md.text.startswith("# Cost assumptions audit: Faro")
    assert "| # | Assumption |" in md.text and "How to verify" in md.text
    c = client.get(f"/api/projects/{pid}/cost-audit.csv")
    rows = list(csv.reader(io.StringIO(c.text)))
    assert rows[0][0] == "Rank" and len(rows) > 20
    j = client.get(f"/api/projects/{pid}/cost-audit").json()
    assert j["quantity"] == 500 and j["unverified"] == len(j["rows"])
