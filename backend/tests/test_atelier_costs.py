"""Atelier cost items, compliance one-offs, scenarios and the cost-down summary (no Faro assumptions)."""

import pytest

from app.costing.data import load_cost_data
from app.services.templates import load_template

TPL = load_template("atelier")
PLAIN = {**TPL["cad_parameters"], "grille_perforated": 0}


def test_every_cost_item_and_scenario_item_has_a_price():
    cost = load_cost_data()
    keys = {it["price_key"] for it in TPL["cost_items"] if it.get("price_key")}
    for sc in TPL["scenarios"]:
        eff = sc["effect"]
        keys |= {a["price_key"] for a in eff.get("add_items", [])} | set(eff.get("remove_items", []))
    missing = sorted(k for k in keys if k not in cost.bought_in)
    assert missing == []
    one_offs = {it["price_key"] for it in TPL["cost_items"] if it["kind"] == "one_off"}
    assert {"speaker_radio_emc_safety_testing", "bluetooth_sig_listing"} <= one_offs
    parts = {p["cad_key"] for p in TPL["parts"]}
    for sc in TPL["scenarios"]:
        rp = sc["effect"].get("remove_part", [])
        assert set([rp] if isinstance(rp, str) else rp) <= parts


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    from fastapi.testclient import TestClient

    from app.db import init_db
    from app.main import create_app

    app = create_app()
    init_db(f"sqlite:///{tmp_path_factory.mktemp('db') / 'costs.db'}")
    with TestClient(app) as c:
        pid = c.post("/api/projects", json={"name": "Atelier", "template": "atelier"}).json()["id"]
        assert c.post(f"/api/projects/{pid}/cad/generate", json={"parameters": PLAIN}).status_code == 201
        yield c, pid


def test_cost_items_seeded_from_the_template(project):
    c, pid = project
    items = c.get(f"/api/projects/{pid}/cost-items").json()
    keys = {it["price_key"] for it in items if it.get("price_key")}
    assert {"speaker_driver_57", "speaker_main_board", "battery_pack_1s2p", "knob_logo_engrave", "collar_lettering_etch"} <= keys
    assert any(it["kind"] == "assembly" and it["quantity"] == 30 for it in items)


def test_cost_report_counts_three_fins(project):
    c, pid = project
    rep = c.get(f"/api/projects/{pid}/costs").json()
    fin = next(p for p in rep["parts"] if p["name"] == "Fin")
    assert fin["quantity"] == 3
    assert rep["unit_cost"]["mid"] > 0 and rep["uses_unverified_data"]
    one_off = [ln for ln in rep["product_lines"] if "one-off" in ln.get("explanation", "").lower() or ln.get("category") == "one_off"]
    assert one_off  # testing and the SIG listing, shared over the batch
    assert c.get(f"/api/projects/{pid}/cost-audit?quantity=500").status_code == 200


def test_cost_down_summary_has_no_faro_assumptions(project):
    c, pid = project
    s = c.get(f"/api/projects/{pid}/cost-down/summary").json()
    assert {r["power"] for r in s["rows"]} == {"A"}
    assert s["premium"]["rows"] == []  # no brass edition for Atelier
    assert any("cordless (2 x 18650 1S2P" in n for n in s["notes"])
    assert not any("touch dimmer" in n for n in s["notes"])
    scen = {d["key"] for d in c.get(f"/api/projects/{pid}/scenarios").json()["scenarios"]}
    assert {"nose_cone_spun", "custom_battery_pack", "sealed_no_radiator"} <= scen
    best = next(r for r in s["rows"] if r["quantity"] == 2000 and r["tier"] == "strict")
    cur = next(r for r in s["rows"] if r["quantity"] == 2000 and r["tier"] == "current")
    assert best["cost"]["mid"] <= cur["cost"]["mid"]
    assert "sealed_no_radiator" not in [x["key"] for x in best["selection"]]  # slight compromise: not in "strict"


def test_faro_summary_notes_still_name_its_power_options(client, faro_project):
    notes = client.get(f"/api/projects/{faro_project['id']}/cost-down/summary").json()["notes"]
    assert any("Power options are costed side by side" in n for n in notes)
