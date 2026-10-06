"""FARO nameplate lettering: one artwork for the vector files, the 3D model and the drawing.

Lettering: "FARO" in Cormorant Garamond SemiBold (the Bathsheva manuals' typeface), bundled in
seed/fonts/ so every machine produces the same outlines. Cap height 5.0 mm (as on the
prototype), centred optically on the plate: all capitals, no descenders, so the outline's
bounding box is centred on the plate (no em-box offset). The plate outline is the production
nameplate (37 × 11.5 mm, R1.2).

The exported files are stored in seed/artwork/ (scripts/export_nameplate_artwork.py); the
Factory Pack checks they still match the artwork generated here.
"""

from __future__ import annotations

import math
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import SEED_DIR

TEXT = "FARO"
FONT_PATH = SEED_DIR / "fonts" / "CormorantGaramond-SemiBold.ttf"
FONT_NAME = "Cormorant Garamond SemiBold"
CAP_HEIGHT = 5.0  # mm, as the prototype's lettering
CORNER_R = 1.2
ETCH_DEPTH = 0.15  # etched into the plate, filled black, flush
FLATTEN_STEP = 8.0  # font units (about 0.063 mm): curves become polylines this fine (chord error < 0.003 mm)
ARTWORK_DIR = SEED_DIR / "artwork"
STEM = "F-05_nameplate_lettering"


def _glyph_contours(text: str) -> list[list[list[tuple[str, list[tuple[float, float]]]]]]:
    """Per letter, its contours as segments ("line" | "quad" | "cubic", points) in font units, read
    straight from the bundled TTF with fontTools (not the CAD kernel's font engine, which mangles
    some of this font's glyphs)."""
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont

    class Collect(BasePen):
        def __init__(self, glyphset, dx):
            super().__init__(glyphset)
            self.dx, self.contours, self.cur, self.start, self.pt = dx, [], [], None, None

        def _p(self, p):
            return (p[0] + self.dx, p[1])

        def _moveTo(self, p):
            self.cur, self.start, self.pt = [], self._p(p), self._p(p)

        def _lineTo(self, p):
            q = self._p(p)
            if q != self.pt:
                self.cur.append(("line", [self.pt, q]))
            self.pt = q

        def _qCurveToOne(self, p1, p2):
            q1, q2 = self._p(p1), self._p(p2)
            self.cur.append(("quad", [self.pt, q1, q2]))
            self.pt = q2

        def _curveToOne(self, p1, p2, p3):
            pts = [self.pt, self._p(p1), self._p(p2), self._p(p3)]
            self.cur.append(("cubic", pts))
            self.pt = pts[-1]

        def _closePath(self):
            if self.pt != self.start:
                self.cur.append(("line", [self.pt, self.start]))
            self.contours.append(self.cur)
            self.cur = []

    font = TTFont(str(FONT_PATH))
    glyphs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    x, out = 0.0, []
    for ch in text:
        name = cmap[ord(ch)]
        pen = Collect(glyphs, x)
        glyphs[name].draw(pen)
        out.append(pen.contours)
        x += hmtx[name][0]
    return out


def _bezier_point(ps, t: float) -> tuple[float, float]:
    pts = [tuple(map(float, p)) for p in ps]
    while len(pts) > 1:
        pts = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(pts, pts[1:])]
    return pts[0]


def _polyline(segs, step: float = FLATTEN_STEP) -> list[tuple[float, float]]:
    """A contour flattened to a closed polyline (font units); curves split every `step` units or finer."""
    pts: list[tuple[float, float]] = []
    for kind, ps in segs:
        if kind == "line":
            pts.append(tuple(map(float, ps[0])))
            continue
        ctrl = sum(math.dist(a, b) for a, b in zip(ps, ps[1:]))
        k = max(2, math.ceil(ctrl / step))
        pts += [_bezier_point(ps, i / k) for i in range(k)]
    return pts


def _winding(pt: tuple[float, float], polys: list[list[tuple[float, float]]]) -> int:
    """Nonzero winding number of a point (how TrueType fills overlapping and self-crossing contours)."""
    x, y, w = pt[0], pt[1], 0
    for poly in polys:
        for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
            cross = (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)
            if y1 <= y < y2 and cross > 0:
                w += 1
            elif y2 <= y < y1 and cross < 0:
                w -= 1
    return w


def _inside_point(face) -> tuple[float, float] | None:
    from build123d import Vector

    bb = face.bounding_box()
    for i in range(1, 40):
        for j in range(1, 40):
            p = Vector(bb.min.X + bb.size.X * i / 40, bb.min.Y + bb.size.Y * j / 40, 0)
            if face.is_inside(p):
                return (p.X, p.Y)
    return None


def _letter_solid(polys: list[list[tuple[float, float]]]):
    """One letter as a 1-unit-thick solid: split every edge at its crossings, build the enclosed regions,
    keep those the nonzero winding rule fills, extrude and fuse them. Handles overlapping contours
    (F and A crossbars) and self-crossing ones (this font's A). Straight edges only, so it is exact."""
    from build123d import Compound, Edge, Vector, extrude
    from OCP.BOPAlgo import BOPAlgo_Tools
    from OCP.TopoDS import TopoDS_Compound

    edges = [Edge.make_line(Vector(*a), Vector(*b)) for poly in polys for a, b in zip(poly, poly[1:] + poly[:1])]
    split = edges[0].fuse(*edges[1:])
    wires, faces = TopoDS_Compound(), TopoDS_Compound()
    BOPAlgo_Tools.EdgesToWires_s(split.wrapped, wires, False)
    BOPAlgo_Tools.WiresToFaces_s(wires, faces)
    keep = [f for f in Compound(faces).faces() if (pt := _inside_point(f)) is not None and _winding(pt, polys) != 0]
    sols = [extrude(f if f.normal_at().Z > 0 else -f, amount=1) for f in keep]
    return (sols[0].fuse(*sols[1:]) if len(sols) > 1 else sols[0]).clean()


@lru_cache(maxsize=1)
def letters_from_font():
    """One clean planar face per letter, cap height CAP_HEIGHT, centred optically on the plate, built from
    the bundled font (slow: a few seconds). The result is stored as point loops in seed/artwork/."""
    from build123d import Axis, Pos, Sketch, scale

    glyphs = [[_polyline(segs) for segs in contours] for contours in _glyph_contours(TEXT)]
    pts = [p for g in glyphs for poly in g for p in poly]
    ymin, ymax = min(p[1] for p in pts), max(p[1] for p in pts)
    xmin, xmax = min(p[0] for p in pts), max(p[0] for p in pts)
    k = CAP_HEIGHT / (ymax - ymin)
    faces = []
    for g in glyphs:
        solid = _letter_solid(g)
        # the top face of each solid (normal +Z), moved back down to z = 0
        faces += [Pos(0, 0, -1) * sol.faces().filter_by(Axis.Z).sort_by(Axis.Z)[-1] for sol in solid.solids()]
    sk = Pos(-(xmin + xmax) / 2 * k, -(ymin + ymax) / 2 * k) * scale(Sketch() + faces, k)
    # All capitals and no descenders: the outline's own centre is the optical centre (no em-box offset).
    return sk


LOOPS_FILE = "F-05_nameplate_lettering_loops.json"


def _loops_of(sk) -> list[list[list[tuple[float, float]]]]:
    from build123d import Vertex
    from OCP.BRepTools import BRepTools_WireExplorer

    def loop(w):
        exp, pts = BRepTools_WireExplorer(w.wrapped), []
        while exp.More():
            v = Vertex(exp.CurrentVertex())
            pts.append((round(v.X, 6), round(v.Y, 6)))
            exp.Next()
        return pts

    return [[loop(f.outer_wire())] + [loop(w) for w in f.inner_wires()] for f in sk.faces()]


def _sketch_from_loops(loops):
    from build123d import Face, Sketch, Vector, Wire

    def wire(pts):
        return Wire.make_polygon([Vector(x, y, 0) for x, y in pts], close=True)

    return Sketch() + [Face(wire(face[0]), [wire(h) for h in face[1:]]) for face in loops]


@lru_cache(maxsize=1)
def _letters_cached():
    """The artwork: stored loops (seed/artwork) if present, else built from the font."""
    import json

    stored = ARTWORK_DIR / LOOPS_FILE
    if stored.is_file():
        return _sketch_from_loops(json.loads(stored.read_text())["letters"])
    return letters_from_font()


def nonzero_area(step: float = 3.0) -> float:
    """Independent check of the filled lettering area (mm²): the font contours sampled on a grid with
    the nonzero winding rule, without the CAD kernel."""
    import numpy as np

    glyphs = [[np.array(_polyline(s)) for s in c] for c in _glyph_contours(TEXT)]
    allp = np.vstack([p for g in glyphs for p in g])
    k = CAP_HEIGHT / (allp[:, 1].max() - allp[:, 1].min())
    total = 0
    for polys in glyphs:
        pp = np.vstack(polys)
        xs = np.arange(pp[:, 0].min(), pp[:, 0].max(), step) + step / 2
        ys = np.arange(pp[:, 1].min(), pp[:, 1].max(), step) + step / 2
        X, Y = np.meshgrid(xs, ys)
        W = np.zeros(X.shape, dtype=int)
        for poly in polys:
            q = np.roll(poly, -1, axis=0)
            for (x1, y1), (x2, y2) in zip(poly, q):
                c = (x2 - x1) * (Y - y1) - (X - x1) * (y2 - y1)
                W += ((y1 <= Y) & (Y < y2) & (c > 0)).astype(int) - ((y2 <= Y) & (Y < y1) & (c < 0)).astype(int)
        total += (W != 0).sum() * step * step
    return total * k * k


def shapes():
    """(plate outline, lettering faces), centred on the plate, in plate coordinates (mm)."""
    import copy

    from build123d import RectangleRounded

    from app.cad import faro

    plate = RectangleRounded(faro.NAMEPLATE_W, faro.NAMEPLATE_H, CORNER_R)
    return plate, copy.copy(_letters_cached())


@lru_cache(maxsize=1)
def letter_loops() -> list[list[list[tuple[float, float]]]]:
    """Per letter: [outline, counter, ...] as point lists (mm, plate centre at 0, 0), in wire order.
    The drawing uses these, so it shows exactly the artwork."""
    from build123d import Vertex
    from OCP.BRepTools import BRepTools_WireExplorer

    def loop(w):
        exp, pts = BRepTools_WireExplorer(w.wrapped), []
        while exp.More():
            v = Vertex(exp.CurrentVertex())
            pts.append((v.X, v.Y))
            exp.Next()
        return pts

    return [[loop(f.outer_wire())] + [loop(w) for w in f.inner_wires()] for f in shapes()[1].faces()]


@lru_cache(maxsize=1)
def letter_area() -> float:
    return sum(f.area for f in shapes()[1].faces())


def export(out_dir: Path) -> dict[str, Path]:
    """Write <STEM>.svg and <STEM>.dxf (millimetres, 1:1) into out_dir."""
    from build123d import ExportDXF, ExportSVG, Unit

    plate, letters = shapes()
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path, dxf_path = out_dir / f"{STEM}.svg", out_dir / f"{STEM}.dxf"
    svg = ExportSVG(unit=Unit.MM, line_weight=0.05)
    svg.add_layer("plate_outline_reference", line_color="gray", line_weight=0.05)
    svg.add_layer("lettering_etch", fill_color="black", line_color=None, line_weight=0.0)
    svg.add_shape(plate.edges(), layer="plate_outline_reference")
    svg.add_shape(letters.faces(), layer="lettering_etch")
    svg.write(str(svg_path))
    dxf = ExportDXF(unit=Unit.MM)
    dxf.add_layer("PLATE_OUTLINE_REFERENCE")
    dxf.add_layer("LETTERING_ETCH")
    dxf.add_shape(plate.edges(), layer="PLATE_OUTLINE_REFERENCE")
    dxf.add_shape(letters.faces(), layer="LETTERING_ETCH")
    dxf.write(str(dxf_path))
    return {"svg": svg_path, "dxf": dxf_path}


def export_loops(out_dir: Path) -> Path:
    """Store the artwork outlines built from the font, so other runs needn't rebuild them."""
    import json

    path = out_dir / LOOPS_FILE
    path.write_text(json.dumps({"text": TEXT, "font": FONT_NAME, "cap_height_mm": CAP_HEIGHT,
                                "letters": _loops_of(letters_from_font())}, separators=(",", ":")))
    return path


def artwork_files() -> dict[str, bytes]:
    """The stored artwork (seed/artwork); exported on the fly if it is missing."""
    files = {ext: ARTWORK_DIR / f"{STEM}.{ext}" for ext in ("svg", "dxf")}
    if not all(p.is_file() for p in files.values()):
        files = export(Path(tempfile.mkdtemp(prefix="nameplate-")))
    return {f"{STEM}.{ext}": p.read_bytes() for ext, p in files.items()}


def consistency(saved_part_info: dict[str, Any], built_info: dict[str, Any]) -> list[tuple[str, bool, str]]:
    """The vector files, the 3D model and the drawing all show the same lettering."""
    out = list(_artwork_checks())
    area = letter_area()
    # 3. 3D model: etched volume = lettering area × etch depth (a little more from the curved plate).
    etch = built_info.get("nameplate_etch_mm3", 0.0)
    expect = area * ETCH_DEPTH
    ok3d = expect * 0.98 <= etch <= expect * 1.03
    saved = saved_part_info.get("nameplate", {}).get("volume_mm3")
    out.append(("Nameplate lettering on the 3D model", ok3d,
                f"etched {etch:.2f} mm³ vs {expect:.2f} mm³ (area × {ETCH_DEPTH:g} mm depth)"
                + (f"; saved CAD nameplate {saved:.1f} mm³" if saved else "")))
    # 4. Drawing: drawn from letter_loops(), i.e. these faces.
    loops = letter_loops()
    loop_area = sum(_shoelace(face[0]) - sum(_shoelace(h) for h in face[1:]) for face in loops)
    out.append(("Nameplate lettering on the drawing", abs(loop_area - area) < 0.005 * area and len(loops) == len(TEXT),
                f"{len(loops)} letters drawn, area {loop_area:.2f} mm²"))
    return out


@lru_cache(maxsize=1)
def _artwork_checks() -> tuple[tuple[str, bool, str], ...]:
    """Project-independent checks of the artwork itself (computed once per process)."""
    out = []
    plate, letters = shapes()
    area = letter_area()
    bb = letters.bounding_box()
    # 1. Artwork geometry: the CAD kernel's face area against an independent nonzero-winding count.
    nz = nonzero_area()
    centred = abs(bb.center().X) < 0.01 and abs(bb.center().Y) < 0.01
    fits = bb.size.X < faro_dims()[0] - 4 and bb.size.Y < faro_dims()[1] - 4
    out.append(("Nameplate lettering is clean and centred", abs(area - nz) < 0.01 * nz and centred and fits,
                f"{FONT_NAME}, {bb.size.X:.1f} × {bb.size.Y:.2f} mm, centre ({bb.center().X:+.2f}, {bb.center().Y:+.2f}); "
                f"area {area:.2f} mm² (font contours: {nz:.2f} mm²)"))
    # 2. Vector files in the pack: stored copies equal a fresh export, and the SVG holds the same outlines.
    fresh = export(Path(tempfile.mkdtemp(prefix="nameplate-check-")))
    stored = artwork_files()
    same = (stored.get(fresh["svg"].name) == fresh["svg"].read_bytes()
            and _dxf_signature(stored.get(fresh["dxf"].name, b"")) == _dxf_signature(fresh["dxf"].read_bytes()))
    font_loops = _loops_of(letters_from_font())
    import json

    stored_path = ARTWORK_DIR / LOOPS_FILE
    stored_loops = json.loads(stored_path.read_text())["letters"] if stored_path.is_file() else None
    same = same and stored_loops is not None and \
        [[[tuple(p) for p in loop] for loop in face] for face in stored_loops] == font_loops
    out.append(("Nameplate SVG / DXF match the artwork", same,
                "stored files match a fresh export" if same else "stored artwork is out of date: run scripts/export_nameplate_artwork.py"))
    return tuple(out)


def faro_dims() -> tuple[float, float]:
    from app.cad import faro

    return faro.NAMEPLATE_W, faro.NAMEPLATE_H


def _shoelace(pts) -> float:
    return abs(0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])))


def _dxf_signature(data: bytes) -> list[tuple]:
    """DXF geometry (entity type, layer, points to 1 µm), ignoring the header's date and random IDs."""
    import io

    import ezdxf

    if not data:
        return []
    doc = ezdxf.read(io.StringIO(data.decode("utf-8", errors="replace")))
    sig = []
    for e in doc.modelspace():
        if e.dxftype() == "LINE":
            pts = [e.dxf.start, e.dxf.end]
        elif e.dxftype() == "ARC":
            pts = [e.dxf.center, (e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle)]
        elif e.dxftype() == "LWPOLYLINE":
            pts = list(e.get_points("xy"))
        elif e.dxftype() == "SPLINE":
            pts = list(e.control_points)
        else:
            pts = []
        sig.append((e.dxftype(), e.dxf.layer, tuple(tuple(round(float(v), 3) for v in p) for p in pts)))
    return sig
