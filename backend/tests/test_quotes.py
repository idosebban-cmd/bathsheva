import hashlib
import io
import zipfile
from datetime import date

from build123d import import_step
import pytest

from app.config import SEED_DIR, settings
from app.models import ExternalQuote, Part
from app.services.projects import create_project
from app.services.quotes import compare, estimate_for

# --- model -------------------------------------------------------------------


def test_external_quote_model_and_cascade(db):
    project = create_project(db, "Faro", template="faro")
    base = project.parts[0]
    q = ExternalQuote(project_id=project.id, part_id=base.id, source="Xometry", quote_date=date(2026, 10, 1),
                      quantity=100, unit_price=14.2, currency="GBP")
    db.add(q)
    db.commit()
    assert q.id and q.dfm_notes == "" and q.revision_id is None and q.lead_time_days is None
    db.delete(db.get(Part, base.id))
    db.commit()
    assert db.query(ExternalQuote).count() == 0  # quotes go with their part


# --- comparison ----------------------------------------------------------------


EST = {"low": 10.0, "high": 15.0, "currency": "GBP", "basis": "test"}


def test_compare_against_estimate():
    assert compare(None, 12, "GBP")["status"] == "no_estimate"
    assert compare(EST, 12, "EUR")["status"] == "currency_mismatch"
    assert compare(EST, 12, "gbp")["status"] == "within"
    below = compare(EST, 8, "GBP")
    assert below["status"] == "below" and below["diff"] == -2 and below["diff_pct"] == -20
    above = compare(EST, 18, "GBP")
    assert above["status"] == "above" and above["diff"] == 3 and above["diff_pct"] == 20
    assert compare(EST, 10, "GBP")["status"] == "within" and compare(EST, 15, "GBP")["status"] == "within"


def test_estimate_from_part_costs():
    assert estimate_for(Part(name="x", cost_low=None, cost_high=None)) is None
    assert estimate_for(Part(name="x", cost_low=5, cost_high=None))["high"] == 5
    assert estimate_for(Part(name="x", cost_low=9, cost_high=4)) == {
        "low": 4, "high": 9, "currency": "GBP", "basis": "Unit cost estimate on the part (Parts / BOM)", "source": "manual"}


# --- API -----------------------------------------------------------------------


def _part(client, pid, cad_key):
    return next(p for p in client.get(f"/api/projects/{pid}/parts").json() if p["cad_key"] == cad_key)


def _quote(client, pid, part_id, files=None, **fields):
    data = {"source": "Xometry", "quote_date": "2026-10-01", "quantity": "100", "unit_price": "18.00",
            "currency": "GBP", "process": "CNC machining", "material": "6061-T6", "finish": "Black anodise",
            "lead_time_days": "15", "dfm_notes": "Add 0.5 mm fillet to inner edge.", **fields}
    return client.post(f"/api/projects/{pid}/parts/{part_id}/quotes", data=data, files=files)


def test_quotes_api_add_list_compare_delete(client, faro_project):
    pid = faro_project["id"]
    base = _part(client, pid, "base")
    client.patch(f"/api/projects/{pid}/parts/{base['id']}", json={"cost_low": 10, "cost_high": 15})
    rev = client.post(f"/api/projects/{pid}/revisions", json={"note": "sent to Xometry"}).json()

    r = _quote(client, pid, base["id"], revision_id=str(rev["id"]),
               files={"attachment": ("quote.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert r.status_code == 201, r.text
    q = r.json()
    assert q["comparison"]["status"] == "above" and q["comparison"]["diff_pct"] == 20
    assert q["total_price"] == 1800 and q["revision_number"] == 1
    assert client.get(f"/files/{q['attachment_path']}").content == b"%PDF-1.4 test"

    _quote(client, pid, base["id"], source="Local spinner", unit_price="12", quote_date="2026-10-03", lead_time_days="")
    _quote(client, pid, base["id"], source="EU shop", unit_price="11", currency="eur")

    listing = client.get(f"/api/projects/{pid}/parts/{base['id']}/quotes").json()
    assert listing["estimate"]["low"] == 10
    assert [x["source"] for x in listing["quotes"]][0] == "Local spinner"  # newest first
    statuses = {x["source"]: x["comparison"]["status"] for x in listing["quotes"]}
    assert statuses == {"Xometry": "above", "Local spinner": "within", "EU shop": "currency_mismatch"}
    assert next(x for x in listing["quotes"] if x["source"] == "EU shop")["currency"] == "EUR"
    assert next(x for x in listing["quotes"] if x["source"] == "Local spinner")["lead_time_days"] is None

    assert client.delete(f"/api/projects/{pid}/quotes/{q['id']}").status_code == 204
    assert not (settings.data_dir / q["attachment_path"]).exists()
    assert len(client.get(f"/api/projects/{pid}/parts/{base['id']}/quotes").json()["quotes"]) == 2
    assert client.delete(f"/api/projects/{pid}/quotes/{q['id']}").status_code == 404


def test_quote_validation(client, faro_project):
    pid = faro_project["id"]
    base = _part(client, pid, "base")
    assert _quote(client, pid, base["id"], source=" ").status_code == 422
    assert _quote(client, pid, base["id"], quantity="0").status_code == 422
    assert _quote(client, pid, base["id"], unit_price="-1").status_code == 422
    assert _quote(client, pid, base["id"], currency="POUNDS").status_code == 422
    assert _quote(client, pid, base["id"], revision_id="9999").status_code == 422
    assert _quote(client, pid, base["id"], files={"attachment": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 422
    other = client.post("/api/projects", json={"name": "Other", "template": "faro"}).json()
    other_part = _part(client, other["id"], "base")
    assert _quote(client, pid, other_part["id"]).status_code == 404  # part from another project


def test_quotes_do_not_touch_rules_or_seed_data(client, faro_project):
    pid = faro_project["id"]
    seed_hash = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(SEED_DIR.rglob("*.yaml")))).hexdigest()
    before = client.get(f"/api/projects/{pid}/recommendations").json()["recommendations"]
    base = _part(client, pid, "base")
    process_before = base["process"]  # the template's accepted decision (spun base)
    _quote(client, pid, base["id"], process="High-pressure die casting", unit_price="2.00", quantity="10000")
    after = client.get(f"/api/projects/{pid}/recommendations").json()["recommendations"]
    assert before == after
    assert _part(client, pid, "base")["process"] == process_before == "Metal spinning"  # the part itself is unchanged too
    assert hashlib.sha256(b"".join(p.read_bytes() for p in sorted(SEED_DIR.rglob("*.yaml")))).hexdigest() == seed_hash


# --- quoting pack ----------------------------------------------------------------


def test_quote_pack_requires_cad(client, faro_project):
    r = client.get(f"/api/projects/{faro_project['id']}/quote-pack.zip")
    assert r.status_code == 409 and "Generate CAD" in r.json()["detail"]


def test_quote_pack_zip(client, faro_project):
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": {**params, "overall_height": 320}})
    tower = _part(client, pid, "tower")
    client.patch(f"/api/projects/{pid}/parts/{tower['id']}", json={"material": "Aluminium 3003 (H14)", "quantity": 2})

    r = client.get(f"/api/projects/{pid}/quote-pack.zip")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert 'filename="faro_quote_pack_v1.zip"' in r.headers["content-disposition"]
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = sorted(zf.namelist())
    folder = "faro_quote_pack_v1/"
    assert names == sorted(folder + n for n in [
        "README.md", "01_base.step", "02_bottom_plate.step", "04_weight_plate.step", "05_nameplate.step",
        "06_cream_band.step", "07_tower.step", "08_window_diffuser.step", "11_dimmer_knob.step", "12_gallery.step",
        "13_gallery_railing.step", "14_lantern_frame.step", "15_lantern_glass.step", "17_cap.step",
        "18_cap_bayonet_spigot.step", "19_finial.step",
    ])  # electronics and the felt are not sent; the plates are made to drawing

    for n in names:
        if n.endswith(".step"):
            assert zf.read(n).startswith(b"ISO-10303-21;")
    out = zf.extract(folder + "07_tower.step", path=str(settings.data_dir / "unzipped"))
    tower_solid = import_step(out)
    assert len(tower_solid.solids()) == 1
    # Tower = overall − finial − cap − lantern − gallery − (base + band).
    assert tower_solid.solids()[0].bounding_box().size.Z == pytest.approx(320 - 19 - 33 - 41.3 - 9.7 - 33, abs=0.5)

    readme = zf.read(folder + "README.md").decode()
    assert "CAD version v1" in readme
    assert "| 07_tower.step | Tower | 2 | Aluminium 3003 (H14) | Metal spinning | Two-tone lacquer" in readme
    base_line = next(line for line in readme.splitlines() if line.startswith("| 01_base.step"))
    assert "Metal spinning" in base_line and "(recommended)" not in base_line and "Satin black lacquer" in base_line
    assert "- Battery pack × 1: bought-in component" in readme
    assert "M3 x 25 socket screw" in readme  # hardware listed as not included
