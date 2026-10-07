"""The Faro logo (a half sun with seven rays rising over the sea): the brand master and the knob engraving.

The master is traced from the reference image (seed/artwork/reference/logo_reference.webp):
scripts/trace_logo.py finds the plate edges either side of every dark groove, takes the centre-line and
width, and fits smooth curves, stored in brand/logo/bathsheva_emblem_curves.json (reference-image pixels).
This module builds the shapes from those curves: 11 raised shapes (seven rays, the sun and three sea
bands) inside one true circle, separated by the grooves. There is no border ring: the circle is formed
by the ends of the shapes. The ray grooves curve and widen towards the rim, the lowest rays sit on
curved dark wedges, the sun is a little less than a half circle and the top of the horizon band bows
very slightly, all as in the reference. Left and right are pooled, so the master is symmetric.

The master files live in brand/logo/ as bathsheva_emblem.* (SVG, PDF, DXF, transparent PNG, plus the outline loops).

On the knob the grooves are engraved and filled black. The knob version differs from the master in
two ways, both for engraving only:

* the horizon line under the sun is widened to 0.3 mm (in the master it is 0.21-0.23 mm at Ø16 mm);
* a 0.3 mm edge groove runs round the medallion, so the outer ends of the rays and bands (and the
  circle they form) show on the brass face, which is otherwise level with the shapes.

One artwork drives the knob's vector files, the 3D model and the knob drawing, as for the nameplate
lettering (`nameplate.py`). Straight-edged polygons only (curves sampled finely), so the CAD booleans
are exact.
"""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import SEED_DIR
from app.factory.nameplate import _dxf_signature, _loops_of, _shoelace, _sketch_from_loops

ARTWORK_DIR = SEED_DIR / "artwork"
STEM = "F-11_knob_logo"
LOOPS_FILE = "F-11_knob_logo_loops.json"
REFERENCE = ARTWORK_DIR / "reference" / "logo_reference.webp"

BRAND_DIR = SEED_DIR.parents[1] / "brand" / "logo"
CURVES_FILE = "bathsheva_emblem_curves.json"
MASTER_STEM = "bathsheva_emblem"
MASTER_LOOPS_FILE = "bathsheva_emblem_master.json"
MASTER_DIAMETER_MM = 100.0  # size of the master SVG / PDF / DXF (vector, scale freely)
MASTER_PNG_PX = 2048
RAYS = 7  # counted on the reference image: three each side and one at the top

# On the knob.
EDGE_FILLET = 1.0  # the knob's front edge radius (faro.build_model)
FACE_MARGIN = 0.7  # flat face left round the edge groove
EDGE_GROOVE_MM = 0.3  # groove round the medallion (knob only)
KNOB_HORIZON_MM = 0.3  # horizon line under the sun widened to this (knob only)
DESIGN_RADIUS_MM = 8.0  # the medallion radius the knob widths above are set for (Ø20 knob)
ENGRAVE_DEPTH = 0.2
MIN_GROOVE_MM = 0.3  # finest line we ask the engraver for
STEP_PX = 10.0  # curve sampling, reference-image pixels (0.14 mm on the knob; chord error under 0.001 mm)


def logo_radius(knob_diameter: float) -> float:
    """Medallion radius on a knob of this diameter: the edge groove sits inside the front-edge radius with a
    small flat margin (8.0 mm on the Ø20 knob)."""
    return knob_diameter / 2 - EDGE_FILLET - FACE_MARGIN - EDGE_GROOVE_MM


def edge_groove() -> float:
    """Edge groove width as a fraction of the medallion radius."""
    return EDGE_GROOVE_MM / DESIGN_RADIUS_MM


@lru_cache(maxsize=1)
def curves() -> dict[str, Any]:
    return json.loads((BRAND_DIR / CURVES_FILE).read_text())


# ---------------------------------------------------------------------------------------------------
# Groove outlines from the traced curves. Sampled in reference-image pixels (y down), then mapped to a
# unit medallion (radius 1, centred at the origin, +Y up).


def _n(length: float) -> int:
    return max(8, int(math.ceil(length / STEP_PX)))


def _strip(cl: list[tuple[float, float]], widths: list[float]) -> list[tuple[float, float]]:
    """Band of the given widths either side of a centre-line."""
    left, right = [], []
    for i, (x, y) in enumerate(cl):
        (x0, y0), (x1, y1) = cl[max(i - 1, 0)], cl[min(i + 1, len(cl) - 1)]
        tl = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / tl, (x1 - x0) / tl
        h = widths[i] / 2
        left.append((x + nx * h, y + ny * h))
        right.append((x - nx * h, y - ny * h))
    return left + right[::-1]


def _poly(c: list[float], x: float) -> float:
    return sum(k * x ** (len(c) - 1 - i) for i, k in enumerate(c))


def _band_top(c: dict, x: float, shift: float = 0.0) -> float:
    b = c["horizon_band_top"]
    return b["c0"] + shift + b["c2"] * (x - c["frame"]["axis_x"]) ** 2


def horizon_shift_px(c: dict, min_unit: float) -> float:
    """How far the sun's lower edge moves up and the band's top moves down (px each) for the horizon line
    under the sun to be at least min_unit (fraction of the radius) wide; 0 for the master."""
    if min_unit <= 0:
        return 0.0
    ax = c["frame"]["axis_x"]
    s = c["sun"]
    half = math.sqrt(s["r"] ** 2 - (s["cy"] - c["sun_chord_y"]) ** 2)  # the sun's lower edge ends here
    narrowest = min(_band_top(c, ax + half), _band_top(c, ax)) - c["sun_chord_y"]
    return max(0.0, (min_unit * c["frame"]["radius"] - narrowest) / 2)


def groove_polygons_px(c: dict, horizon_min: float = 0.0) -> list[list[tuple[float, float]]]:
    """Groove regions (px, y down); they overlap and run past the medallion's circle."""
    f = c["frame"]
    ax, big = f["axis_x"], f["radius"] * 1.25
    shift = horizon_shift_px(c, horizon_min)
    chord = c["sun_chord_y"] - shift
    out = []
    # Groove round the sun: between the ring's outer circle and the sun, down to the horizon.
    ro, si = c["sun_ring_outer"], c["sun"]
    y_cut = chord + 2.0
    ao = math.asin((ro["cy"] - y_cut) / ro["r"])
    ai = math.asin((si["cy"] - y_cut) / si["r"])
    n = _n(math.pi * ro["r"])
    ring = [(ax + ro["r"] * math.cos(ao + (math.pi - 2 * ao) * i / n), ro["cy"] - ro["r"] * math.sin(ao + (math.pi - 2 * ao) * i / n))
            for i in range(n + 1)]
    ring += [(ax + si["r"] * math.cos(math.pi - ai - (math.pi - 2 * ai) * i / n), si["cy"] - si["r"] * math.sin(math.pi - ai - (math.pi - 2 * ai) * i / n))
             for i in range(n + 1)]
    out.append(ring)
    # Horizon line: from the sun's lower edge to the (slightly bowed) top of the band, full width.
    n = _n(2 * big)
    xs = [ax - big + 2 * big * i / n for i in range(n + 1)]
    out.append([(ax - big, chord), (ax + big, chord)] + [(x, _band_top(c, x, shift)) for x in reversed(xs)])
    # Ray grooves (both sides): centre angle and width against distance from the pivot.
    px_, py_ = c["ray_pivot"]
    for g in c["ray_grooves"]:
        r0, r1 = 250.0, 1.3 * f["radius"]
        n = _n(r1 - r0)
        rs = [r0 + (r1 - r0) * i / n for i in range(n + 1)]
        th = [_poly(g["theta_poly"], r) for r in rs]
        w = [_poly(g["width_poly"], r) for r in rs]
        for side in (1, -1):
            out.append(_strip([(px_ + side * r * math.cos(t), py_ - r * math.sin(t)) for r, t in zip(rs, th)], w))
    # Wave grooves: cosine series about the axis, constant width.
    for wv in c["wave_grooves"]:
        a0, a1, k, a2 = wv["coeffs"]
        n = _n(2 * big)
        cl = []
        for i in range(n + 1):
            x = ax - big + 2 * big * i / n
            t = k * abs(x - ax)
            cl.append((x, a0 + a1 * math.cos(t) + a2 * math.cos(2 * t)))
        out.append(_strip(cl, [wv["width"]] * len(cl)))
    # The dark wedges under the lowest rays: from inside the sun's groove out past the rim, down to the horizon.
    wt = c["wedge_top"]
    d1 = wt["d_max"]
    slope = sum((len(wt["poly"]) - 1 - i) * k * d1 ** (len(wt["poly"]) - 2 - i) for i, k in enumerate(wt["poly"][:-1]))

    def top(d):
        return _poly(wt["poly"], d) if d <= d1 else _poly(wt["poly"], d1) + slope * (d - d1)

    d0, dmax = 270.0, big
    n = _n(dmax - d0)
    ds = [d0 + (dmax - d0) * i / n for i in range(n + 1)]
    for side in (1, -1):
        pts = [(ax + side * d, top(d)) for d in ds] + [(ax + side * dmax, y_cut), (ax + side * d0, y_cut)]
        out.append(pts if side > 0 else pts[::-1])
    return out


def _to_unit(c: dict, pts):
    f = c["frame"]
    return [((x - f["axis_x"]) / f["radius"], (f["centre_y"] - y) / f["radius"]) for x, y in pts]


def _circle(r: float, n: int = 360) -> list[tuple[float, float]]:
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _polygon_solid(pts, z0: float = 0.0, h: float = 1.0):
    from build123d import Face, Vector, Wire, extrude

    f = Face(Wire.make_polygon([Vector(x, y, z0) for x, y in pts], close=True))
    if f.normal_at().Z < 0:
        f = -f
    return extrude(f, amount=h)


def _top_faces(solid):
    from build123d import Axis, Pos, Sketch

    faces = [Pos(0, 0, -1) * s.faces().filter_by(Axis.Z).sort_by(Axis.Z)[-1] for s in solid.solids()]
    return Sketch() + faces


def _grooves_solid(horizon_min: float):
    c = curves()
    solids = [_polygon_solid(_to_unit(c, poly)) for poly in groove_polygons_px(c, horizon_min)]
    return solids[0].fuse(*solids[1:])


@lru_cache(maxsize=2)
def unit_shapes_from_curves(horizon_min: float = 0.0):
    """The raised shapes for a unit medallion (11 faces), built from the traced curves (a few seconds).
    horizon_min > 0 gives the knob version, with the horizon line widened."""
    disc = _polygon_solid(_circle(1.0))
    return _top_faces((disc - _grooves_solid(horizon_min)).clean())


def knob_horizon() -> float:
    return KNOB_HORIZON_MM / DESIGN_RADIUS_MM


@lru_cache(maxsize=1)
def unit_grooves_from_geometry():
    """The engraved region for a unit medallion on the knob: everything inside the edge groove's outer
    circle except the raised shapes (knob version). Stored as loops in seed/artwork/ by
    scripts/export_nameplate_artwork.py."""
    outer = _polygon_solid(_circle(1.0 + edge_groove()))
    shapes = [_polygon_solid(face[0]) for face in _loops_of(unit_shapes_from_curves(knob_horizon()))]
    return _top_faces((outer - shapes[0].fuse(*shapes[1:])).clean())


# ---------------------------------------------------------------------------------------------------
# Knob artwork (runtime reads the stored loops).


@lru_cache(maxsize=1)
def _unit_grooves():
    stored = ARTWORK_DIR / LOOPS_FILE
    if stored.is_file():
        return _sketch_from_loops(json.loads(stored.read_text())["grooves"])
    return unit_grooves_from_geometry()


def grooves(radius: float):
    """Engraved region scaled to a medallion of this radius (mm), centred at the origin, upright (+Y up)."""
    from build123d import scale

    return scale(_unit_grooves(), radius)


def unit_groove_area() -> float:
    return sum(f.area for f in _unit_grooves().faces())


def loops(radius: float) -> list[list[list[tuple[float, float]]]]:
    """Per groove region: [outline, holes...] point lists (mm), for the drawing."""
    return [[[(x * radius, y * radius) for x, y in loop] for loop in face] for face in _unit_loops()]


@lru_cache(maxsize=1)
def _unit_loops():
    return _loops_of(_unit_grooves())


def export(out_dir: Path, radius: float) -> dict[str, Path]:
    """<STEM>.svg and .dxf at 1:1 (mm) for a medallion of this radius: engraved region (filled) plus the
    knob face outline for reference."""
    from build123d import Circle, ExportDXF, ExportSVG, Unit

    g = grooves(radius)
    face = Circle(radius + EDGE_GROOVE_MM + FACE_MARGIN + EDGE_FILLET)
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path, dxf_path = out_dir / f"{STEM}.svg", out_dir / f"{STEM}.dxf"
    svg = ExportSVG(unit=Unit.MM, line_weight=0.05)
    svg.add_layer("knob_outline_reference", line_color="gray", line_weight=0.05)
    svg.add_layer("logo_engrave", fill_color="black", line_color=None, line_weight=0.0)
    svg.add_shape(face.edges(), layer="knob_outline_reference")
    svg.add_shape(g.faces(), layer="logo_engrave")
    svg.write(str(svg_path))
    dxf = ExportDXF(unit=Unit.MM)
    dxf.add_layer("KNOB_OUTLINE_REFERENCE")
    dxf.add_layer("LOGO_ENGRAVE")
    dxf.add_shape(face.edges(), layer="KNOB_OUTLINE_REFERENCE")
    dxf.add_shape(g.faces(), layer="LOGO_ENGRAVE")
    dxf.write(str(dxf_path))
    return {"svg": svg_path, "dxf": dxf_path}


def geometry_params() -> dict[str, Any]:
    """What the stored artwork was generated from (a change here means re-export)."""
    digest = hashlib.sha256((BRAND_DIR / CURVES_FILE).read_bytes()).hexdigest()[:16]
    return {"curves_sha256": digest, "step_px": STEP_PX, "edge_groove_mm": EDGE_GROOVE_MM,
            "knob_horizon_mm": KNOB_HORIZON_MM, "design_radius_mm": DESIGN_RADIUS_MM}


def export_loops(out_dir: Path) -> Path:
    path = out_dir / LOOPS_FILE
    path.write_text(json.dumps({"description": "Knob logo grooves (knob version of brand/logo), unit medallion radius, +Y up",
                                "params": geometry_params(),
                                "grooves": _loops_of(unit_grooves_from_geometry())}, separators=(",", ":")))
    return path


# ---------------------------------------------------------------------------------------------------
# Brand master files.


def master_loops() -> list[list[tuple[float, float]]]:
    """The 11 raised shapes of the master (unit radius, +Y up): stored file, else built from the curves."""
    stored = BRAND_DIR / MASTER_LOOPS_FILE
    if stored.is_file():
        return [[tuple(p) for p in loop] for loop in json.loads(stored.read_text())["shapes"]]
    return [face[0] for face in _loops_of(unit_shapes_from_curves(0.0))]


def export_master(out_dir: Path = BRAND_DIR, fresh: bool = True) -> dict[str, Path]:
    """brand/logo/: outline loops (JSON), SVG, PDF and DXF at Ø100 mm, transparent PNG. Black shapes, no
    border: the circle is formed by the ends of the shapes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    shapes = [face[0] for face in _loops_of(unit_shapes_from_curves(0.0))] if fresh else master_loops()
    paths = {"json": out_dir / MASTER_LOOPS_FILE}
    paths["json"].write_text(json.dumps({"description": "Bathsheva emblem master: 11 raised shapes (7 rays, sun, 3 sea bands), "
                                                         "unit radius, centred at the origin, +Y up",
                                         "params": geometry_params(), "shapes": shapes}, separators=(",", ":")) + "\n")
    r = MASTER_DIAMETER_MM / 2
    # SVG (mm, y down).
    d = " ".join("M " + " L ".join(f"{r + x * r:.4f} {r - y * r:.4f}" for x, y in loop) + " Z" for loop in shapes)
    paths["svg"] = out_dir / f"{MASTER_STEM}.svg"
    paths["svg"].write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * r:g}mm" height="{2 * r:g}mm" viewBox="0 0 {2 * r:g} {2 * r:g}">\n'
        f'  <title>Bathsheva emblem</title>\n  <path fill="#000000" fill-rule="nonzero" d="{d}"/>\n</svg>\n')
    # PDF (page = the medallion's square).
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    paths["pdf"] = out_dir / f"{MASTER_STEM}.pdf"
    cv = canvas.Canvas(str(paths["pdf"]), pagesize=(2 * r * mm, 2 * r * mm), invariant=1)
    cv.setTitle("Bathsheva emblem")
    cv.setFillColorRGB(0, 0, 0)
    p = cv.beginPath()
    for loop in shapes:
        p.moveTo((r + loop[0][0] * r) * mm, (r + loop[0][1] * r) * mm)
        for x, y in loop[1:]:
            p.lineTo((r + x * r) * mm, (r + y * r) * mm)
        p.close()
    cv.drawPath(p, stroke=0, fill=1)
    cv.showPage()
    cv.save()
    # DXF (mm, +Y up, centred on the origin): closed outlines plus a solid fill.
    import ezdxf

    doc = ezdxf.new(units=ezdxf.units.MM)
    doc.layers.add("LOGO")
    msp = doc.modelspace()
    hatch = msp.add_hatch(color=7, dxfattribs={"layer": "LOGO"})
    for loop in shapes:
        pts = [(x * r, y * r) for x, y in loop]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "LOGO"})
        hatch.paths.add_polyline_path(pts, is_closed=True)
    paths["dxf"] = out_dir / f"{MASTER_STEM}.dxf"
    doc.saveas(paths["dxf"])
    # PNG, transparent background, drawn 4x and downsampled.
    from PIL import Image, ImageDraw

    ss, n = 4, MASTER_PNG_PX
    img = Image.new("L", (n * ss, n * ss), 0)
    draw = ImageDraw.Draw(img)
    for loop in shapes:
        draw.polygon([((1 + x) * n * ss / 2, (1 - y) * n * ss / 2) for x, y in loop], fill=255)
    alpha = img.resize((n, n), Image.LANCZOS)
    png = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    png.putalpha(alpha)
    paths["png"] = out_dir / f"{MASTER_STEM}.png"
    png.save(paths["png"], optimize=True)
    return paths


# ---------------------------------------------------------------------------------------------------
# Checks.


def artwork_files(radius: float) -> dict[str, bytes]:
    files = {ext: ARTWORK_DIR / f"{STEM}.{ext}" for ext in ("svg", "dxf")}
    if not all(p.is_file() for p in files.values()):
        files = export(Path(tempfile.mkdtemp(prefix="logo-")), radius)
    return {f"{STEM}.{ext}": p.read_bytes() for ext, p in files.items()}


def consistency(radius: float, built_info: dict[str, Any]) -> list[tuple[str, bool, str]]:
    """The stored vector files, the 3D knob and the drawing all show the same logo."""
    out = list(_artwork_checks(round(radius, 4)))
    area = unit_groove_area() * radius * radius
    etch = built_info.get("knob_logo_mm3", 0.0)
    expect = area * ENGRAVE_DEPTH
    out.append(("Knob logo on the 3D model", expect * 0.98 <= etch <= expect * 1.02,
                f"engraved {etch:.2f} mm³ vs {expect:.2f} mm³ (groove area {area:.2f} mm² × {ENGRAVE_DEPTH:g} mm)"))
    drawn = sum(_shoelace(f[0]) - sum(_shoelace(h) for h in f[1:]) for f in loops(radius))
    out.append(("Knob logo on the drawing", abs(drawn - area) < 0.005 * area, f"groove area drawn {drawn:.2f} mm²"))
    return out


def narrowest_lines_mm(radius: float) -> dict[str, float]:
    """Designed widths on the knob (mm): the horizon line under the sun, the edge groove, the narrowest
    ray, ring and wave grooves."""
    c = curves()
    k = radius / c["frame"]["radius"]
    shift = horizon_shift_px(c, knob_horizon())
    ax, s, ro = c["frame"]["axis_x"], c["sun"], c["sun_ring_outer"]
    half = math.sqrt(s["r"] ** 2 - (s["cy"] - c["sun_chord_y"]) ** 2)
    horizon = min(_band_top(c, ax + half), _band_top(c, ax)) - c["sun_chord_y"] + 2 * shift
    ring = (s["cy"] - s["r"]) - (ro["cy"] - ro["r"])  # at the top, its narrowest
    rays = min(_poly(g["width_poly"], g["r_range"][0]) for g in c["ray_grooves"])
    waves = min(w["width"] for w in c["wave_grooves"])
    return {"horizon": horizon * k, "edge": EDGE_GROOVE_MM * radius / DESIGN_RADIUS_MM, "sun_ring": ring * k,
            "rays": rays * k, "waves": waves * k}


@lru_cache(maxsize=2)
def _artwork_checks(radius: float) -> tuple[tuple[str, bool, str], ...]:
    out = []
    w = narrowest_lines_mm(radius)
    finest = min(w.values())
    out.append(("Knob logo lines are engravable", finest >= MIN_GROOVE_MM - 1e-6,
                f"finest groove {finest:.2f} mm (≥ {MIN_GROOVE_MM:g} mm): horizon {w['horizon']:.2f}, edge {w['edge']:.2f}, "
                f"sun ring {w['sun_ring']:.2f}, rays {w['rays']:.2f}, waves {w['waves']:.2f} mm; medallion Ø{2 * radius:.1f} mm"))
    fresh = export(Path(tempfile.mkdtemp(prefix="logo-check-")), radius)
    stored = artwork_files(radius)
    same = (stored.get(fresh["svg"].name) == fresh["svg"].read_bytes()
            and _dxf_signature(stored.get(fresh["dxf"].name, b"")) == _dxf_signature(fresh["dxf"].read_bytes()))
    # The stored outlines were generated from the current curves (tests also regenerate and compare them).
    params = geometry_params()
    for path in (ARTWORK_DIR / LOOPS_FILE, BRAND_DIR / MASTER_LOOPS_FILE):
        same = same and path.is_file() and json.loads(path.read_text()).get("params") == params
    out.append(("Knob logo SVG / DXF match the artwork", same,
                "stored files match a fresh export and the brand master" if same
                else "stored artwork is out of date: run scripts/export_nameplate_artwork.py"))
    return tuple(out)
