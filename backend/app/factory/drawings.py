"""2D quotation drawings (SVG and PDF) from the generated CAD solids.

Pure: takes CAD parameters plus part metadata, returns a reportlab Drawing that is
rendered to both SVG and PDF, so the two formats always match. No database access.

Each sheet is A4 landscape with a full section through the part's axis (cut from
the same solid that is exported to STEP, so the drawing always matches the CAD), a
plan view or flat pattern where that is how the part is made, overall dimensions,
wall thickness, notes and a title block that says the dimensions are for
quotation only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from build123d import Plane, Pos, Rectangle, Rot
from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Polygon, Rect, String
from reportlab.lib import colors

from app.cad import faro

PT_PER_MM = 72 / 25.4
PAGE_W, PAGE_H = 842.0, 595.0  # A4 landscape, points
MARGIN = 18.0
TITLE_W, TITLE_H = 330.0, 128.0
STANDARD_SCALES = [0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 10]
TOLERANCE_NOTE = "Dimensions for quotation, tolerances to be agreed"
INK = colors.HexColor("#1a1a1a")
DIM = colors.HexColor("#1f4e9c")
SECTION_FILL = colors.HexColor("#d9dde3")
WARN = colors.HexColor("#b3261e")
UNV = colors.HexColor("#8a5a00")

# Parts the drawings cover (made to drawing); bought-in parts are specified by datasheet.
DRAWN_PARTS = ["base", "band_cream", "tower", "diffuser", "gallery", "railing", "lantern_frame", "lantern_glass", "cap",
               "cap_spigot", "finial", "knob", "nameplate", "weight_plate", "base_plate"]
# Parts drawn with a plan (top) view as well as the section.
PLAN_PARTS = {"weight_plate", "base_plate", "base", "lantern_frame", "cap_spigot"}
SPUN = {"base", "tower", "cap"}
# The process each part's drawing notes are written for. The Factory Pack checks the part's
# chosen process against it, so a changed route can't ship with stale notes.
NOTE_PROCESS = {
    "base": "metal_spinning", "tower": "metal_spinning", "cap": "metal_spinning", "gallery": "metal_spinning",
    "band_cream": "cnc_turning_near_net", "lantern_frame": "cnc_turning_near_net", "cap_spigot": "cnc_turning_near_net",
    "finial": "cnc_turning_near_net", "knob": "cnc_turning_near_net",
    "railing": "photo_etching", "nameplate": "photo_etching",
    "diffuser": "glass_tube_cut", "lantern_glass": "glass_tube_cut",
}


@dataclass
class PartSheet:
    cad_key: str
    part_no: str
    name: str
    material: str
    process: str
    finish: str
    quantity: int
    project: str
    cad_version: int | None
    date: str
    unverified: list[str] = field(default_factory=list)  # values on the sheet that are unverified
    safety: list[str] = field(default_factory=list)  # safety-relevant notes


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------


def _text(g: Group, x: float, y: float, s: str, size: float = 7.5, anchor: str = "start", color=INK, bold: bool = False):
    g.add(String(x, y, s, fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=size, fillColor=color,
                 textAnchor=anchor))


def _arrow(g: Group, x: float, y: float, angle: float, size: float = 4.0):
    a = math.radians(angle)
    left = (x - size * math.cos(a - 0.35), y - size * math.sin(a - 0.35))
    right = (x - size * math.cos(a + 0.35), y - size * math.sin(a + 0.35))
    g.add(Polygon([x, y, *left, *right], fillColor=DIM, strokeColor=DIM, strokeWidth=0.3))


def _dim_h(g: Group, x1: float, x2: float, y_feature: float, y: float, label: str):
    """Horizontal dimension between x1 and x2, drawn at height y, with extension lines from y_feature."""
    for x in (x1, x2):
        g.add(Line(x, y_feature, x, y + (3 if y > y_feature else -3), strokeColor=DIM, strokeWidth=0.35))
    g.add(Line(x1, y, x2, y, strokeColor=DIM, strokeWidth=0.5))
    _arrow(g, x1, y, 180)
    _arrow(g, x2, y, 0)
    _text(g, (x1 + x2) / 2, y + 2.5, label, 7.5, "middle", DIM)


def _dim_v(g: Group, y1: float, y2: float, x_feature: float, x: float, label: str):
    """Vertical dimension between y1 and y2 at x, with extension lines from x_feature."""
    for y in (y1, y2):
        g.add(Line(x_feature, y, x + (3 if x > x_feature else -3), y, strokeColor=DIM, strokeWidth=0.35))
    g.add(Line(x, y1, x, y2, strokeColor=DIM, strokeWidth=0.5))
    _arrow(g, x, y1, 270)
    _arrow(g, x, y2, 90)
    tx = x + 3 if x > x_feature else x - 3
    _text(g, tx, (y1 + y2) / 2 - 2.5, label, 7.5, "start" if x > x_feature else "end", DIM)


def _leader(g: Group, x: float, y: float, tx: float, ty: float, label: str):
    g.add(Line(x, y, tx, ty, strokeColor=DIM, strokeWidth=0.4))
    g.add(Circle(x, y, 0.9, fillColor=DIM, strokeColor=DIM))
    _text(g, tx + (2 if tx >= x else -2), ty - 2.5, label, 7.5, "start" if tx >= x else "end", DIM)


def _centreline(g: Group, x: float, y1: float, y2: float):
    g.add(Line(x, y1, x, y2, strokeColor=INK, strokeWidth=0.3, strokeDashArray=[8, 2, 1.5, 2]))


def _choose_scale(width_mm: float, height_mm: float, box_w: float, box_h: float) -> float:
    for n in STANDARD_SCALES:
        if width_mm * PT_PER_MM / n <= box_w and height_mm * PT_PER_MM / n <= box_h:
            return n
    return STANDARD_SCALES[-1]


def _fmt(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# Sheet
# ---------------------------------------------------------------------------


def _frame_and_title(g: Group, sheet: PartSheet, scale: float):
    g.add(Rect(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN, fillColor=None, strokeColor=INK, strokeWidth=0.8))
    x0, y0 = PAGE_W - MARGIN - TITLE_W, MARGIN
    g.add(Rect(x0, y0, TITLE_W, TITLE_H, fillColor=colors.white, strokeColor=INK, strokeWidth=0.8))
    rows = [
        ("Project", sheet.project), ("Part", f"{sheet.part_no}  {sheet.name}"),
        ("Material", sheet.material or "TBD"), ("Process", sheet.process or "TBD"), ("Finish", sheet.finish or "TBD"),
        ("Qty per lamp", str(sheet.quantity)),
        ("CAD", f"v{sheet.cad_version}" if sheet.cad_version else "not generated"),
        ("Scale / units", f"1:{_fmt(scale)}  ·  mm  ·  A4"), ("Date", sheet.date),
    ]
    row_h = 10.5
    for i, (k, v) in enumerate(rows):
        y = y0 + TITLE_H - 13 - i * row_h
        _text(g, x0 + 6, y, k, 6.5, color=colors.HexColor("#555555"))
        _text(g, x0 + 70, y, v[:62], 7.5, bold=(k == "Part"))
    _text(g, x0 + 6, y0 + 15, TOLERANCE_NOTE.upper(), 7.5, bold=True)
    _text(g, x0 + 6, y0 + 5, "Unverified design values — confirm before tooling.  Bathsheva London / Product Workbench",
          6.0, color=WARN)


def _wrap(text: str, width: int = 88) -> list[str]:
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width and line:
            out.append(line)
            line = "   " + word
        else:
            line = f"{line} {word}".strip() if not line.startswith("   ") or line.strip() else line + word
    if line:
        out.append(line)
    return out


def _notes(g: Group, lines: list[tuple[str, Any]]):
    x0 = PAGE_W - MARGIN - TITLE_W
    y = MARGIN + TITLE_H + 12
    for text, color in reversed(lines):
        for part in reversed(_wrap(text)):
            _text(g, x0 + 2, y, part, 7.0, color=color)
            y += 9
    _text(g, x0 + 2, y + 2, "NOTES", 7.5, bold=True)


# ---------------------------------------------------------------------------
# Sheet
# ---------------------------------------------------------------------------


def _frame_and_title(g: Group, sheet: PartSheet, scale: float):
    g.add(Rect(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN, fillColor=None, strokeColor=INK, strokeWidth=0.8))
    x0, y0 = PAGE_W - MARGIN - TITLE_W, MARGIN
    g.add(Rect(x0, y0, TITLE_W, TITLE_H, fillColor=colors.white, strokeColor=INK, strokeWidth=0.8))
    rows = [
        ("Project", sheet.project), ("Part", f"{sheet.part_no}  {sheet.name}"),
        ("Material", sheet.material or "TBD"), ("Process", sheet.process or "TBD"), ("Finish", sheet.finish or "TBD"),
        ("Qty per lamp", str(sheet.quantity)),
        ("CAD", f"v{sheet.cad_version}" if sheet.cad_version else "not generated"),
        ("Scale / units", f"1:{_fmt(scale)}  ·  mm  ·  A4"), ("Date", sheet.date),
    ]
    row_h = 10.5
    for i, (k, v) in enumerate(rows):
        y = y0 + TITLE_H - 13 - i * row_h
        _text(g, x0 + 6, y, k, 6.5, color=colors.HexColor("#555555"))
        _text(g, x0 + 70, y, v[:62], 7.5, bold=(k == "Part"))
    _text(g, x0 + 6, y0 + 15, TOLERANCE_NOTE.upper(), 7.5, bold=True)
    _text(g, x0 + 6, y0 + 5, "Unverified design values — confirm before tooling.  Bathsheva London / Product Workbench",
          6.0, color=WARN)


def _wrap(text: str, width: int = 88) -> list[str]:
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width and line:
            out.append(line)
            line = "   " + word
        else:
            line = f"{line} {word}".strip() if not line.startswith("   ") or line.strip() else line + word
    if line:
        out.append(line)
    return out


def _notes(g: Group, lines: list[tuple[str, Any]]):
    x0 = PAGE_W - MARGIN - TITLE_W
    y = MARGIN + TITLE_H + 12
    for text, color in reversed(lines):
        for part in reversed(_wrap(text)):
            _text(g, x0 + 2, y, part, 7.0, color=color)
            y += 9
    _text(g, x0 + 2, y + 2, "NOTES", 7.5, bold=True)


def _section_view(g: Group, outline: list[tuple[float, float]], cx: float, y0: float, k: float):
    """Full section: right half and its mirror, filled, with a centreline."""
    right = [c for r, z in outline for c in (cx + r * k, y0 + z * k)]
    left = [c for r, z in outline for c in (cx - r * k, y0 + z * k)]
    for pts in (right, left):
        g.add(Polygon(pts, fillColor=SECTION_FILL, strokeColor=INK, strokeWidth=0.7))


# ---------------------------------------------------------------------------
# Geometry for the views (from the CAD solids)
# ---------------------------------------------------------------------------


def _local(cad_key: str, params: dict[str, Any]):
    """The part as drawn: axis vertical, centred on the axis, bottom at z = 0."""
    solid = faro.build(params)[cad_key]
    if cad_key == "knob":
        solid = Rot(-90, 0, 0) * solid  # the knob's axis points out of the front (-Y)
    bb = solid.bounding_box()
    cx = (bb.min.X + bb.max.X) / 2 if cad_key in ("knob", "nameplate") else 0.0
    cy = (bb.min.Y + bb.max.Y) / 2 if cad_key in ("knob",) else 0.0
    return Pos(-cx, -cy, -bb.min.Z) * solid


def _wires_xy(face, plane: str, n: int = 48) -> list[list[tuple[float, float]]]:
    """Outer and inner wires of a planar face as point lists (x, z) for XZ or (x, y) for XY."""
    out = []
    for wire in [face.outer_wire(), *face.inner_wires()]:
        pts = []
        for e in wire.edges():
            k = 1 if e.geom_type.name == "LINE" else n
            for i in range(k):
                q = e.position_at(i / k)
                pts.append((q.X, q.Z) if plane == "XZ" else (q.X, q.Y))
        out.append(pts)
    return out


def section_faces(cad_key: str, params: dict[str, Any]) -> list[list[list[tuple[float, float]]]]:
    """Faces of the cut through the part's axis (XZ plane): [[outer, *holes], ...] in mm."""
    solid = _local(cad_key, params)
    cut = solid & (Plane.XZ * Rectangle(4000, 4000))
    if cut is None or not cut.faces():  # nothing on the XZ plane: cut through YZ instead
        cut = Rot(0, 0, 90) * solid & (Plane.XZ * Rectangle(4000, 4000))
    return [_wires_xy(f, "XZ") for f in cut.faces()] if cut is not None else []


def plan_faces(cad_key: str, params: dict[str, Any], z: float | None = None) -> list[list[list[tuple[float, float]]]]:
    solid = _local(cad_key, params)
    bb = solid.bounding_box()
    zc = (bb.min.Z + bb.max.Z) / 2 if z is None else z
    cut = solid & (Plane(origin=(0, 0, zc)) * Rectangle(4000, 4000))
    return [_wires_xy(f, "XY") for f in cut.faces()]


def railing_flat_pattern(params: dict[str, Any]) -> dict[str, Any]:
    """Developed (flat) pattern of the photo-etched railing strip, in mm."""
    p = {k: float(v) for k, v in params.items()}
    r_mid = p["gallery_diameter"] / 2 - faro.RAIL_INSET - faro.RAIL_T / 2
    length = 2 * math.pi * r_mid
    h = p["railing_height"]
    n = int(p["railing_posts"])
    pitch = length / n
    z_mid = h * faro.RAIL_MID_FRAC
    windows = []
    for k in range(n):
        x0 = k * pitch + faro.RAIL_POST_W / 2
        x1 = (k + 1) * pitch - faro.RAIL_POST_W / 2
        windows.append((x0, faro.RAIL_FOOT_H, x1, z_mid - faro.RAIL_BAR_H / 2))
        windows.append((x0, z_mid + faro.RAIL_BAR_H / 2, x1, h - faro.RAIL_BAR_H))
    return {"length": length, "height": h, "posts": n, "pitch": pitch, "windows": windows}


def _poly_pts(pts: list[tuple[float, float]], ox: float, oy: float, k: float) -> list[float]:
    return [c for x, y in pts for c in (ox + x * k, oy + y * k)]


def _draw_faces(g: Group, faces, ox: float, oy: float, k: float, fill=SECTION_FILL):
    for wires in faces:
        outer, holes = wires[0], wires[1:]
        if len(outer) >= 3:
            g.add(Polygon(_poly_pts(outer, ox, oy, k), fillColor=fill, strokeColor=INK, strokeWidth=0.6))
        for hole in holes:
            if len(hole) >= 3:
                g.add(Polygon(_poly_pts(hole, ox, oy, k), fillColor=colors.white, strokeColor=INK, strokeWidth=0.5))


def _bounds(faces) -> tuple[float, float, float, float]:
    xs = [x for wires in faces for w in wires for x, _ in w] or [0.0]
    ys = [y for wires in faces for w in wires for _, y in w] or [0.0]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# Notes per part
# ---------------------------------------------------------------------------


def _part_notes(key: str, p: dict[str, float], d: dict[str, Any]) -> list[tuple[str, Any]]:
    w = p["wall_thickness"]
    n: list[tuple[str, Any]] = []
    if key in SPUN:
        n.append((f"Spun from aluminium 1050A H14 sheet, wall t = {_fmt(w)} min all over. Class A outside surface: spin lines "
                  "removed before lacquer; trimmed edges deburred.", INK))
    if key == "base":
        n.append((f"Top edge radius R{_fmt(p['base_top_round'])}. Centre hole Ø{_fmt(faro.WIRE_HOLE_D)}. "
                  f"{faro.BAND_SCREWS} × Ø{_fmt(faro.BAND_SCREW_CLEAR)} holes on PCD Ø{_fmt(d['band_screw_pcd'])} (under the band).", INK))
        n.append((f"Rear (+Y): USB-C slot {_fmt(faro.USBC_W)} × {_fmt(faro.USBC_H)}, centre {_fmt(faro.USBC_Z)} above the underside "
                  "(laser cut after spinning).", INK))
        n.append(("Gloss black lacquer, clear-coated. Nameplate bonded on the front (-Y) after lacquer.", INK))
        n.append(("SAFETY: tip-over stability to be verified on the finished lamp with the weight plate fitted.", WARN))
    elif key == "tower":
        n.append((f"Spun cone Ø{_fmt(p['tower_bottom_diameter'])} → Ø{_fmt(p['tower_top_diameter'])} over {_fmt(d['tower_height'])}, "
                  "open both ends.", INK))
        wins = ", ".join(f"{_fmt(z - d['tower_bottom_z'])} @ {a:g}°" for z, a in d["windows"])
        if d["windows"]:
            n.append((f"{len(d['windows'])} arched windows {_fmt(p['window_width'])} × {_fmt(p['window_height'])} (round top), laser-cut "
                      f"after spinning; centre heights above the tower foot @ angle from the front, turning to the right: {wins}.", INK))
        n.append((f"Dimmer hole Ø{_fmt(faro.POT_HOLE_D)} on the front, {_fmt(p['knob_z'] - d['tower_bottom_z'])} above the foot.", INK))
        n.append((f"Two-tone lacquer: red from the foot to {_fmt(p['red_section_height'])} (masked line, crisp and level), cream "
                  "above; clear-coated. Mask the window edges.", INK))
    elif key == "band_cream":
        n.append((f"Turned from aluminium 6061 thick tube or a ring blank (near-net stock). {faro.BAND_SCREWS} × M3 tapped blind holes from below on PCD "
                  f"Ø{_fmt(d['band_screw_pcd'])}, 5 deep. Spigot locates the tower (bonded).", INK))
        n.append(("Cream lacquer, clear-coated; top edge R1.", INK))
    elif key == "diffuser":
        n.append((f"Opal (acid-etched) borosilicate 3.3 tube, OD Ø{_fmt(d['diffuser_od'])}, wall {_fmt(faro.DIFFUSER_WALL)}, length "
                  f"{_fmt(d['diffuser_length'])} (window zone only). Nearest stock OD may be proposed. Stands on a spider on the "
                  "tower-light spine; a silicone ring centres the top in the tower.", INK))
        n.append(("Both ends ground. Even diffusion: no clear patches visible through the windows.", INK))
        n.append(("SAFETY: glass edge finishing and retention to be verified.", WARN))
    elif key == "gallery":
        n.append((f"Spun brass (CZ108) shell t = {_fmt(faro.GALLERY_SHEET)}: flat top with a Ø{_fmt(faro.LEDGE_BORE)} bore (the LED "
                  f"rests on it), outer skirt, open underneath; top outer edge R{_fmt(faro.GALLERY_ROUND)}.", INK))
        n.append(("Turned brass locating ring (from tube) soldered under the top: sits on the tower top, spigot fits inside it "
                  "(bonded).", INK))
        n.append(("Tumble-polished, clear lacquer. The railing is soldered or bonded on the top face.", INK))
    elif key == "railing":
        fp = railing_flat_pattern(p)
        n.append((f"Photo-etched brass sheet t = {_fmt(faro.RAIL_T)}. Flat pattern {_fmt(fp['length'])} × {_fmt(fp['height'])}: "
                  f"{fp['posts']} posts {_fmt(faro.RAIL_POST_W)} wide at {_fmt(fp['pitch'])} pitch, top and mid rails "
                  f"{_fmt(faro.RAIL_BAR_H)}, foot band {_fmt(faro.RAIL_FOOT_H)}.", INK))
        n.append(("Rolled to a ring, seam soldered on a post, then soldered to the gallery. Tumble-polished, clear lacquer.", INK))
        n.append(("Alternatives to quote: soldered brass wire (Ø1.6 posts and rails) or lost-wax cast brass.", INK))
    elif key == "lantern_frame":
        n.append((f"Brass: bottom ring and top band turned from tube; {int(p['lantern_mullions'])} mullion bars {_fmt(faro.MULLION_W)} × "
                  f"{_fmt(faro.MULLION_DEPTH)} soldered or brazed between them (a panel faces the front).", INK))
        n.append((f"Top band carries the bayonet: lip {_fmt(faro.LIP_H)} high, {faro.LOCK_LUGS} entry slots "
                  f"{_fmt(faro.LOCK_LUG_W + 2 * faro.FIT_CLEAR)} wide, and a stop {abs(faro.LOCK_TURN_DEG):g}° clockwise "
                  "(seen from above) from each slot.", INK))
        n.append(("Lowered over the glass and bonded to the gallery. Tumble-polished, clear lacquer.", INK))
    elif key == "lantern_glass":
        n.append((f"Frosted (acid-etched inside) borosilicate 3.3 tube, OD Ø{_fmt(d['glass_od'])}, wall "
                  f"{_fmt(p['glass_wall_thickness'])}, length {_fmt(d['glass_height'])}. Nearest stock size may be proposed.", INK))
        n.append(("Both ends ground or fire-polished; no chips, bubbles or scratches visible at 50 cm.", INK))
        n.append(("SAFETY: glass breakage, edge finishing and retention to be verified.", WARN))
    elif key == "cap":
        n.append((f"Rim Ø{_fmt(p['cap_rim_diameter'])} × {_fmt(p['cap_rim_height'])}, dome Ø{_fmt(p['cap_dome_diameter'])}, "
                  f"neck for the finial spun in (verify with the spinner; fallback a separate turned collar). Centre hole "
                  f"Ø{_fmt(faro.FINIAL_STUD_D + 0.5)}.", INK))
        n.append(("Red lacquer, clear-coated. The brass bayonet spigot is bonded under the shoulder.", INK))
    elif key == "cap_spigot":
        n.append((f"Brass ring turned from tube, with {faro.LOCK_LUGS} lugs {_fmt(faro.LOCK_LUG_W)} × {_fmt(faro.LOCK_LUG_H)} at the foot; "
                  f"fit clearance {_fmt(faro.FIT_CLEAR)} per side in the lantern lip. Flange bonded inside the cap.", INK))
        n.append(("Hidden when fitted: natural brass, no cosmetic finish.", INK))
    elif key == "finial":
        n.append((f"Brass ball Ø{_fmt(p['finial_diameter'])}, turned from close-fitting bar, on a neck, M4 stud through the cap (nyloc nut inside).", INK))
        n.append(("Tumble-polished, clear lacquer.", INK))
    elif key == "knob":
        n.append((f"Solid brass knob (turned from close-fitting bar) Ø{_fmt(p['knob_diameter'])} × {_fmt(faro.KNOB_PROUD)}, front edge R1; D-shaft bore "
                  "and grub screw (or push-fit) to suit the chosen 9 mm pot.", INK))
        n.append(("Tumble-polished, clear lacquer. Back face clears the conical tower by 0.5 mm.", INK))
    elif key == "nameplate":
        n.append((f"Etched brass t = {_fmt(faro.NAMEPLATE_T)}, {_fmt(faro.NAMEPLATE_W)} × {_fmt(faro.NAMEPLATE_H)}, corner R1.2, "
                  f"formed to R{_fmt(p['base_diameter'] / 2)} (the base). \"FARO\" etched, filled black.", INK))
        n.append(("Bonded on the base front, centred {0} above the underside.".format(_fmt(faro.NAMEPLATE_Z)), INK))
    elif key == "weight_plate":
        n.append((f"Laser-cut mild steel S275, t = {_fmt(p['weight_plate_thickness'])}, zinc plated. Hidden; no cosmetic requirement.", INK))
        n.append((f"Battery cut-out {_fmt(faro.BATTERY[0] + 2)} × {_fmt(faro.BATTERY[1] + 2)} R3; {faro.STANDOFFS} × M2.5 tapped "
                  f"holes on R{_fmt(faro.STANDOFF_R)} for the bottom-plate standoffs; {faro.BAND_SCREWS} × Ø{_fmt(faro.BAND_SCREW_CLEAR)} "
                  f"counterbored for M3 socket heads.", INK))
    elif key == "base_plate":
        n.append((f"Laser-cut aluminium 5052, t = {_fmt(faro.BOTTOM_PLATE_T)}, black lacquer. {faro.STANDOFFS} × M2.5 countersunk "
                  f"holes on R{_fmt(faro.STANDOFF_R)}; {faro.MAGNETS} × Ø{_fmt(faro.MAGNET_D)} magnet holes between them.", INK))
        n.append(("User-removable (battery replacement): screws must be standard hex socket.", INK))
    return n


# ---------------------------------------------------------------------------
# Sheet
# ---------------------------------------------------------------------------


def part_drawing(params: dict[str, Any], sheet: PartSheet) -> Drawing:
    """A4 landscape quotation drawing for one made-to-drawing part."""
    p = {k: float(v) for k, v in params.items()}
    d = faro.derived(p)
    key = sheet.cad_key
    drawing = Drawing(PAGE_W, PAGE_H)
    g = Group()

    if key == "railing":
        fp = railing_flat_pattern(p)
        main = [[[(0, 0), (fp["length"], 0), (fp["length"], fp["height"]), (0, fp["height"])]]]
        main_title = "FLAT PATTERN (developed, as etched)"
    elif key == "nameplate":
        w_, h_, r_ = faro.NAMEPLATE_W, faro.NAMEPLATE_H, 1.2
        pts = []
        for cx, cy, a0 in ((w_ - r_, r_, -90), (w_ - r_, h_ - r_, 0), (r_, h_ - r_, 90), (r_, r_, 180)):
            pts += [(cx + r_ * math.cos(math.radians(a0 + 90 * i / 6)), cy + r_ * math.sin(math.radians(a0 + 90 * i / 6)))
                    for i in range(7)]
        main = [[pts]]
        main_title = "FRONT VIEW (developed, before forming)"
    else:
        main = section_faces(key, params)
        main_title = "SECTION A–A (through the axis)"
    x0, y0, x1, y1 = _bounds(main)
    W, H = x1 - x0, y1 - y0
    view_w = PAGE_W - 2 * MARGIN - TITLE_W - 80
    view_h = PAGE_H - 2 * MARGIN - 110
    n = _choose_scale(W + 6, H + 6, view_w, view_h)
    k = PT_PER_MM / n
    _frame_and_title(g, sheet, n)

    ox = MARGIN + 50 - x0 * k + max((view_w - W * k) / 2, 0)
    oy = MARGIN + 80 - y0 * k + max((view_h - H * k) / 2 - 20, 0)
    _draw_faces(g, main, ox, oy, k)
    if key == "nameplate":
        _text(g, ox + faro.NAMEPLATE_W / 2 * k, oy + (faro.NAMEPLATE_H / 2 - 2.3) * k, "FARO", 6.5 * k, "middle", bold=True)
    if key == "railing":
        for (a, b, c, e) in fp["windows"]:
            g.add(Rect(ox + a * k, oy + b * k, (c - a) * k, (e - b) * k, fillColor=colors.white, strokeColor=INK,
                       strokeWidth=0.4))
    elif key != "nameplate":
        _centreline(g, ox, oy + y0 * k - 10, oy + y1 * k + 10)
    _text(g, ox + (x0 + x1) / 2 * k, oy + y0 * k - 58, main_title, 7.5, "middle", bold=True)

    # Overall dimensions.
    lbl_w = (f"Ø{_fmt(W)}" if key not in ("railing", "nameplate") else _fmt(W))
    _dim_h(g, ox + x0 * k, ox + x1 * k, oy + y1 * k, oy + y1 * k + 18, lbl_w)
    _dim_v(g, oy + y0 * k, oy + y1 * k, ox + x1 * k, ox + x1 * k + 20, _fmt(H))
    if key in SPUN:
        _leader(g, ox + (x1 - p["wall_thickness"] / 2) * k, oy + (y0 + H * 0.35) * k, ox + x1 * k + 36,
                oy + (y0 + H * 0.35) * k, f"wall t = {_fmt(p['wall_thickness'])} (min)")

    if key in PLAN_PARTS:
        plan_z = {"base": H - 0.5, "lantern_frame": H - faro.LIP_H / 2, "cap_spigot": faro.LOCK_LUG_H / 2}.get(key)
        plan = plan_faces(key, params, z=plan_z)
        px0, py0, px1, py1 = _bounds(plan)
        kp = min(k, (TITLE_W - 60) / max(px1 - px0, 1), (PAGE_H - 2 * MARGIN - TITLE_H - 170) / max(py1 - py0, 1))
        pcx = PAGE_W - MARGIN - TITLE_W / 2
        pcy = PAGE_H - MARGIN - 40 - (py1 - py0) / 2 * kp
        _draw_faces(g, plan, pcx, pcy, kp, fill=colors.HexColor("#eef0f3"))
        where = {"base": ", top face", "lantern_frame": ", cut through the bayonet lip",
                 "cap_spigot": ", cut through the lugs"}.get(key, "")
        _text(g, pcx, pcy - (py1 - py0) / 2 * kp - 14, f"PLAN VIEW (from above{where})", 7.5, "middle", bold=True)
        _text(g, pcx, pcy + (py1 - py0) / 2 * kp + 6, "front (-Y) at the bottom", 6.5, "middle", DIM)

    notes = _part_notes(key, p, d)
    for u in sheet.unverified:
        notes.append((f"UNVERIFIED: {u}", UNV))
    for sft in sheet.safety:
        kw = " ".join(sft.lower().split()[:2])
        if not any(kw in t.lower() for t, _ in notes):
            notes.append((f"SAFETY: {sft}", WARN))
    notes.append(("All dimensions in mm. " + TOLERANCE_NOTE + ".", INK))
    _notes(g, notes)
    drawing.add(g)
    return drawing


def to_svg(drawing: Drawing) -> str:
    return renderSVG.drawToString(drawing)


def to_pdf(drawing: Drawing) -> bytes:
    return renderPDF.drawToString(drawing)
