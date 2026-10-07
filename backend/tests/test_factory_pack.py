"""RFQ pack: drawings, RFQ document and the zip."""

import io
import re
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


def _text(svg: str) -> str:
    """All text in a drawing as one string (notes wrap across several SVG text lines)."""
    import html

    return " ".join(html.unescape(t) for t in re.findall(r"<text[^>]*>([^<]*)</text>", svg))


def test_drawing_dimensions_follow_parameters():
    svg = dr.to_svg(dr.part_drawing({**DEFAULTS, "base_diameter": 130, "band_diameter": 110}, _sheet("base")))
    assert "Ø130" in svg and "PCD Ø102" in svg  # overall diameter and the band-screw pitch circle
    tower = _text(dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("tower"))))
    assert f"Ø{DEFAULTS['tower_bottom_diameter']:g}" in tower and "arched windows" in tower and "masked" in tower
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
    root, mech, elec = "faro_rfq_pack_v1/", "faro_rfq_pack_v1/mechanical/", "faro_rfq_pack_v1/electronics/"
    assert {mech + "artwork/F-05_nameplate_lettering.svg", mech + "artwork/F-05_nameplate_lettering.dxf"} <= names
    assert zf.read(mech + "artwork/F-05_nameplate_lettering.svg").startswith(b"<?xml")
    assert {root + "README.txt", mech + "rfq.md", mech + "rfq.pdf", mech + "bom.csv", mech + "step/faro_assembly.step",
            elec + "rfq_electronics.md", elec + "rfq_electronics.pdf"} <= names
    for stem in ("F-01_base", "F-07_tower", "F-06_cream_band", "F-12_gallery", "F-13_gallery_railing", "F-14_lantern_frame",
                 "F-15_lantern_glass", "F-17_cap", "F-18_cap_bayonet_spigot", "F-04_weight_plate", "F-02_bottom_plate"):
        assert {f"{mech}drawings/{stem}.svg", f"{mech}drawings/{stem}.pdf", f"{mech}step/{stem}.step"} <= names
    assert not any("led" in n.lower() or "battery" in n for n in names)  # bought-in parts are specified, not drawn
    assert zf.read(mech + "rfq.pdf").startswith(b"%PDF") and zf.read(elec + "rfq_electronics.pdf").startswith(b"%PDF")
    assert zf.read(mech + "step/F-07_tower.step").startswith(b"ISO-10303-21;")

    md = zf.read(mech + "rfq.md").decode()
    for text in ("300, 500, 2,000", "MOQ", "Tooling", "Lead time", "Samples", "Suggested design changes",
                 "Material (£)", "Cycle time (min)", "Finishing (£)", "Tooling one-off (£)", "Method",
                 "cordless", "photo-etched", "twist-lock", "Where production departs",
                 "visible metal must be solid metal", "metal-effect paint",
                 "Class A", "orange peel", "colour samples we supply", "Minimum wall thickness", "rattle", "Target total lamp mass",
                 "Golden sample", "UNVERIFIED", "SAFETY", "ISO 2768-m", "AQL 1.0",
                 "[COMPANY NAME]", "[CONTACT NAME, ROLE]", "[QUOTE DEADLINE]", "Colours and finishes", "#121212", "#F9F2E1",
                 "#8A1C15", "RAL 9005", "RAL 9001", "RAL 3011 Brown red (approx.) / RAL 3002 Carmine red (approx.)",
                 "approximate", "Physical colour samples will be supplied and are the master", "satin, 30–50 GU",
                 "gloss, 80+ GU", "Brushed brass, clear lacquer", "matching our Atelier", "satin black (30–50 GU)",
                 "300 to 500 lamps", "UKCA", "CE marking for the EU may follow", "FOB (port of loading)", "DDP to our UK address",
                 "[DELIVERY ADDRESS, to be filled in]", "GBP or USD", "final assembly", "protective packing", "pull-test",
                 "artwork/",
                 "Brass parts: please quote two ways", "your preferred method", "near-net basis",
                 "Spun from a 1.0 mm CZ108 brass disc", "separate RFQ", "Battery bay"):
        assert text in md, text
    # Not components: our one-off testing cost, and electronics (separate RFQ) aren't priced here.
    assert "EMC testing" not in md and "| Pre-certified Li-ion battery pack" not in md
    brass_rows = md.split("Brass parts: please quote two ways")[1].split("\n## ")[0]
    for name in ("Gallery", "Lantern frame", "Cap bayonet spigot", "Finial", "Dimmer knob", "Gallery railing", "Nameplate"):
        assert f"| {name} |" in brass_rows, name
    assert "| F-12 | B | 2,000 |" in md  # breakdown rows for both methods

    emd = zf.read(elec + "rfq_electronics.md").decode()
    for text in ("300, 500, 2,000", "pre-certified 2 x 18650", "Pass-through charging", "UN38.3", "62133-2", "2023/1542",
                 "protection", "1S2P", "Two constant-current LED channels", "Dimming", "flicker", "2700 K", "CRI 90",
                 "filament", "Option B", "DC-DC", "Runtime", "70 × 38 × 19.5", "Space available", "[COMPANY NAME]",
                 "UKCA", "UK plug", "FOB (port of loading)", "GBP or USD", "300 to 500 sets", "charging indicator LED"):
        assert text in emd, text
    # Our own cost estimates and targets never go to suppliers.
    for doc in (md, emd):
        assert "£75" not in doc and "target factory cost" not in doc.lower() and "cost model estimate" not in doc.lower()
        assert not re.search(r"£\s?\d", doc)
    bom = zf.read(mech + "bom.csv").decode()
    assert "Weight plate" in bom and "Battery pack" in bom and "Electronics (separate RFQ)" in bom
    assert "cost" not in bom.lower() and "GBP" not in bom
    header = bom.splitlines()[0].split(",")
    assert "Colour reference" in header and "Gloss" in header
    assert "Oxblood red lacquer #8A1C15, RAL 3011 Brown red (approx.) / RAL 3002 Carmine red (approx.)" in bom
    assert "satin, 30–50 GU (60°)" in bom and "gloss, 80+ GU (60°)" in bom and "brushed satin grain" in bom
    assert "Tumble" not in md and "Tumble" not in bom
    assert "artwork/F-05_nameplate_lettering.svg" in bom
    assert "UK and EU" not in md and "UNVERIFIED)" not in emd.split("charging indicator")[1].split("\n")[0]
    assert bom.splitlines()[1].startswith("F-01,Base")
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


def test_consistency_checks_and_open_questions(client, faro_project):
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params})
    s = client.get(f"/api/projects/{pid}/factory-pack").json()
    checks = {c["check"]: c for c in s["consistency"]}
    assert all(c["ok"] or c.get("level") == "warn" for c in s["consistency"]), [c for c in s["consistency"] if not c["ok"]]
    assert not checks["Contact and delivery details filled in"]["ok"]  # blank by default: a warning, not a failure
    for name in ("Drawings and STEP files show the same solids", "STEP file for every drawing",
                 "Drawing notes match each part's process", "Production change: Gallery", "Production change: Window diffusers",
                 "No prices or cost targets in supplier documents"):
        assert name in checks, name
    assert s["quantity_tiers"] == [300, 500, 2000]
    assert {q["id"] for q in s["open_questions"]} >= {"battery_config", "tolerances", "colours", "artwork", "incoterms",
                                                       "production_volume", "electrical_data", "intended_markets"}
    assert all(q["status"] == "resolved" and q["answer"] for q in s["open_questions"])
    assert "[DELIVERY ADDRESS, to be filled in]" in s["placeholders"] and "[COMPANY NAME]" in s["placeholders"]
    for name in ("No stray placeholders in the RFQs", "Nameplate lettering is clean and centred", "Nameplate SVG / DXF match the artwork",
                 "Nameplate lettering on the 3D model", "Nameplate lettering on the drawing", "Supplier questions answered"):
        assert checks[name]["ok"], name
    assert len(s["brass_parts"]) == 7 and s["electronics_rfq_markdown"].startswith("# Request for quotation")
    assert client.get(f"/api/projects/{pid}/rfq-electronics.pdf").content.startswith(b"%PDF")
    assert client.get(f"/api/projects/{pid}/rfq-electronics.md").text.startswith("# Request for quotation")


def test_consistency_flags_stale_cad_and_changed_routes(client, faro_project):
    from app.db import new_session
    from app.models import CadModel, Part, Project
    from app.services import factory_pack as fp

    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params})
    session = new_session()
    project = session.get(Project, pid)
    model = session.query(CadModel).filter_by(project_id=pid).one()
    info = dict(model.part_info)
    info["gallery"] = {**info["gallery"], "volume_mm3": info["gallery"]["volume_mm3"] * 3}  # as if made by an older generator
    model.part_info = info
    gallery = next(p for p in project.parts if p.cad_key == "gallery")
    gallery.process = "CNC machining"
    session.commit()
    checks = {c["check"]: c for c in fp.consistency_checks(project)}
    assert not checks["Drawings and STEP files show the same solids"]["ok"]
    assert "F-12 Gallery" in checks["Drawings and STEP files show the same solids"]["detail"]
    assert not checks["Drawing notes match each part's process"]["ok"]
    session.close()


def test_production_change_checks_follow_geometry():
    from app.cad import faro

    checks = {c["feature"]: c for c in faro.production_change_checks(DEFAULTS)}
    assert all(c["ok"] for c in checks.values()), checks
    assert {"Shell walls", "Window diffusers", "Gallery", "Cap twist-lock", "Lantern glass"} <= set(checks)


def test_nameplate_lettering_artwork():
    """Cormorant Garamond SemiBold from the bundled font, 5 mm caps, centred exactly on the plate."""
    from app.factory import nameplate

    assert nameplate.FONT_PATH.is_file() and "Cormorant" in nameplate.FONT_NAME
    files = nameplate.artwork_files()
    assert set(files) == {"F-05_nameplate_lettering.svg", "F-05_nameplate_lettering.dxf"}
    svg = files["F-05_nameplate_lettering.svg"].decode()
    assert 'width="37.05mm"' in svg and 'id="lettering_etch"' in svg and 'fill="rgb(0,0,0)"' in svg
    plate, letters = nameplate.shapes()
    faces = letters.faces()
    assert len(faces) == 4 and all(f.is_valid for f in faces)  # F, A, R, O: overlaps and the A's self-crossing resolved
    assert [len(f.inner_wires()) for f in faces] == [0, 1, 1, 1]  # counters in A, R, O
    bb = letters.bounding_box()
    assert bb.size.Y == pytest.approx(5.0, abs=0.01) and 18 < bb.size.X < 22
    assert abs(bb.center().X) < 0.01 and abs(bb.center().Y) < 0.01  # optical centre, no em-box offset
    assert nameplate.letter_area() == pytest.approx(nameplate.nonzero_area(), rel=0.01)


def test_nameplate_lettering_on_model_and_drawing():
    from app.factory import nameplate

    m = faro.model(DEFAULTS)
    assert m.parts["nameplate"].is_valid
    assert len(m.preview["nameplate_fill"].solids()) == 4
    assert m.info["nameplate_etch_mm3"] == pytest.approx(nameplate.letter_area() * nameplate.ETCH_DEPTH, rel=0.03)
    checks = nameplate.consistency({}, m.info)
    assert all(ok for _, ok, _ in checks), checks
    svg = dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("nameplate")))
    assert "Cormorant Garamond SemiBold" in svg and ">FARO<" not in svg  # outlines from the artwork, not a font


def test_contact_fields_fill_the_rfqs(client, faro_project):
    pid = faro_project["id"]
    r = client.get(f"/api/projects/{pid}/factory-pack/contact").json()
    assert all(v == "" for v in r["values"].values()) and len(r["missing"]) == 7
    md = client.get(f"/api/projects/{pid}/rfq.md").text
    assert "[COMPANY NAME]" in md and "[DELIVERY ADDRESS, to be filled in]" in md
    assert client.put(f"/api/projects/{pid}/factory-pack/contact", json={"email": "not-an-email"}).status_code == 422
    assert client.put(f"/api/projects/{pid}/factory-pack/contact", json={"fax": "1"}).status_code == 422
    details = {"company_name": "Bathsheva London", "contact_name": "A. Person, Founder", "email": "hello@example.com",
               "phone": "+44 20 0000 0000", "company_address": "1 Example Street, London", "quote_deadline": "30 October 2026",
               "delivery_address": "Unit 2, Example Estate, London E1"}
    r = client.put(f"/api/projects/{pid}/factory-pack/contact", json=details)
    assert r.status_code == 200 and r.json()["missing"] == []
    md = client.get(f"/api/projects/{pid}/rfq.md").text
    emd = client.get(f"/api/projects/{pid}/rfq-electronics.md").text
    for doc in (md, emd):
        assert "| From | Bathsheva London |" in doc and "hello@example.com" in doc and "30 October 2026" in doc
        assert "DDP to our UK address: Unit 2, Example Estate, London E1" in doc
        assert "[COMPANY NAME]" not in doc and "[DELIVERY ADDRESS" not in doc
    s = client.get(f"/api/projects/{pid}/factory-pack").json()
    assert s["missing_contact"] == [] and s["placeholders"] == []
    # Clearing a field brings its placeholder (and the warning) back.
    client.put(f"/api/projects/{pid}/factory-pack/contact", json={"phone": ""})
    assert "[PHONE]" in client.get(f"/api/projects/{pid}/rfq.md").text
    assert client.get(f"/api/projects/{pid}/factory-pack").json()["missing_contact"] == ["Phone"]


def test_brass_drawings_and_finishes_are_brushed():
    for key in ("gallery", "railing", "lantern_frame", "finial", "knob", "nameplate"):
        txt = _text(dr.to_svg(dr.part_drawing(DEFAULTS, _sheet(key))))
        assert "brushed satin" in txt.lower() and "clear lacquer" in txt and "Tumble" not in txt, key
    assert "Satin black lacquer (#121212), 30–50 GU" in _text(dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("base"))))
    assert "80+ GU" in _text(dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("tower"))))
    assert "80+ GU" in _text(dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("cap"))))


def test_knob_logo_artwork_model_and_drawing():
    """The logo on the knob face: one artwork for the vector files, the 3D knob and the drawing."""
    import json

    from app.factory import logo, nameplate

    # The stored outlines are exactly what the generator makes from the current proportions.
    stored = json.loads((logo.ARTWORK_DIR / logo.LOOPS_FILE).read_text())
    assert stored["params"] == logo.geometry_params()
    regen = nameplate._loops_of(logo.unit_grooves_from_geometry())

    def canon(faces):  # loop order and starting vertex vary between kernel runs; the outlines don't
        out = []
        for f in faces:
            lps = []
            for lp in f:
                pts = [tuple(round(v, 5) for v in p) for p in lp]
                i = pts.index(min(pts))
                lps.append(tuple(pts[i:] + pts[:i]))
            out.append((lps[0], tuple(sorted(lps[1:]))))
        return sorted(out)

    assert canon(stored["grooves"]) == canon(regen)
    grooves = logo._unit_grooves().faces()
    assert len(grooves) == 1 and len(grooves[0].inner_wires()) == 13  # 9 rays + sun + 3 sea bands, all one groove network
    r = logo.logo_radius(DEFAULTS["knob_diameter"])
    assert r * (1 + logo.GROOVE) <= DEFAULTS["knob_diameter"] / 2 - logo.EDGE_FILLET  # inside the front-edge radius
    assert logo.GROOVE * r >= logo.MIN_GROOVE_MM
    files = logo.artwork_files(r)
    assert set(files) == {"F-11_knob_logo.svg", "F-11_knob_logo.dxf"} and b'id="logo_engrave"' in files["F-11_knob_logo.svg"]

    m = faro.model(DEFAULTS)
    assert m.parts["knob"].is_valid
    expect = logo.unit_groove_area() * r * r * logo.ENGRAVE_DEPTH
    assert m.info["knob_logo_mm3"] == pytest.approx(expect, rel=0.02)
    assert "knob_logo_fill" in faro.preview_extras(DEFAULTS)
    checks = logo.consistency(r, m.info)
    assert all(ok for _, ok, _ in checks), checks

    txt = _text(dr.to_svg(dr.part_drawing(DEFAULTS, _sheet("knob"))))
    assert "FRONT VIEW: LOGO FACE" in txt and "off stop" in txt and "F-11_knob_logo" in txt
    assert any(row["feature"] == "Knob logo" for row in faro.PRODUCTION_CHANGES)


def test_knob_logo_in_the_pack(client, faro_project):
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params})
    zf = zipfile.ZipFile(io.BytesIO(client.get(f"/api/projects/{pid}/factory-pack.zip").content))
    mech = "faro_rfq_pack_v1/mechanical/"
    assert {mech + "artwork/F-11_knob_logo.svg", mech + "artwork/F-11_knob_logo.dxf"} <= set(zf.namelist())
    md = zf.read(mech + "rfq.md").decode()
    assert "Engrave the logo on the knob face" in md and "(on the knob)" in md and "knob logo, 1:1 vector" in md
    assert "artwork/F-11_knob_logo.svg" in zf.read(mech + "bom.csv").decode()
    s = client.get(f"/api/projects/{pid}/factory-pack").json()
    checks = {c["check"]: c for c in s["consistency"]}
    for name in ("Knob logo lines are engravable", "Knob logo SVG / DXF match the artwork", "Knob logo on the 3D model",
                 "Knob logo on the drawing"):
        assert checks[name]["ok"], (name, checks[name])
