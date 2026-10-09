"""2D quotation drawings for Atelier (SVG and PDF), from the same solids that are exported to STEP.

Uses the sheet, dimensioning and section helpers of `drawings` (Faro's drawings), with Atelier's own views:
sections through the axis for the turned and cast round parts, a section through the front-back plane for
the body and the bezels, the fin's mid-plane section and plan, and projected front views of the honeycomb
grilles drawn from the same hole layout the CAD cuts. Pure: CAD parameters plus part metadata in, a
reportlab Drawing out. No database access.
"""

from __future__ import annotations

import math
from typing import Any

from build123d import Plane, Pos, Rectangle, Rot
from reportlab.graphics.shapes import Drawing, Group
from reportlab.lib import colors

from app.cad import atelier
from app.factory import drawings as dr
from app.factory.drawings import (DIM, ENGRAVED_FILL, INK, MARGIN, PAGE_H, PAGE_W, PT_PER_MM, SECTION_FILL, TITLE_H,
                                  TITLE_W, UNV, WARN, PartSheet, _bounds, _centreline, _choose_scale, _dim_h, _dim_v,
                                  _draw_faces, _fmt, _frame_and_title, _notes, _scale_label, _text, _wires_xy)

# Made-to-drawing parts, in drawing order (bought-in parts are specified by datasheet).
DRAWN_PARTS = ["body", "nose_cone", "fin", "collar", "foot", "knob", "bezel", "grille", "rear_bezel", "rear_grille",
               "ballast", "chassis", "fin_pad"]
# The process each drawing's notes are written for (the Factory Pack checks the part's process against it).
NOTE_PROCESS = {
    "body": "injection_moulding", "nose_cone": "cnc_machining", "fin": "zinc_die_casting", "collar": "zinc_die_casting",
    "foot": "zinc_die_casting", "knob": "cnc_turning_near_net", "bezel": "cnc_machining", "rear_bezel": "cnc_machining",
    "grille": "photo_etching_stainless", "rear_grille": "photo_etching_stainless",
}
GOLD_PVD = ("Gold PVD, fine brushed satin, one matched tone across all parts (ΔE ≤ 1.5 to the signed master sample); "
            "base layer as the coater specifies (copper-nickel on zinc, nickel on brass). Grain horizontal as fitted.")


def _turn(cad_key: str, solid):
    """The part as drawn: axis or main plane where the views expect it, centred, bottom at z = 0."""
    if cad_key == "knob":
        solid = Rot(-90, 0, 0) * solid  # the knob's axis points out of the front (-Y): stand it up
    elif cad_key in ("fin", "fin_pad"):
        solid = Rot(0, 0, 90 - atelier.proto.FIN_ANGLE_OFFSET_DEG) * solid  # the first fin points along +X
    elif cad_key in ("body", "bezel", "rear_bezel", "chassis"):
        solid = Rot(0, 0, 90) * solid  # front-back plane onto XZ (front, -Y, to the left)
    bb = solid.bounding_box()
    cx = (bb.min.X + bb.max.X) / 2 if cad_key in ("knob", "fin_pad", "bezel", "rear_bezel") else 0.0
    cy = (bb.min.Y + bb.max.Y) / 2 if cad_key in ("knob", "bezel", "rear_bezel") else 0.0
    return Pos(-cx, -cy, -bb.min.Z) * solid


def _section(solid) -> list:
    cut = solid & (Plane.XZ * Rectangle(4000, 4000))
    return [_wires_xy(f, "XZ") for f in cut.faces()] if cut is not None else []


def _plan(solid, z: float) -> list:
    cut = solid & (Plane(origin=(0, 0, z)) * Rectangle(4000, 4000))
    return [_wires_xy(f, "XY") for f in cut.faces()] if cut is not None else []


def _hexes(a: float, b: float) -> list:
    """The honeycomb the CAD cuts (atelier_geometry._cut_honeycomb), as faces in the front view (x, z)."""
    pitch = atelier.HEX_HOLE + atelier.HEX_WEB
    dz = pitch * math.sqrt(3) / 2
    hex_r = atelier.HEX_HOLE / math.sqrt(3)
    m_ = atelier.HEX_WEB + hex_r
    la, lb = a - m_, b - m_
    out, j, z = [], 0, -lb
    while z <= lb + 1e-6:
        x = -la - (pitch / 2 if j % 2 else 0.0)
        while x <= la + 1e-6:
            if (x / la) ** 2 + (z / lb) ** 2 <= 1.0:
                out.append([[(x + hex_r * math.cos(math.radians(90 + 60 * k)), z + hex_r * math.sin(math.radians(90 + 60 * k)))
                             for k in range(6)]])
            x += pitch
        z += dz
        j += 1
    return out


def _ellipse(a: float, b: float, n: int = 120) -> list:
    return [(a * math.cos(2 * math.pi * i / n), b * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _part_notes(key: str, p: dict[str, float], m: atelier.Model) -> list[tuple[str, Any]]:
    I = m.info
    n: list[tuple[str, Any]] = []
    if key == "body":
        n += [(f"PC/ABS, injection moulded, wall {_fmt(p['wall_thickness'])} (Technical Specification). The belly "
               f"(Ø{_fmt(p['body_max_diameter'])}) is wider than both openings: propose a collapsible core or two welded "
               "halves, and where the internal seats go.", INK),
              ("Oxblood red #8A1C15: primer, colour, two clear coats, cut and polished to ≥ 90 GU; ΔE ≤ 1.0 to the signed "
               "master sample. Class A surface: no sink, weld lines or gate marks on the outside.", INK),
              (f"Front: grille recess and Ø{_fmt(I['sound_opening_dia'])} sound opening; knob hole and Ø3 LED hole below "
               "it. Rear: radiator opening with its recess. Six vertical slots for the M4 fin screws.", INK),
              ("Seams to the nose cone and collar 0.3 ±0.1 mm, flush within 0.1 mm.", INK)]
    elif key == "nose_cone":
        n += [("6061-T6, CNC turned and hollowed (spec). Spigot with an O-ring groove; bayonet with a hidden detent to "
               "be detailed with the moulder (not shown).", INK), (GOLD_PVD, INK)]
    elif key == "fin":
        n += [("Zamak 5 die-cast, hollow, 3 mm wall, open towards the body; two cast bosses tapped M4 for the fixing "
               "screws. Draft about 0.5° outside / 1° inside. Vacuum-assisted casting; no porosity on cosmetic faces.", INK),
              ("Quantity 3 per speaker (one tool).", INK), (GOLD_PVD, INK),
              ("A 1 mm TPU pad is bonded under the tip.", INK)]
    elif key == "collar":
        n += [("Zamak die-cast, machined at the USB-C port face and the screw seats. Sealed (IP67) USB-C receptacle "
               "pocket at 120° facing 45° down; wire channel to the battery bay.", INK),
              (f"Underside: three M2.5 countersunk holes on Ø{_fmt(atelier.COLLAR_SCREW_PCD)} and the M4 stud hole, "
               "all under the foot.", INK),
              (f"\"ATELIER\" laser-etched {atelier.LETTERING_DEPTH:g} deep, tone-on-tone, round the foot on the "
               f"underside (Cormorant Garamond SemiBold, {atelier.LETTERING_CAP:g} cap height); artwork/A-01_collar_lettering.svg / .dxf. "
               "Etch before PVD.", INK), (GOLD_PVD, INK)]
    elif key == "foot":
        n += [("Zamak die-cast, machined; tapped M4 at the centre of the top face: screws onto the collar's stud by hand "
               "and hides the collar screws.", INK), (GOLD_PVD, INK)]
    elif key == "knob":
        n += [(f"Solid brass C360, CNC turned, Ø{_fmt(p['knob_diameter'])}. Fine straight knurl DIN 82 RAA 0.5 on the edge "
               "and a smooth R1 front edge. The Bathsheva emblem engraved 0.2 deep in the face (artwork/ logo files), "
               "tone-on-tone; knurl and engraving cut before PVD, so the grooves are gold too.", INK),
              ("Hidden boss on the back; blind bore for the 6 mm encoder shaft. Gap to the body 0.3 ±0.05; wobble ≤ 0.1.", INK),
              (GOLD_PVD, INK)]
    elif key in ("bezel", "rear_bezel"):
        n += [("6061-T6, CNC machined to follow the body's double curve, diamond-cut chamfer on the outer edge. The "
               "grille is bonded to it and the pair is fixed from inside (no visible fasteners).", INK), (GOLD_PVD, INK)]
    elif key in ("grille", "rear_grille"):
        n += [(f"Stainless 304, {_fmt(p['grille_thickness'])} sheet, photo-etched: {_fmt(atelier.HEX_HOLE)} mm hexagons "
               f"(across flats), {_fmt(atelier.HEX_WEB)} mm webs, solid border; then formed to the body's double curve "
               "(the projected view shows the hole layout).", INK),
              ("Black acoustic fabric behind it. Bonded to its bezel.", INK), (GOLD_PVD, INK)]
    elif key == "ballast":
        n += [("Mild steel, zinc plated: sawn bar with a milled pocket for the battery and a slot for the USB-C wires; "
               "two M2.5 tapped holes in the bottom face for the tray plate. Hidden.", INK)]
    elif key == "chassis":
        n += [("Mild steel 1.2 mm, zinc plated: three fin brackets, the board spine and the 3 mm battery tray plate "
               "(three M2.5 tapped holes for the collar, two countersunk holes to the ballast cup). Laser cut and bent. "
               "Hidden.", INK)]
    elif key == "fin_pad":
        n += [("TPU, 1 mm, black, adhesive-backed, die-cut. Quantity 3 per speaker. Hidden under the fin tips.", INK)]
    return n


def part_drawing(params: dict[str, Any], sheet: PartSheet) -> Drawing:
    """A4 landscape quotation drawing for one Atelier made-to-drawing part."""
    p = {k: float(v) for k, v in params.items()}
    m = atelier.model(params)
    key = sheet.cad_key
    I = m.info
    solid = _turn(key, m.parts[key])
    drawing = Drawing(PAGE_W, PAGE_H)
    g = Group()

    grille_ab = None
    if key == "grille":
        grille_ab = (I["grille_front_width"] / 2 - 0.1, I["grille_dia"] / 2 - 0.1)
    elif key == "rear_grille":
        cw, chh = I["rear_cover_size"]
        grille_ab = (cw / 2 - 0.1, chh / 2 - 0.1)
    if grille_ab is not None:
        a, b = grille_ab
        main = [[_ellipse(a, b)]]
        main_title = "FRONT VIEW (projected; formed to the body after etching)"
    elif key == "fin_pad":
        bb = solid.bounding_box()
        main = _plan(solid, bb.max.Z / 2)
        main_title = "PLAN VIEW"
    else:
        main = _section(solid)
        main_title = {"body": "SECTION A–A (front–back, through the axis; front to the left)",
                      "fin": "SECTION A–A (through the fin's mid-plane; body side to the left)",
                      "bezel": "SECTION A–A (vertical, through the centre)",
                      "rear_bezel": "SECTION A–A (vertical, through the centre)",
                      "chassis": "SECTION A–A (front–back, through the axis)"}.get(key, "SECTION A–A (through the axis)")
    x0, y0, x1, y1 = _bounds(main)
    W, H = x1 - x0, y1 - y0
    view_w = PAGE_W - 2 * MARGIN - TITLE_W - 80
    view_h = PAGE_H - 2 * MARGIN - 110
    n = _choose_scale(W + 6, H + 6, view_w, view_h)
    k = PT_PER_MM / n
    _frame_and_title(g, sheet, n)
    ox = MARGIN + 50 - x0 * k + max((view_w - W * k) / 2, 0)
    oy = MARGIN + 80 - y0 * k + max((view_h - H * k) / 2 - 20, 0)
    _draw_faces(g, main, ox, oy, k, fill=SECTION_FILL if grille_ab is None else colors.HexColor("#eef0f3"))
    if grille_ab is not None:
        _draw_faces(g, _hexes(*grille_ab), ox, oy, k, fill=colors.white, width=0.15)
    if key in ("nose_cone", "collar", "foot", "knob", "ballast"):
        _centreline(g, ox, oy + y0 * k - 10, oy + y1 * k + 10)
    _text(g, ox + (x0 + x1) / 2 * k, oy + y0 * k - 58, main_title, 7.5, "middle", bold=True)
    round_part = key in ("nose_cone", "collar", "foot", "knob", "ballast")
    _dim_h(g, ox + x0 * k, ox + x1 * k, oy + y1 * k, oy + y1 * k + 18, (f"Ø{_fmt(W)}" if round_part else _fmt(W)))
    _dim_v(g, oy + y0 * k, oy + y1 * k, ox + x1 * k, ox + x1 * k + 20, _fmt(H))

    # Second view at the top right: plans and the knob face.
    side = None
    if key == "collar":
        # a plan cut is seen from above: mirror it (x -> -x) so it reads as seen from below, like the etched name
        below = [[[(-x, y) for x, y in w] for w in wires] for wires in _plan(solid, 0.07)]
        side = (below, "VIEW FROM BELOW (cut 0.07 above the underside: screw holes, stud and etched name)")
    elif key in ("fin", "ballast", "chassis"):
        bb = solid.bounding_box()
        zc = {"fin": bb.max.Z * 0.3, "ballast": bb.max.Z / 2, "chassis": 3.0 / 2 + 0.01}[key]
        side = (_plan(solid, zc), f"PLAN VIEW (cut at z = {_fmt(zc)})")
    elif key in ("bezel", "rear_bezel"):
        if key == "bezel":
            a_o, b_o = I["grille_front_width"] / 2 + atelier.proto.BEZEL_WIDTH, I["bezel_od"] / 2
            a_i, b_i = I["grille_front_width"] / 2, I["grille_dia"] / 2
        else:
            (bw, bh), (cw, chh) = I["rear_bezel_size"], I["rear_cover_size"]
            a_o, b_o, a_i, b_i = bw / 2, bh / 2, cw / 2, chh / 2
        side = ([[_ellipse(a_o, b_o), _ellipse(a_i, b_i)]], "FRONT VIEW (projected)")
    if side is not None and side[0]:
        faces, title = side
        px0, py0, px1, py1 = _bounds(faces)
        kp = min(k, (TITLE_W - 60) / max(px1 - px0, 1), (PAGE_H - 2 * MARGIN - TITLE_H - 170) / max(py1 - py0, 1))
        pcx = PAGE_W - MARGIN - TITLE_W / 2 - (px0 + px1) / 2 * kp
        pcy = PAGE_H - MARGIN - 40 - py1 * kp
        _draw_faces(g, faces, pcx, pcy, kp, fill=colors.HexColor("#eef0f3"))
        _text(g, pcx + (px0 + px1) / 2 * kp, pcy + py0 * kp - 14, title, 7.0, "middle", bold=True)
    if key == "knob":
        from app.factory import logo as art

        rk = p["knob_diameter"] / 2
        kf = min((TITLE_W - 80) / (2 * rk), (PAGE_H - 2 * MARGIN - TITLE_H - 190) / (2 * rk))
        fcx = PAGE_W - MARGIN - TITLE_W / 2
        fcy = PAGE_H - MARGIN - 50 - rk * kf
        circle = lambda r: [(r * math.cos(2 * math.pi * i / 180), r * math.sin(2 * math.pi * i / 180)) for i in range(180)]  # noqa: E731
        _draw_faces(g, [[circle(rk)]], fcx, fcy, kf, fill=SECTION_FILL)
        _draw_faces(g, art.loops(art.logo_radius(p["knob_diameter"])), fcx, fcy, kf, fill=ENGRAVED_FILL,
                    hole_fill=SECTION_FILL, stroke=colors.black, width=0.1)
        _text(g, fcx, fcy - rk * kf - 14, f"FRONT VIEW: EMBLEM FACE (scale {_scale_label(1 / (kf / PT_PER_MM))})", 7.5,
              "middle", bold=True)
        _text(g, fcx, fcy + rk * kf + 6, "shaded = engraved 0.2 deep, no fill; the emblem turns with the knob", 6.5,
              "middle", DIM)

    notes = _part_notes(key, p, m)
    for u in sheet.unverified:
        notes.append((f"UNVERIFIED: {u}", UNV))
    for sft in sheet.safety:
        notes.append((f"SAFETY: {sft}", WARN))
    notes.append(("All dimensions in mm. " + dr.TOLERANCE_NOTE + ".", INK))
    _notes(g, notes)
    drawing.add(g)
    return drawing
