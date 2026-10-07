"""The logo (a half sun with seven rays rising over the sea) engraved on the dimmer knob's face.

One artwork drives the vector files for the engraver, the 3D model and the knob drawing, as for the
nameplate lettering (`nameplate.py`). The logo is redrawn as clean geometry from the reference image
(seed/artwork/reference/logo_reference.webp): a medallion of raised segments separated by grooves.
Proportions are fractions of the medallion radius R, measured from the reference:

* horizon 0.234 R below the centre; half sun of radius 0.43 R sitting on it;
* seven rays, evenly spread over the half circle (180°/7 apart), radiating from the sun's centre; the lowest pair sit on a slight wedge above
  the horizon (8° at the rim);
* two wave grooves below the horizon (lowest at the centre, wavelength 1.05 R, amplitude 0.05 R);
* grooves 0.05 R wide (rays, sun, horizon, rim) and 0.07 R (waves).

What is engraved (and filled black) is the grooves plus a rim groove just outside the medallion, so
the medallion reads as a disc on the knob face. Straight-edged polygons only (curves sampled finely),
so the CAD booleans are exact.
"""

from __future__ import annotations

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

# Proportions (fractions of the medallion radius), measured from the reference image.
HORIZON_Y = -0.234
SUN_R = 0.43
RAYS = 7  # counted on the reference image: three each side and one at the top
GROOVE = 0.05
WAVE_GROOVE = 0.07
WAVES = (-0.40, -0.59)  # wave groove centre lines
WAVE_AMP = 0.05
WAVE_LEN = 1.05
LOW_RAY_WEDGE_DEG = (2.0, 8.0)  # the lowest rays' wedge above the horizon: at the sun, at the rim

# On the knob.
EDGE_FILLET = 1.0  # the knob's front edge radius (faro.build_model)
FACE_MARGIN = 0.6  # flat face left round the logo's rim groove
ENGRAVE_DEPTH = 0.2
MIN_GROOVE_MM = 0.3  # finest line we ask the engraver for
STEP = 0.015  # curve sampling (fraction of R)


def logo_radius(knob_diameter: float) -> float:
    """Medallion radius on a knob of this diameter: the rim groove sits inside the front-edge radius with a
    small flat margin."""
    return (knob_diameter / 2 - EDGE_FILLET - FACE_MARGIN) / (1 + GROOVE)


def _arc(cx: float, cy: float, r: float, a0: float, a1: float) -> list[tuple[float, float]]:
    n = max(8, int(abs(a1 - a0) * r / STEP))
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def _cutters() -> list[list[tuple[float, float]]]:
    """Groove regions (polygons, unit medallion radius); they may overlap and run past the rim."""
    cx, cy = 0.0, HORIZON_Y
    g, out = GROOVE, []
    big = 1.5
    # Horizon groove across the whole medallion.
    out.append([(-big, cy - g / 2), (big, cy - g / 2), (big, cy + g / 2), (-big, cy + g / 2)])
    # Groove round the sun (upper half annulus).
    outer = _arc(cx, cy, SUN_R + g, 0, math.pi)
    inner = _arc(cx, cy, SUN_R, math.pi, 0)
    out.append(outer + inner)
    # Radial grooves between the rays (constant width), from the sun groove outwards.
    for k in range(1, RAYS):
        a = math.pi * k / RAYS
        ux, uy, nx, ny = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
        r0, r1 = SUN_R, 2.0
        out.append([(cx + r0 * ux + nx * g / 2, cy + r0 * uy + ny * g / 2), (cx + r1 * ux + nx * g / 2, cy + r1 * uy + ny * g / 2),
                    (cx + r1 * ux - nx * g / 2, cy + r1 * uy - ny * g / 2), (cx + r0 * ux - nx * g / 2, cy + r0 * uy - ny * g / 2)])
    # The lowest rays sit on a wedge above the horizon, wider at the rim.
    a_in, a_out = (math.radians(v) for v in LOW_RAY_WEDGE_DEG)
    for side in (1, -1):
        p0 = (cx + side * (SUN_R + g) * math.cos(a_in), cy + (SUN_R + g) * math.sin(a_in))
        p1 = (cx + side * 2.0 * math.cos(a_out), cy + 2.0 * math.sin(a_out))
        poly = [p0, p1, (p1[0], cy), (p0[0], cy)]
        out.append(poly if side > 0 else poly[::-1])
    # Wave grooves.
    for c in WAVES:
        xs = [-big + i * STEP for i in range(int(2 * big / STEP) + 1)]
        top = [(x, c - WAVE_AMP * math.cos(2 * math.pi * x / WAVE_LEN) + WAVE_GROOVE / 2) for x in xs]
        bot = [(x, c - WAVE_AMP * math.cos(2 * math.pi * x / WAVE_LEN) - WAVE_GROOVE / 2) for x in reversed(xs)]
        out.append(top + bot)
    return out


def _polygon_solid(pts, z0: float = 0.0, h: float = 1.0):
    from build123d import Face, Vector, Wire, extrude

    f = Face(Wire.make_polygon([Vector(x, y, z0) for x, y in pts], close=True))
    if f.normal_at().Z < 0:
        f = -f
    return extrude(f, amount=h)


@lru_cache(maxsize=1)
def unit_grooves_from_geometry():
    """The engraved region for a unit medallion: grooves inside the disc plus the rim groove. Slow-ish
    (a few seconds); stored as loops in seed/artwork/ by scripts/export_nameplate_artwork.py."""
    from build123d import Axis, Pos, Sketch

    disc = _polygon_solid(_arc(0, 0, 1.0, 0, 2 * math.pi)[:-1])
    cut = None
    for poly in _cutters():
        s = _polygon_solid(poly)
        cut = s if cut is None else cut.fuse(s)
    inside = cut & disc
    rim = _polygon_solid(_arc(0, 0, 1.0 + GROOVE, 0, 2 * math.pi)[:-1]) - disc
    solid = (inside.fuse(rim)).clean()
    faces = [Pos(0, 0, -1) * sol.faces().filter_by(Axis.Z).sort_by(Axis.Z)[-1] for sol in solid.solids()]
    return Sketch() + faces


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
    face = Circle(radius + GROOVE * radius + FACE_MARGIN + EDGE_FILLET)
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
    """The proportions the stored artwork was generated from (a change here means re-export)."""
    return {"horizon_y": HORIZON_Y, "sun_r": SUN_R, "rays": RAYS, "groove": GROOVE, "wave_groove": WAVE_GROOVE,
            "waves": list(WAVES), "wave_amp": WAVE_AMP, "wave_len": WAVE_LEN, "low_ray_wedge_deg": list(LOW_RAY_WEDGE_DEG),
            "step": STEP}


def export_loops(out_dir: Path) -> Path:
    path = out_dir / LOOPS_FILE
    path.write_text(json.dumps({"description": "Knob logo grooves, unit medallion radius, +Y up",
                                "params": geometry_params(),
                                "grooves": _loops_of(unit_grooves_from_geometry())}, separators=(",", ":")))
    return path


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


@lru_cache(maxsize=2)
def _artwork_checks(radius: float) -> tuple[tuple[str, bool, str], ...]:
    out = []
    groove_mm = GROOVE * radius
    out.append(("Knob logo lines are engravable", groove_mm >= MIN_GROOVE_MM,
                f"finest groove {groove_mm:.2f} mm (≥ {MIN_GROOVE_MM:g} mm), wave grooves {WAVE_GROOVE * radius:.2f} mm, "
                f"medallion Ø{2 * radius:.1f} mm"))
    fresh = export(Path(tempfile.mkdtemp(prefix="logo-check-")), radius)
    stored = artwork_files(radius)
    same = (stored.get(fresh["svg"].name) == fresh["svg"].read_bytes()
            and _dxf_signature(stored.get(fresh["dxf"].name, b"")) == _dxf_signature(fresh["dxf"].read_bytes()))
    # The stored outlines were generated from the current proportions (tests also regenerate and compare them).
    stored_path = ARTWORK_DIR / LOOPS_FILE
    same = same and stored_path.is_file() and json.loads(stored_path.read_text()).get("params") == geometry_params()
    out.append(("Knob logo SVG / DXF match the artwork", same,
                "stored files match a fresh export" if same else "stored artwork is out of date: run scripts/export_nameplate_artwork.py"))
    return tuple(out)
