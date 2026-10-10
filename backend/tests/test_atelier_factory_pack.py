"""Atelier's Factory Pack: RFQs, drawings, STEP, supplier BOM, artwork and consistency checks."""

import io
import zipfile

import pytest

from app.factory import atelier_drawings as adr
from app.services.templates import load_template

PLAIN = {**load_template("atelier")["cad_parameters"], "grille_perforated": 0}


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    from fastapi.testclient import TestClient

    from app.db import init_db
    from app.main import create_app

    app = create_app()
    init_db(f"sqlite:///{tmp_path_factory.mktemp('db') / 'pack.db'}")
    with TestClient(app) as c:
        pid = c.post("/api/projects", json={"name": "Atelier", "template": "atelier"}).json()["id"]
        assert c.post(f"/api/projects/{pid}/cad/generate", json={"parameters": PLAIN}).status_code == 201
        yield c, pid


def test_summary_and_consistency(project):
    c, pid = project
    r = c.get(f"/api/projects/{pid}/factory-pack")
    assert r.status_code == 200, r.text
    s = r.json()
    assert [pt["cad_key"] for pt in s["parts"]] == [k for k in adr.DRAWN_PARTS if k in {pt["cad_key"] for pt in s["parts"]}] \
        or len(s["parts"]) == len(adr.DRAWN_PARTS)
    assert {pt["cad_key"] for pt in s["parts"]} == set(adr.DRAWN_PARTS)
    assert all(pt["part_no"].startswith("A-") for pt in s["parts"])
    checks = {ch["check"]: ch for ch in s["consistency"]}
    must_pass = ["Drawings and STEP files show the same solids", "All bodies in the model", "STEP file for every drawing",
                 "Drawing notes match each part's process", "BOM lists every drawn part",
                 "No prices or cost targets in supplier documents", "No stray placeholders in the RFQs",
                 "Collar lettering artwork", "Production change: Stability", "Production change: Mass"]
    for name in must_pass:
        assert checks[name]["ok"], (name, checks[name]["detail"])
    assert checks["Contact and delivery details filled in"]["level"] == "warn"
    assert not checks["Supplier questions answered"]["ok"]  # the six supplier questions are open, and say so
    assert len([q for q in s["open_questions"] if q["status"] == "open"]) >= 6
    assert {x["group"] for x in s["bought_in"]} >= {"electronics", "operation"}


def test_rfqs_say_what_the_spec_says(project):
    c, pid = project
    md = c.get(f"/api/projects/{pid}/rfq.md").text
    for text in ("rocket Bluetooth speaker", "Gold PVD", "ΔE ≤ 1.5", "#8A1C15", "≥ 90 GU", "ISO 2409", "salt spray",
                 "24 soft detents", "ISTA 2A", "Battery replacement", "1.5 mm hex key", "UNVERIFIED", "COMPLIANCE",
                 "Where production departs from the prototype", "300 / 500 / 2,000", "[COMPANY NAME]", "FOB"):
        assert text in md, text
    assert "table lamp" not in md and "£" not in md
    emd = c.get(f"/api/projects/{pid}/rfq-electronics.md").text
    for text in ("Bluetooth 5.3", "Multipoint", "stereo pairing", "remembers 8 devices", "OTA", "no microphone",
                 "20 W RMS", "boost converter", "USB-C PD", "hold 10 s = factory reset", "slow breathing",
                 "1S2P", "UN38.3", "IEC 62133-2", "Thiele-Small", "60 Hz–20 kHz", "THD 1%"):
        assert text in emd, text
    assert "£" not in emd
    assert c.get(f"/api/projects/{pid}/rfq.pdf").content.startswith(b"%PDF")
    assert c.get(f"/api/projects/{pid}/rfq-electronics.pdf").content.startswith(b"%PDF")


@pytest.mark.parametrize("key", adr.DRAWN_PARTS)
def test_every_drawing_renders(project, key):
    c, pid = project
    svg = c.get(f"/api/projects/{pid}/drawings/{key}.svg")
    assert svg.status_code == 200, svg.text
    assert "<svg" in svg.text and "Qty per speaker" in svg.text
    assert c.get(f"/api/projects/{pid}/drawings/{key}.pdf").content.startswith(b"%PDF")


def test_zip_contents(project):
    c, pid = project
    r = c.get(f"/api/projects/{pid}/factory-pack.zip")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(zf.namelist())
    root = "atelier_rfq_pack_v1/"
    mech, elec = root + "mechanical/", root + "electronics/"
    assert {root + "README.txt", mech + "rfq.pdf", mech + "rfq.md", mech + "bom.csv", elec + "rfq_electronics.pdf",
            mech + "step/atelier_assembly.step", mech + "artwork/A-01_collar_lettering.svg",
            mech + "artwork/A-01_collar_lettering.dxf"} <= names
    assert len([n for n in names if n.startswith(mech + "drawings/") and n.endswith(".pdf")]) == len(adr.DRAWN_PARTS)
    assert len([n for n in names if n.startswith(mech + "step/A-")]) == len(adr.DRAWN_PARTS)
    bom = zf.read(mech + "bom.csv").decode()
    assert "Qty/speaker" in bom and "£" not in bom and "Electronics (separate RFQ)" in bom
    assert "speaker" in zf.read(root + "README.txt").decode()


def test_odm_rfq(project):
    """ODM: cover note, quote sheet and the full pack in one zip; no prices; asks for route, tooling, prices, lead times."""
    c, pid = project
    md = c.get(f"/api/projects/{pid}/odm-rfq.md").text
    for text in ("complete product (ODM)", "recommended manufacturing route", "Tooling", "300 / 500 / 2,000",
                 "Lead times", "FOB and DDP", "real metal", "replaceable after removing the base collar", "COMPLIANCE",
                 "odm_quote_sheet.csv", "[COMPANY NAME]"):
        assert text in md, text
    assert "£" not in md
    assert c.get(f"/api/projects/{pid}/odm-rfq.pdf").content.startswith(b"%PDF")
    sheet = c.get(f"/api/projects/{pid}/odm-quote-sheet.csv").text
    assert "Unit price at 300" in sheet and "Unit price at 2,000" in sheet and "Tooling cost" in sheet
    assert "Golden sample" in sheet and "£" not in sheet
    r = c.get(f"/api/projects/{pid}/factory-pack-odm.zip")
    assert r.status_code == 200
    names = set(zipfile.ZipFile(io.BytesIO(r.content)).namelist())
    root = "atelier_odm_rfq_pack_v1/"
    assert {root + "README.txt", root + "odm/odm_cover_note.pdf", root + "odm/odm_cover_note.md",
            root + "odm/odm_quote_sheet.csv", root + "mechanical/rfq.pdf", root + "electronics/rfq_electronics.pdf",
            root + "mechanical/step/atelier_assembly.step"} <= names
    s = c.get(f"/api/projects/{pid}/factory-pack").json()
    assert s["odm"]["available"] and "Cover note" in s["odm"]["markdown"]
    checks = {ch["check"]: ch for ch in s["consistency"]}
    assert checks["No prices or cost targets in supplier documents"]["ok"]


def test_no_odm_rfq_for_faro_yet(client, faro_project):
    assert client.get(f"/api/projects/{faro_project['id']}/odm-rfq.md").status_code == 404

def test_faro_pack_still_served_by_its_own_module(client, faro_project):
    from app.services import factory_pack as fp

    from app.models import Project
    from app.db import new_session

    with new_session() as s:
        proj = s.get(Project, faro_project["id"])
        assert fp.pack_module(proj) is fp
