"""RFQ pack: drawings, RFQ document and the zip."""

import io
import zipfile

import pytest

from app.cad import faro
from app.factory import drawings as dr
from app.services.templates import load_template

DEFAULTS = load_template("faro")["cad_parameters"]


def _sheet(key):
    return dr.PartSheet(key, "F-01", key, "Aluminium", "Metal spinning", "Black lacquer", 1, "Faro", 1, "2026-10-06",
                        unverified=["placeholder"], safety=["tip-over stability to be tested"])


@pytest.mark.parametrize("key", dr.DRAWN_PARTS)
def test_drawings_render_to_svg_and_pdf_with_title_block(key):
    d = dr.part_drawing(DEFAULTS, _sheet(key))
    svg, pdf = dr.to_svg(d), dr.to_pdf(d)
    assert svg.lstrip().startswith("<?xml") and "<svg" in svg
    assert pdf.startswith(b"%PDF")
    assert dr.TOLERANCE_NOTE.upper() in svg
    assert "UNVERIFIED" in svg


def test_drawing_dimensions_follow_parameters():
    svg = dr.to_svg(dr.part_drawing({**DEFAULTS, "base_diameter": 200}, _sheet("base")))
    assert "Ø200" in svg and "Ø110" in svg  # overall diameter and rivet-nut pitch circle
    body = dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("main_body")))
    assert f"Ø{DEFAULTS['body_diameter']:g}" in body and "locating step" in body


def test_section_profiles_match_cad_heights():
    prof = faro.section_profiles(DEFAULTS)
    d = faro.derived({k: float(v) for k, v in DEFAULTS.items()})
    assert prof["main_body"]["height"] == pytest.approx(d["body_height"])
    assert prof["lantern"]["height"] == pytest.approx(d["glass_length"])
    assert max(z for _, z in prof["top_cap"]["outline"]) == pytest.approx(DEFAULTS["top_cap_height"])


def test_pack_needs_cad(client, faro_project):
    r = client.get(f"/api/projects/{faro_project['id']}/factory-pack.zip")
    assert r.status_code == 409 and "Generate CAD" in r.json()["detail"]
    s = client.get(f"/api/projects/{faro_project['id']}/factory-pack").json()
    assert s["ready"] is False and s["parts"]


def test_pack_contents(client, faro_project):
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    assert client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params}).status_code == 201
    r = client.get(f"/api/projects/{pid}/factory-pack.zip")
    assert r.status_code == 200 and 'faro_rfq_pack_v1.zip' in r.headers["content-disposition"]
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(zf.namelist())
    root = "faro_rfq_pack_v1/"
    assert {root + "rfq.md", root + "rfq.pdf", root + "bom.csv", root + "step/faro_assembly.step"} <= names
    for stem in ("F-01_base", "F-02_main_body", "F-03_decorative_band", "F-04_lantern", "F-05_top_cap", "F-09_weight_plate"):
        assert {f"{root}drawings/{stem}.svg", f"{root}drawings/{stem}.pdf", f"{root}step/{stem}.step"} <= names
    assert not any("led_module" in n or "cable" in n for n in names)  # bought-in parts are specified, not drawn
    assert zf.read(root + "rfq.pdf").startswith(b"%PDF")
    assert zf.read(root + "step/F-02_main_body.step").startswith(b"ISO-10303-21;")

    md = zf.read(root + "rfq.md").decode()
    for text in ("100, 500, 2,000", "MOQ", "Tooling", "Lead time", "Samples", "Suggested design changes",
                 "Material (£)", "Cycle time (min)", "Finishing (£)", "Tooling one-off (£)",
                 "Option A", "Option B", "DC-DC", "Dimmer", "UK and EU sale", "COMPLIANCE",
                 "visible metal must be solid metal", "metal-effect paint",
                 "Class A", "orange peel", "approved sample", "Minimum wall thickness", "rattle", "Target total lamp mass",
                 "Golden sample", "UNVERIFIED", "SAFETY", "tolerances to be agreed"):
        assert text in md, text
    # Our own cost estimates and targets never go to suppliers.
    assert "£75" not in md and "target factory cost" not in md.lower() and "cost model estimate" not in md.lower()
    bom = zf.read(root + "bom.csv").decode()
    assert "Weight plate" in bom and "Lamp tube" in bom


def test_drawing_and_rfq_endpoints(client, faro_project):
    pid = faro_project["id"]
    r = client.get(f"/api/projects/{pid}/drawings/base.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg")
    assert client.get(f"/api/projects/{pid}/drawings/base.pdf").content.startswith(b"%PDF")
    assert client.get(f"/api/projects/{pid}/drawings/led_module.svg").status_code == 404
    assert client.get(f"/api/projects/{pid}/drawings/base.png").status_code == 404
    assert client.get(f"/api/projects/{pid}/rfq.md").text.startswith("# Request for quotation")
    assert client.get(f"/api/projects/{pid}/rfq.pdf").content.startswith(b"%PDF")
    s = client.get(f"/api/projects/{pid}/factory-pack").json()
    assert s["safety"] and s["unverified"] and s["compliance"]
    assert {p["cad_key"] for p in s["parts"]} == set(dr.DRAWN_PARTS)
    blank = client.post("/api/projects", json={"name": "Blank"}).json()["id"]
    assert client.get(f"/api/projects/{blank}/factory-pack").status_code == 409
