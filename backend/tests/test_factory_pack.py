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
    svg = dr.to_svg(dr.part_drawing({**DEFAULTS, "base_diameter": 130, "band_diameter": 110}, _sheet("base")))
    assert "Ø130" in svg and "PCD Ø102" in svg  # overall diameter and the band-screw pitch circle
    tower = dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("tower")))
    assert f"Ø{DEFAULTS['tower_bottom_diameter']:g}" in tower and "arched windows" in tower and "masked line" in tower
    railing = dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("railing")))
    assert "FLAT PATTERN" in railing and "Photo-etched" in railing
    frame = dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("lantern_frame")))
    assert "bayonet" in frame and "PLAN VIEW" in frame


def test_drawings_are_cut_from_the_cad_solids():
    """The section of each drawn part has the solid's height and outer diameter."""
    parts = faro.build(DEFAULTS)
    for key in ("base", "tower", "gallery", "cap", "lantern_glass", "diffuser"):
        faces = dr.section_faces(key, DEFAULTS)
        x0, y0, x1, y1 = dr._bounds(faces)
        bb = parts[key].bounding_box()
        assert y1 - y0 == pytest.approx(bb.size.Z, abs=0.05), key
        assert x1 - x0 == pytest.approx(bb.size.X, abs=0.2), key


def test_section_profiles_match_cad_heights():
    prof = faro.section_profiles(DEFAULTS)
    d = faro.derived({k: float(v) for k, v in DEFAULTS.items()})
    assert prof["tower"]["height"] == pytest.approx(d["tower_height"])
    assert prof["lantern_glass"]["height"] == pytest.approx(d["glass_height"])
    assert prof["cap"]["z0"] == pytest.approx(d["cap_bottom_z"])
    assert prof["base"]["diameter"] == pytest.approx(DEFAULTS["base_diameter"])


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
    for stem in ("F-01_base", "F-07_tower", "F-06_cream_band", "F-12_gallery", "F-13_gallery_railing", "F-14_lantern_frame",
                 "F-15_lantern_glass", "F-17_cap", "F-18_cap_bayonet_spigot", "F-04_weight_plate", "F-02_bottom_plate"):
        assert {f"{root}drawings/{stem}.svg", f"{root}drawings/{stem}.pdf", f"{root}step/{stem}.step"} <= names
    assert not any("led" in n.lower() or "battery" in n for n in names)  # bought-in parts are specified, not drawn
    assert zf.read(root + "rfq.pdf").startswith(b"%PDF")
    assert zf.read(root + "step/F-07_tower.step").startswith(b"ISO-10303-21;")

    md = zf.read(root + "rfq.md").decode()
    for text in ("100, 500, 2,000", "MOQ", "Tooling", "Lead time", "Samples", "Suggested design changes",
                 "Material (£)", "Cycle time (min)", "Finishing (£)", "Tooling one-off (£)",
                 "cordless", "Option B", "DC-DC", "dimmer", "UK and EU sale", "COMPLIANCE", "UN38.3", "62133",
                 "2023/1542", "Runtime target", "photo-etched", "twist-lock", "Where production departs",
                 "visible metal must be solid metal", "metal-effect paint",
                 "Class A", "orange peel", "approved sample", "Minimum wall thickness", "rattle", "Target total lamp mass",
                 "Golden sample", "UNVERIFIED", "SAFETY", "tolerances to be agreed"):
        assert text in md, text
    # Our own cost estimates and targets never go to suppliers.
    assert "£75" not in md and "target factory cost" not in md.lower() and "cost model estimate" not in md.lower()
    bom = zf.read(root + "bom.csv").decode()
    assert "Weight plate" in bom and "Battery pack" in bom


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
