"""2D quotation drawings (SVG and PDF) from the parametric section profiles.

Pure: takes CAD parameters plus part metadata, returns a reportlab Drawing that is
rendered to both SVG and PDF, so the two formats always match. No database access.

Each sheet is A4 landscape with a full section view (both halves sectioned), a plan
view for parts with holes, overall dimensions, wall thickness, hole positions, notes
and a title block that says the dimensions are for quotation only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Polygon, Rect, String
from reportlab.lib import colors

from app.cad import faro

PT_PER_MM = 72 / 25.4
PAGE_W, PAGE_H = 842.0, 595.0  # A4 landscape, points
MARGIN = 18.0
TITLE_W, TITLE_H = 330.0, 128.0
STANDARD_SCALES = [1, 1.5, 2, 2.5, 3, 4, 5, 10]
TOLERANCE_NOTE = "Dimensions for quotation, tolerances to be agreed"
INK = colors.HexColor("#1a1a1a")
DIM = colors.HexColor("#1f4e9c")
SECTION_FILL = colors.HexColor("#d9dde3")
WARN = colors.HexColor("#b3261e")

# Parts the drawings cover (made to drawing); bought-in parts are specified by datasheet.
DRAWN_PARTS = ["base", "main_body", "band", "lantern", "top_cap", "weight_plate"]


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


def _section_view(g: Group, outline: list[tuple[float, float]], cx: float, y0: float, k: float):
    """Full section: right half and its mirror, filled, with a centreline."""
    right = [c for r, z in outline for c in (cx + r * k, y0 + z * k)]
    left = [c for r, z in outline for c in (cx - r * k, y0 + z * k)]
    for pts in (right, left):
        g.add(Polygon(pts, fillColor=SECTION_FILL, strokeColor=INK, strokeWidth=0.7))


def _plan_view(g: Group, sheet_key: str, p: dict[str, float], cx: float, cy: float, k: float):
    """Plan (top) view with holes, for the base and the weight plate."""
    d = faro.derived(p)
    outer = (p["base_diameter"] if sheet_key == "base" else p["weight_plate_diameter"]) / 2
    g.add(Circle(cx, cy, outer * k, fillColor=None, strokeColor=INK, strokeWidth=0.7))
    bore = d["central_hole_diameter"] / 2
    g.add(Circle(cx, cy, bore * k, fillColor=None, strokeColor=INK, strokeWidth=0.6))
    n = int(p["mounting_hole_count"])
    pcd = p["mounting_hole_pcd"] / 2
    hole = (p["mounting_hole_diameter"] if sheet_key == "base" else faro.SCREW_CLEARANCE) / 2
    g.add(Circle(cx, cy, pcd * k, fillColor=None, strokeColor=DIM, strokeWidth=0.3, strokeDashArray=[6, 2, 1, 2]))
    for i in range(n):
        a = 2 * math.pi * i / n
        g.add(Circle(cx + pcd * k * math.cos(a), cy + pcd * k * math.sin(a), hole * k, fillColor=None, strokeColor=INK,
                     strokeWidth=0.6))
    g.add(Line(cx - outer * k - 6, cy, cx + outer * k + 6, cy, strokeColor=INK, strokeWidth=0.3, strokeDashArray=[8, 2, 1.5, 2]))
    g.add(Line(cx, cy - outer * k - 6, cx, cy + outer * k + 6, strokeColor=INK, strokeWidth=0.3, strokeDashArray=[8, 2, 1.5, 2]))
    lx = cx - outer * k
    _leader(g, cx + pcd * k, cy + hole * k, lx, cy + outer * k + 26,
            f"{n} × Ø{_fmt(2 * hole)} {'rivet-nut holes' if sheet_key == 'base' else 'screw clearance holes'} on PCD Ø{_fmt(2 * pcd)}, "
            "equally spaced")
    _leader(g, cx, cy + bore * k, lx, cy + outer * k + 14, f"Centre bore Ø{_fmt(2 * bore)} for the M10x1 lamp tube")
    if sheet_key == "base":
        _text(g, cx + outer * k + 8, cy - 2.5, "0° cable", 6.5, color=DIM)
        if p["dimmer_hole_diameter"] > 0:
            _text(g, cx - outer * k - 8, cy - 2.5, "180° dimmer", 6.5, "end", DIM)
    _text(g, cx, cy - outer * k - 16, "PLAN VIEW (from above)", 7.5, "middle", bold=True)


def part_drawing(params: dict[str, Any], sheet: PartSheet) -> Drawing:
    """A4 landscape quotation drawing for one made-to-drawing part."""
    p = {k: float(v) for k, v in params.items()}
    d = faro.derived(p)
    prof = faro.section_profiles(p)[sheet.cad_key]
    outline, H, D = prof["outline"], prof["height"], prof["diameter"]
    has_plan = sheet.cad_key in ("base", "weight_plate")

    drawing = Drawing(PAGE_W, PAGE_H)
    g = Group()
    view_w = PAGE_W - 2 * MARGIN - TITLE_W - 70
    view_h = PAGE_H - 2 * MARGIN - 90
    n = _choose_scale(D + 40, H + 30, view_w, view_h)
    plan_h = PAGE_H - 2 * MARGIN - TITLE_H - 120  # space above the notes, right-hand column
    if has_plan:
        n = max(n, _choose_scale(D, D, TITLE_W - 40, plan_h - 60))
    k = PT_PER_MM / n
    _frame_and_title(g, sheet, n)

    # Section view, placed in the left part of the sheet.
    cx = MARGIN + 50 + D / 2 * k
    y0 = MARGIN + 80 + max((view_h - H * k) / 2 - 30, 0)
    _section_view(g, outline, cx, y0, k)
    _centreline(g, cx, y0 - 10, y0 + H * k + 10)
    _text(g, cx, y0 - 58, "SECTION A–A (through the axis)", 7.5, "middle", bold=True)

    top_y = y0 + H * k
    w = p["wall_thickness"]
    notes: list[tuple[str, Any]] = []
    unv = colors.HexColor("#8a5a00")
    if sheet.cad_key in ("base", "top_cap"):
        _dim_h(g, cx - D / 2 * k, cx + D / 2 * k, top_y, top_y + 18, f"Ø{_fmt(D)}")
        _dim_v(g, y0, top_y, cx + D / 2 * k, cx + D / 2 * k + 18, _fmt(H))
        bore = d["central_hole_diameter"]
        _leader(g, cx + bore / 2 * k, top_y, cx + D / 4 * k, top_y + 34, f"Ø{_fmt(bore)} centre bore")
        _leader(g, cx + (D / 2 - w / 2) * k, y0 + H * k * 0.3, cx + D / 2 * k + 30, y0 + H * k * 0.3,
                f"wall t = {_fmt(w)} (min, all over)")
        notes.append(("Spun from aluminium sheet; spinning marks removed before finishing (class A outside).", INK))
        if sheet.cad_key == "base":
            notes.append((f"Side holes: cable Ø{_fmt(p['cable_hole_diameter'])} at 0°, dimmer Ø{_fmt(p['dimmer_hole_diameter'])} "
                          f"at 180°, centres {_fmt(d['cable_z'])} above the underside.", INK))
            notes.append(("Rivet nuts M4 fitted from inside; heads hidden under the body foot.", INK))
            notes.append(("SAFETY: tip-over stability to be verified on the finished lamp with the weight plate fitted.", WARN))
        else:
            notes.append(("Inside dome seats the upper lantern gasket; cap nut seats on the flat top.", INK))
    elif sheet.cad_key == "main_body":
        r_bot, r_top = p["body_diameter"] / 2, p["body_top_diameter"] / 2
        _dim_h(g, cx - r_bot * k, cx + r_bot * k, y0, y0 - 40, f"Ø{_fmt(2 * r_bot)}")
        _dim_h(g, cx - r_top * k, cx + r_top * k, top_y, top_y + 18, f"Ø{_fmt(2 * r_top)}")
        _dim_v(g, y0, top_y, cx + r_bot * k, cx + r_bot * k + 24, _fmt(H))
        z1 = prof["step_z"]
        _dim_v(g, y0, y0 + z1 * k, cx - r_bot * k, cx - r_bot * k - 24, _fmt(z1))
        r_z1 = r_bot + (r_top + p["step_depth"] - r_bot) * z1 / H
        _leader(g, cx + (r_z1 - p["step_depth"] / 2) * k, y0 + z1 * k, cx + r_bot * k + 40, y0 + z1 * k + 30,
                f"locating step {_fmt(p['step_depth'])} deep (band seat)")
        _leader(g, cx + (r_bot - w / 2) * k, y0 + 12, cx + r_bot * k + 40, y0 + 12, f"wall t = {_fmt(w)} (min)")
        notes.append(("Spun tapered shell, open both ends. Class A outside surface; no spinning marks under lacquer.", INK))
        notes.append(("Step must be square and concentric so the band ring sits level with an even shadow line.", INK))
    elif sheet.cad_key == "band":
        ri = d["band_inner_diameter"] / 2
        ro = d["band_outer_diameter"] / 2
        _dim_h(g, cx - ro * k, cx + ro * k, top_y, top_y + 18, f"OD Ø{_fmt(2 * ro)}")
        _dim_h(g, cx - ri * k, cx + ri * k, y0, y0 - 18, f"ID Ø{_fmt(2 * ri)}")
        _dim_v(g, y0, top_y, cx + ro * k, cx + ro * k + 18, _fmt(H))
        notes.append((f"Cut from stock aluminium tube (6063); wall {_fmt(p['band_wall_thickness'])}. Nearest stock size may be "
                      "proposed.", INK))
        notes.append(("Faces square, edges with a small even chamfer; class A outside surface.", INK))
        notes.append(("Slides down over the body from the top and is bonded on the body step.", INK))
    elif sheet.cad_key == "lantern":
        rl = p["lantern_diameter"] / 2
        _dim_h(g, cx - rl * k, cx + rl * k, top_y, top_y + 18, f"OD Ø{_fmt(2 * rl)}")
        _dim_v(g, y0, top_y, cx + rl * k, cx + rl * k + 18, _fmt(H))
        _leader(g, cx + (rl - p["lantern_wall_thickness"] / 2) * k, y0 + H * k * 0.5, cx + rl * k + 40, y0 + H * k * 0.6,
                f"wall t = {_fmt(p['lantern_wall_thickness'])}")
        notes.append(("Borosilicate glass tube (e.g. 3.3 grade), cut to length; both ends ground or fire-polished.", INK))
        notes.append((f"Visible length {_fmt(p['lantern_height'])}; the rest sits inside the cap and on the gasket.", INK))
        notes.append(("No chips, bubbles or scratches visible at 50 cm. Clear, or acid-etched inside if frosted.", INK))
        notes.append(("SAFETY: glass breakage, edge finishing and gasket retention to be verified.", WARN))
    elif sheet.cad_key == "weight_plate":
        _dim_h(g, cx - D / 2 * k, cx + D / 2 * k, top_y, top_y + 18, f"Ø{_fmt(D)}")
        _dim_v(g, y0, top_y, cx + D / 2 * k, cx + D / 2 * k + 18, f"t = {_fmt(H)}")
        notes.append(("Laser-cut mild steel S275, zinc plated. Hidden inside the base; no cosmetic requirement.", INK))
        notes.append(("Clamped by the lamp nut and screwed to the rivet nuts: it must not rattle or turn.", INK))
        mass = math.pi * ((D / 2) ** 2 - (d["central_hole_diameter"] / 2) ** 2) * H / 1000 * 7.85 / 1000
        notes.append((f"Approx. mass {mass:.2f} kg (sets the lamp's stability and feel).", INK))
        notes.append(("SAFETY: stability-relevant part; tip-over test on the finished lamp.", WARN))

    if has_plan:
        pcx = PAGE_W - MARGIN - TITLE_W / 2
        pcy = PAGE_H - MARGIN - 50 - D / 2 * k
        _plan_view(g, sheet.cad_key, p, pcx, pcy, k)

    for u in sheet.unverified:
        notes.append((f"UNVERIFIED: {u}", unv))
    for s in sheet.safety:
        key = " ".join(s.lower().split()[:2])
        if not any(key in t.lower() for t, _ in notes):
            notes.append((f"SAFETY: {s}", WARN))
    notes.append(("All dimensions in mm. " + TOLERANCE_NOTE + ".", INK))
    _notes(g, notes)
    drawing.add(g)
    return drawing


def to_svg(drawing: Drawing) -> str:
    return renderSVG.drawToString(drawing)


def to_pdf(drawing: Drawing) -> bytes:
    return renderPDF.drawToString(drawing)
