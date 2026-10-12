"""INTI parametric model: parameters, validation, geometry and mass.

INTI is a home Bluetooth speaker for Bathsheva London: a sculpted, head-shaped body in cream/ivory cast
Jesmonite with a smooth lacquer-like finish, and real-metal brass/gold parts (a brow-and-nose piece, two eyes,
a stepped front grille, two side dials, a top rim and a base ring). Front grille only; a rear connection
panel carries USB-C and a 3.5 mm aux input.

Design source: the concept render `docs/inti/concept.png` (front, side, rear and detail views) and the
user's design facts (Oct 2026). **The proportions come from the render; the size does not.** Every
position and size below is a fraction of the overall height H, measured in pixels on the render's front,
side and rear views (`RENDER`, `SECTIONS`, `FEATURES`; H = 250 px from the ground to the top of the rim).
The overall height itself is TBD: its default is a placeholder, and the width and depth follow from it in
the render's proportions. Material thicknesses (Jesmonite wall, metal parts) can't be read from a render
and are placeholders too (TBD). Where the render and the user's written facts disagree, the written facts
win and the difference is listed (the render shows a third rear port, "POWER": not modelled).

The head is lofted through superelliptic horizontal sections whose width (front view), depth and fore-aft
centre (side view) were measured at nine heights; the brass parts are layers or solids placed on that
surface. Every simplification relative to the render is a row in PRODUCTION_CHANGES.

Coordinate system (as Faro and Atelier): Z up, ground at z = 0 (the base ring's underside), the front
(face, grille) faces -Y, the rear panel faces +Y, X is the speaker's left (its right is -X). Units mm. One
solid per part; the eyes and the dials are one part each (quantity 2): `build` returns one, and the STEP
assembly and the GLB preview add the mirror copy (`INSTANCES`).
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from build123d import (Align, Axis, Box, Color, Compound, Cylinder, Edge, Plane, Polygon, Pos, Rot, Shape, Solid,
                       Vector, Wire, extrude, scale)

from app.cad.validation import ParamDef, ValidationIssue, ValidationResult, WallLimit

GENERATOR = "inti"
MIN = (Align.CENTER, Align.CENTER, Align.MIN)

# ---------------------------------------------------------------------------
# Proportions measured on the concept render (docs/inti/concept.png, 1140 x 1044 px)
# ---------------------------------------------------------------------------
# Front view x 45–330, side view x 380–560, rear view x 620–905; all three share one scale: ground at y 742 px
# and the top of the rim at y 492 px, so H = 250 px. Every value below is a fraction of H.
RENDER = {"file": "docs/inti/concept.png", "height_px": 250, "ground_y_px": 742,
          "views": {"front": "x 45–330 px", "side": "x 380–560 px (face to the left)", "rear": "x 620–905 px"}}

# Head sections: (z, half-width from the front view, half-depth from the side view, fore-aft centre from the
# side view, +Y = towards the back, relative to the base ring's centre). From the body's underside (on the base
# ring) to the crown. Section shape: superellipse of exponent SECTION_N (between an ellipse and a rounded
# rectangle; the render's top view isn't shown, so the exponent is a judgement from the hero view).
SECTIONS: list[tuple[float, float, float, float]] = [
    (0.088, 0.420, 0.234, 0.000),  # underside, on the base ring (y 720 px)
    (0.128, 0.500, 0.266, 0.002),  # jaw (y 710)
    (0.208, 0.534, 0.288, 0.008),  # y 690
    (0.408, 0.546, 0.300, 0.016),  # widest and deepest, at the dials (y 640)
    (0.608, 0.551, 0.288, 0.008),  # eyes (y 590)
    (0.808, 0.534, 0.240, -0.004),  # brow (y 540)
    (0.888, 0.500, 0.200, -0.004),  # rim's lower edge (y 520)
    (0.968, 0.474, 0.162, -0.022),  # y 500
    (1.000, 0.465, 0.150, -0.026),  # crown, flat (y 492)
]
SECTION_N = 3.0
SECTION_POINTS = 48

FEATURES: dict[str, dict[str, float]] = {
    # Eyes: an almond-shaped brass plate in a recessed socket, with a round pupil boss (front view; depth from
    # the side view). Spacing is centre to centre; the pupils sit slightly outboard of the almond's centre.
    "eye": {"z": 0.660, "spacing": 0.620, "width": 0.352, "height": 0.156, "pupil_d": 0.120,
            "pupil_outboard": 0.020, "recess": 0.025},
    # Nose: a tapered wedge from the crown (narrow, flush) down to a projecting tip (front and side views).
    "nose": {"top_width": 0.080, "bottom_z": 0.448, "bottom_width": 0.148, "tip_proud": 0.088},
    # Grille: stepped outline of two tiers centred on the face (front view and the "Signature grille" detail);
    # a raised frame round the perforated field.
    "grille": {"z": 0.264, "tall_width": 0.592, "tall_height": 0.288, "wide_width": 0.732, "wide_height": 0.152,
               "frame": 0.016},
    # Side dials: discs with a stepped-cross relief (side view and the "Volume control" detail).
    "dial": {"z": 0.370, "diameter": 0.296, "y": 0.040, "proud": 0.040, "relief": 0.006,
             "cross_arm": 0.65, "cross_bar": 0.22, "cross_mid": 0.44},  # cross sizes: fractions of the dial diameter
    # Top rim: a brass band round the crown, full height at the brow, open at the back (side and rear views).
    "top_rim": {"bottom_z": 0.888, "back_y": 0.068},
    # Base ring: an elliptical plinth narrower than the head (front: width; side: depth).
    "base_ring": {"half_width": 0.354, "half_depth": 0.200, "height": 0.088},
    # Rear panel: an inset rounded rectangle low on the back (rear view); USB-C on the viewer's left, aux in the
    # middle. The render's third port ("POWER", a barrel jack at x -0.156) is not modelled: the user's facts say
    # no separate power jack.
    "rear_panel": {"z": 0.188, "width": 0.552, "height": 0.200, "corner": 0.030, "port_z": 0.196,
                   "usb_c_x": 0.164, "aux_x": 0.000},
}

# Connector openings: typical sizes for a USB-C receptacle and a 3.5 mm jack (confirm with the chosen parts).
USBC_OPENING = (9.2, 3.6)
AUX_OPENING_D = 6.0
RING_WALL = 4.0  # base ring and top rim wall (placeholder, TBD)
SOCKET_BACKING = 2.5  # Jesmonite left behind an eye socket; the wall is thickened locally where it needs to be
# Placeholder envelopes for the bought-in electronics: space only. Sizes TBD.
DRIVER_DEPTH = 40.0
BATTERY_ENVELOPE = (70.0, 40.0, 20.0)
BOARD_ENVELOPE = (60.0, 8.0, 60.0)

# ---------------------------------------------------------------------------
# Parameters: the size and the thicknesses, all TBD (the proportions are fixed by the render)
# ---------------------------------------------------------------------------
_TBD = "TBD: placeholder, not a design value. "
PARAMS: list[ParamDef] = [
    ParamDef("overall_height", "Overall height", "Overall", 150, 450,
             help=_TBD + "Ground to the top of the rim. Everything else keeps the render's proportions: width about "
                         "1.10 x and depth about 0.60 x the height."),
    ParamDef("wall_thickness", "Body wall", "Body", 3.0, 15.0, step=0.1,
             help=_TBD + "Cast Jesmonite shell; thickened locally behind the eye sockets."),
    ParamDef("trim_thickness", "Metal part thickness", "Metalwork", 0.8, 6.0, step=0.1,
             help=_TBD + "Brass layers on the head (rim, grille frame, eye plates, rear panel inset)."),
    ParamDef("driver_diameter", "Driver envelope diameter", "Internal", 30, 200, step=0.5,
             help=_TBD + "Space only: no driver has been specified. Capped at the grille opening's height."),
]
PARAM_KEYS = [p.key for p in PARAMS]
PARAM_BY_KEY = {p.key: p for p in PARAMS}
TBD_PARAMS = list(PARAM_KEYS)

# Parameters that stay fixed when the speaker is scaled to another height.
UNSCALED_PARAMS = {"wall_thickness", "trim_thickness", "driver_diameter"}

CREAM = (0.93, 0.89, 0.80, 1.0)  # cream/ivory (render reference; colour standard TBD)
BRASS = (0.78, 0.64, 0.36, 1.0)
DARK = (0.08, 0.08, 0.09, 1.0)
PART_COLOURS: dict[str, tuple[float, float, float, float]] = {
    "body": CREAM, "brow_nose": BRASS, "eye": BRASS, "grille": BRASS, "dial": BRASS, "top_rim": BRASS,
    "base_ring": BRASS, "rear_panel": (0.06, 0.06, 0.07, 1.0), "driver": DARK,
    "battery": (0.2, 0.45, 0.75, 1.0), "main_board": (0.1, 0.35, 0.2, 1.0),
}
PART_KEYS = list(PART_COLOURS)
INSTANCES = {"eye": 2, "dial": 2}  # parts modelled once and fitted twice (mirrored left/right)

# Where the model departs from the concept render, and why (CAD tab and DFM report). INTI has no approved
# prototype model: the "prototype" column is the concept render.
PRODUCTION_CHANGES: list[dict[str, str]] = [
    {"feature": "Size", "prototype": "Concept render (no dimensions)",
     "production": "Proportions measured on the render (front, side and rear views); the overall height is a "
                   "placeholder (TBD) and the width and depth follow it"},
    {"feature": "Head form", "prototype": "Sculpted head-shaped body",
     "production": "Lofted through nine superelliptic sections measured on the render; the sculpted brow ridges "
                   "above the eyes and the cheek planes are not modelled. A surface model or scan of the master "
                   "replaces it"},
    {"feature": "Eyes", "prototype": "Almond-shaped brass eyes in recessed sockets, round pupils",
     "production": "Almond plate in a socket recessed about 0.025 x H, round pupil standing proud; the wall is "
                   "thickened behind the sockets"},
    {"feature": "Brow-and-nose piece", "prototype": "Tapered brass nose from the brow, projecting at the tip",
     "production": "Wedge from the crown to a tip about 0.09 x H proud; it meets the top rim, whose front reads as "
                   "the brow. Whether the nose and rim are one part or two is TBD"},
    {"feature": "Front grille", "prototype": "Stepped (Andean) outline, raised frame, round holes in a hex pattern",
     "production": "Two-tier stepped outline as the render; the perforation isn't modelled (hole size, pitch and "
                   "open area TBD)"},
    {"feature": "Side dials", "prototype": "Brass dials with a stepped-cross relief",
     "production": "Discs with the stepped cross in relief, on both sides; which is the volume control and what "
                   "the other does is TBD"},
    {"feature": "Top rim", "prototype": "Brass band round the crown, full height at the brow, open at the back",
     "production": "Modelled as the render"},
    {"feature": "Rear connection panel", "prototype": "Black inset panel: USB-C, AUX and POWER",
     "production": "USB-C and 3.5 mm aux only: the user's facts say no separate power jack, so the render's "
                   "POWER socket is not modelled (to be confirmed). Panel material and finish TBD (black in the "
                   "render). The rear emblem and 'SOUND CONNECTS US' marking are not modelled (TBD)"},
    {"feature": "Electronics", "prototype": "Bluetooth speaker",
     "production": "Driver, battery and main board are space-only placeholder envelopes; none is specified. "
                   "The battery is there only in case INTI is battery-powered: the power source (battery, or mains "
                   "over USB-C) is TBD"},
]

IMPLEMENTED_CHANGES: dict[str, set[str]] = {}

# What the model doesn't settle yet: shown in the DFM report and the CAD tab, for the user and suppliers.
OPEN_ITEMS: list[str] = [
    "Render vs design facts: the render's rear panel has a third port marked POWER; the design facts say no "
    "separate power jack. The model follows the facts; confirm.",
    "Sculpted form: the head is lofted from sections measured on the render until the sculpt's surface model "
    "or scan is supplied.",
    "Bottom closure and access: how the electronics go in and how the base is closed (base plate, fixings) "
    "is not decided.",
    "Fixing of the metal parts to the Jesmonite (bonded, cast-in inserts, screws from inside) is not decided.",
    "Internal structure: no chassis has been specified; the driver, battery and board are placeholder envelopes.",
    "Antenna: the Bluetooth antenna must sit behind the Jesmonite, away from the brass parts; range to be "
    "confirmed on a sample.",
]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _coerce(params: dict[str, Any], res: ValidationResult) -> dict[str, float]:
    p: dict[str, float] = {}
    for d in PARAMS:
        if d.key not in params or params[d.key] is None:
            res.errors.append(ValidationIssue(d.key, f"{d.label} is missing"))
            continue
        try:
            v = float(params[d.key])
        except (TypeError, ValueError):
            res.errors.append(ValidationIssue(d.key, f"{d.label} must be a number"))
            continue
        if not d.min <= v <= d.max:
            res.errors.append(ValidationIssue(d.key, f"{d.label} must be between {d.min:g} and {d.max:g} {d.unit}".rstrip()))
        if d.integer and v != int(v):
            res.errors.append(ValidationIssue(d.key, f"{d.label} must be a whole number"))
        p[d.key] = v
    return p


def section_at(z_frac: float) -> tuple[float, float, float]:
    """Half-width, half-depth and fore-aft centre (fractions of H) at a height, between the measured sections."""
    zs = [s[0] for s in SECTIONS]
    z = min(max(z_frac, zs[0]), zs[-1])
    for (z0, a0, b0, c0), (z1, a1, b1, c1) in zip(SECTIONS, SECTIONS[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return a0 + t * (a1 - a0), b0 + t * (b1 - b0), c0 + t * (c1 - c0)
    raise AssertionError("unreachable")


def surface_x(z_frac: float, y_frac: float) -> float:
    """The head's half-width (fraction of H) at a height and a fore-aft position (superelliptic section)."""
    a, b, c = section_at(z_frac)
    u = min(1.0, abs(y_frac - c) / b)
    return a * (1 - u ** SECTION_N) ** (1 / SECTION_N)


def derived(p: dict[str, float]) -> dict[str, float]:
    """Overall dimensions from the height and the render's proportions (fast, no build)."""
    H = p["overall_height"]
    width = 2 * max(s[1] for s in SECTIONS) * H
    depth = 2 * max(s[2] for s in SECTIONS) * H
    g = FEATURES["grille"]
    return {"width": width, "depth": depth, "body_height": (1 - SECTIONS[0][0]) * H,
            "grille_opening_height": (g["tall_height"] - 2 * g["frame"]) * H,
            "eye_recess": FEATURES["eye"]["recess"] * H}


def validate(params: dict[str, Any], wall_limits: dict[str, WallLimit] | None = None, *args: Any) -> ValidationResult:
    """Ranges and inter-dependencies before regeneration (fast: nothing is built)."""
    res = ValidationResult()
    p = _coerce(params, res)
    if res.errors:
        return res
    err = lambda param, msg: res.errors.append(ValidationIssue(param, msg))  # noqa: E731
    d = derived(p)
    if p["trim_thickness"] > d["eye_recess"] - 1:
        err("trim_thickness", f"The eye plates ({p['trim_thickness']:g} mm) must sit at least 1 mm down in their "
            f"{d['eye_recess']:.1f} mm sockets; use a thinner metal part or a taller head")
    if p["wall_thickness"] > FEATURES["base_ring"]["half_depth"] * p["overall_height"] - 10:
        err("wall_thickness", "The wall would close the head's bottom opening")
    for key, param in (("body", "wall_thickness"),):
        lim = (wall_limits or {}).get(key)
        if lim is None:
            continue
        v = p[param]
        flag = "" if lim.verified else " (unverified)"
        if not lim.min <= v <= lim.max:
            err(param, f"{v:g} mm is outside what {lim.process_name.lower()} can make ({lim.min:g}–{lim.max:g} mm){flag}")
        elif not lim.typical_min <= v <= lim.typical_max:
            res.warnings.append(ValidationIssue(
                param, f"{v:g} mm is outside the typical {lim.typical_min:g}–{lim.typical_max:g} mm for "
                       f"{lim.process_name.lower()}{flag}", "warning"))
    return res


def normalise(params: dict[str, Any]) -> dict[str, float | int]:
    return {d.key: (int(round(float(params[d.key]))) if d.integer else round(float(params[d.key]), 3)) for d in PARAMS}


def upgrade(params: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Saved parameters plus any parameter added since (taken from the template defaults); parameters the
    generator no longer has (the placeholder layout before the render) are dropped."""
    out = {k: v for k, v in params.items() if k in PARAM_BY_KEY}
    for k in PARAM_KEYS:
        out.setdefault(k, defaults.get(k))
    return out


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
@dataclass
class Model:
    parts: dict[str, Shape] = field(default_factory=dict)  # one solid per part key (eye and dial once)
    info: dict[str, Any] = field(default_factory=dict)


def _section_wire(z: float, a: float, b: float, cy: float) -> Wire:
    pts = []
    for i in range(SECTION_POINTS):
        t = 2 * math.pi * i / SECTION_POINTS
        c, s = math.cos(t), math.sin(t)
        pts.append(Vector(a * math.copysign(abs(c) ** (2 / SECTION_N), c),
                          cy + b * math.copysign(abs(s) ** (2 / SECTION_N), s), z))
    return Wire([Edge.make_spline(pts + [pts[0]])])


def _head(H: float, grow: float = 0.0) -> Solid:
    """The head lofted through the measured sections, every section grown outwards by `grow` mm (an
    approximate offset; negative shrinks). The crown stays at H and the underside on the base ring."""
    return Solid.make_loft([_section_wire(z * H, a * H + grow, b * H + grow, c * H) for z, a, b, c in SECTIONS])


def _slab(z0: float, z1: float) -> Shape:
    return Pos(0, 0, z0) * Box(4000, 4000, z1 - z0, align=MIN)


def _y_cyl(x: float, z: float, r: float, front: bool = True) -> Shape:
    """A cylinder along Y through the front (-Y) or rear (+Y) half, centred on (x, z)."""
    return Pos(x, -500 if front else 500, z) * Rot(90, 0, 0) * Cylinder(r, 1000)


def _y_box(x: float, z: float, w: float, h: float, front: bool = True) -> Shape:
    return Pos(x, -500 if front else 500, z) * Box(w, 1000, h)


def _almond(x: float, z: float, w: float, h: float) -> Shape:
    """An almond (vesica) through the front half: two circular arcs meeting at points w apart, h tall."""
    r = ((w / 2) ** 2 + (h / 2) ** 2) / h
    return _y_cyl(x, z - (r - h / 2), r) & _y_cyl(x, z + (r - h / 2), r)


def _solid(shape: Shape) -> Shape:
    """One solid per part (the boolean results come back as a compound)."""
    solids = shape.solids()
    if len(solids) == 1:
        return solids[0]
    out = solids[0]
    for s in solids[1:]:
        out = out.fuse(s)
    return out.solids()[0] if len(out.solids()) == 1 else out


def build_model(params: dict[str, Any]) -> Model:
    res = validate(params)
    if not res.ok:
        raise ValueError("; ".join(e.message for e in res.errors))
    p = {k: float(v) for k, v in normalise(params).items()}
    H, w, t = p["overall_height"], p["wall_thickness"], p["trim_thickness"]
    z0 = SECTIONS[0][0] * H
    outer = _head(H)
    grown = _head(H, t)
    info: dict[str, Any] = {"height_px": RENDER["height_px"]}
    front = Pos(0, -1000, 0) * Box(4000, 2000, 4000)  # the y < 0 half-space
    F = FEATURES

    # Body: hollow head, open underneath (closure TBD), closed flat crown.
    inner = _head(H, -w) & _slab(z0 - 1, H - w)
    body = outer - inner

    # Eyes: an almond socket recessed into the face, an almond brass plate at its floor and a round pupil
    # standing proud. The wall is thickened behind each socket where the socket is deeper than the wall allows.
    e = F["eye"]
    ex, ez, recess = -e["spacing"] / 2 * H, e["z"] * H, e["recess"] * H
    almond = _almond(ex, ez, e["width"] * H, e["height"] * H)
    both = lambda s: s + copy.copy(s).mirror(Plane.YZ)  # noqa: E731  (the body is cut for both eyes)
    socket_floor = _head(H, -recess)
    if recess + SOCKET_BACKING > w:
        backing = _almond(ex, ez, e["width"] * H + 2 * w, e["height"] * H + 2 * w)
        body = body + (both(backing) & front & (outer - _head(H, -recess - SOCKET_BACKING)))
        info["eye_socket_backing"] = True
    body = body - ((both(almond) & front & outer) - socket_floor)
    plate = (almond & front & _head(H, -recess + t)) - socket_floor
    px = ex - e["pupil_outboard"] * H  # outboard: away from the centre line
    pupil = (_y_cyl(px, ez, e["pupil_d"] / 2 * H) & front & grown) - socket_floor
    eye = plate + pupil

    # Brow-and-nose piece: a tapered wedge from the crown, flush there, to a projecting tip.
    n = F["nose"]
    zb = n["bottom_z"] * H
    _, b_top, c_top = section_at(1.0)
    _, b_bot, c_bot = section_at(n["bottom_z"])
    y_top = (c_top - b_top) * H - t  # just proud of the crown's front
    y_tip = (c_bot - b_bot - n["tip_proud"]) * H
    outline = extrude(Plane.XZ * Polygon((-n["top_width"] / 2 * H, H), (n["top_width"] / 2 * H, H),
                                         (n["bottom_width"] / 2 * H, zb), (-n["bottom_width"] / 2 * H, zb)),
                      amount=1000, both=True)
    profile = extrude(Plane.YZ * Polygon((y_tip, zb), (y_top, H), (0, H), (0, zb)), amount=1000, both=True)
    brow_nose = (outline & profile) - outer
    info["nose_tip_proud"] = n["tip_proud"] * H

    # Front grille: two-tier stepped outline; the body is cut inside the frame.
    g = F["grille"]
    gz = g["z"] * H
    tiers = [(g["tall_width"], g["tall_height"]), (g["wide_width"], g["wide_height"])]
    grille_outline = _y_box(0, gz, tiers[0][0] * H, tiers[0][1] * H) + _y_box(0, gz, tiers[1][0] * H, tiers[1][1] * H)
    fr = g["frame"] * H
    opening = (_y_box(0, gz, tiers[0][0] * H - 2 * fr, tiers[0][1] * H - 2 * fr)
               + _y_box(0, gz, tiers[1][0] * H - 2 * fr, tiers[1][1] * H - 2 * fr))
    grille = (grille_outline & front & grown) - outer
    body = body - (opening & front & outer)
    info["grille_tiers"] = len(tiers)
    info["grille_opening_height"] = tiers[0][1] * H - 2 * fr

    # Side dials: discs standing out of the head's left side (+X) with the stepped cross in relief; the right
    # dial is the mirror image.
    dl = F["dial"]
    dz, dy, rd = dl["z"] * H, dl["y"] * H, dl["diameter"] / 2 * H
    x_face = surface_x(dl["z"], dl["y"]) * H + dl["proud"] * H
    disc = (Pos(0, dy, dz) * Rot(0, 90, 0) * Cylinder(rd, x_face, align=MIN)) - outer
    D, rel = 2 * rd, dl["relief"] * H
    cross = None
    for cw, ch in ((dl["cross_bar"] * D, dl["cross_arm"] * D), (dl["cross_arm"] * D, dl["cross_bar"] * D),
                   (dl["cross_mid"] * D, dl["cross_mid"] * D)):
        bar = Pos(x_face + rel / 2, dy, dz) * Box(rel + 0.2, cw, ch)
        cross = bar if cross is None else cross + bar
    dial = disc + cross
    info["dial_x_face"] = x_face

    # Top rim: a band round the crown on the head's surface, full height at the brow, open at the back.
    r = F["top_rim"]
    back = Pos(0, r["back_y"] * H - 1000, 0) * Box(4000, 2000, 4000)  # y < back_y
    top_rim = (grown - outer) & _slab(r["bottom_z"] * H, H) & back

    # Base ring: an elliptical plinth under the head.
    br = F["base_ring"]
    a_o, b_o = br["half_width"] * H, br["half_depth"] * H
    base_ring = (scale(Cylinder(1, z0, align=MIN), by=(a_o, b_o, 1))
                 - Pos(0, 0, -1) * scale(Cylinder(1, z0 + 2, align=MIN), by=(a_o - RING_WALL, b_o - RING_WALL, 1)))

    # Rear connection panel: an inset rounded rectangle with the USB-C and 3.5 mm aux openings.
    rp = F["rear_panel"]
    rz, pz = rp["z"] * H, rp["port_z"] * H
    pw, ph = rp["width"] * H, rp["height"] * H
    slab_box = _y_box(0, rz, pw, ph, front=False)
    slab_box = slab_box.fillet(rp["corner"] * H, slab_box.edges().filter_by(Axis.Y))
    rear = Pos(0, 1000, 0) * Box(4000, 2000, 4000)
    inset = slab_box & rear & outer
    panel = inset - _head(H, -t)
    usbc = Pos(rp["usb_c_x"] * H, 250, pz) * Box(USBC_OPENING[0], 500, USBC_OPENING[1])
    aux = _y_cyl(rp["aux_x"] * H, pz, AUX_OPENING_D / 2, front=False)
    holes = usbc + aux
    body = (body - (inset - _head(H, -t))) - (holes & _slab(z0, H))
    panel = panel - holes
    info["rear_openings"] = ["usb_c", "aux_3_5mm"]

    # Bought-in placeholders (space only; sizes TBD).
    r_drv = min(p["driver_diameter"], info["grille_opening_height"]) / 2
    _, bg, cg = section_at(g["z"])
    y_front_in = (cg - bg) * H + w
    driver = Pos(0, y_front_in + 2, gz) * Rot(-90, 0, 0) * Cylinder(r_drv, DRIVER_DEPTH, align=MIN)
    bw, bd, bh = BATTERY_ENVELOPE
    battery = Pos(0, 0, z0 + 2) * Box(bw, bd, bh, align=MIN)
    ow, od, oh = BOARD_ENVELOPE
    board_z = max(pz, z0 + oh / 2 + bh + 6)
    _, bb, cb = section_at(board_z / H)
    y_rear_in = (cb + bb) * H - w
    board = Pos(0, y_rear_in - od - 12, board_z - oh / 2) * Box(ow, od, oh, align=(Align.CENTER, Align.MIN, Align.MIN))

    parts = {"body": body, "brow_nose": brow_nose, "eye": eye, "grille": grille, "dial": dial,
             "top_rim": top_rim, "base_ring": base_ring, "rear_panel": panel, "driver": driver,
             "battery": battery, "main_board": board}
    return Model(parts={k: _solid(v) for k, v in parts.items()}, info=info)


@lru_cache(maxsize=4)
def _cached(params_json: str) -> Model:
    return build_model(json.loads(params_json))


def model(params: dict[str, Any]) -> Model:
    """One build per parameter set."""
    return _cached(json.dumps(normalise(params), sort_keys=True))


def build(params: dict[str, Any]) -> dict[str, Shape]:
    return dict(model(params).parts)


def _instance_copies(parts: dict[str, Shape]) -> dict[str, Shape]:
    """The second eye and the second dial: mirror images of the first across the face's centre line."""
    return {f"{key}_2": copy.copy(parts[key]).mirror(Plane.YZ) for key in INSTANCES if key in parts}


def assembly(parts: dict[str, Shape], name: str = "inti") -> Compound:
    """A labelled, coloured compound for STEP and glTF export, with both eyes and both dials."""
    kids = []
    for key, shape in {**parts, **_instance_copies(parts)}.items():
        s = copy.copy(shape)
        s.label = key
        s.color = Color(*PART_COLOURS.get(key.removesuffix("_2"), (0.7, 0.7, 0.7, 1.0)))
        kids.append(s)
    return Compound(children=kids, label=name)


def preview_extras(params: dict[str, Any]) -> dict[str, tuple[Shape, tuple]]:
    """Preview-only bodies for the GLB: the second eye and the second dial."""
    return {k: (s, PART_COLOURS[k.removesuffix("_2")]) for k, s in _instance_copies(model(params).parts).items()}


def preview_two_tone(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {}


def public_derived(params: dict[str, Any]) -> dict[str, Any]:
    """Derived dimensions for the API (fast: from the parameters, no build)."""
    d = derived({k: float(v) for k, v in params.items()})
    return {k: round(v, 2) for k, v in d.items()}


def derived_traits(part_key: str, params: dict[str, Any]) -> list[str]:
    return []


def implements(change_key: str, cad_key: str | None, bodies: set[str]) -> bool:
    need = IMPLEMENTED_CHANGES.get(change_key)
    return need is not None and need <= bodies


def estimate_mass(part_info: dict[str, Any], densities: dict[str, float]) -> dict[str, Any]:
    """Mass from CAD volumes (mm³) and densities (g/cm³) per part key; the eyes and dials count twice.

    The driver, battery and board have no specified mass, so they are left out (the total says so)."""
    per = {k: round(info["volume_mm3"] / 1000 * densities[k] / 1000 * INSTANCES.get(k, 1), 3)
           for k, info in part_info.items() if k in densities}
    return {"total_kg": round(sum(per.values()), 3), "parts_kg": per,
            "excluded": [k for k in ("driver", "battery", "main_board") if k in part_info and k not in per]}


def production_change_checks(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Check the built solids against the render's proportions and the design facts."""
    H = float(params["overall_height"])
    m = model(params)
    parts, info = m.parts, m.info
    out = []

    def check(feature: str, ok: bool, detail: str) -> None:
        out.append({"feature": feature, "ok": bool(ok), "detail": detail})

    bb = parts["body"].bounding_box()
    w_ratio, d_ratio = bb.size.X / H, bb.size.Y / H
    check("Proportions", abs(w_ratio - 2 * 0.551) < 0.02 and abs(d_ratio - 2 * 0.300) < 0.02,
          f"head {w_ratio:.2f} x H wide and {d_ratio:.2f} x H deep (render: 1.10 and 0.60)")
    top = max(s.bounding_box().max.Z for k, s in parts.items() if k in ("body", "top_rim", "brow_nose"))
    check("Height", abs(top - H) < 0.05 and abs(parts["base_ring"].bounding_box().min.Z) < 1e-6,
          f"{top:.1f} mm ground to rim (overall height {H:g}, TBD)")
    metal = ["brow_nose", "eye", "grille", "dial", "top_rim", "base_ring"]
    check("Metal parts", all(k in parts and parts[k].volume > 0 for k in metal),
          "brow-and-nose piece, two eyes, stepped grille, two side dials, top rim and base ring are separate parts")
    eye_z = parts["eye"].center().Z / H
    check("Eyes", abs(eye_z - FEATURES["eye"]["z"]) < 0.02 and parts["eye"].center().X < 0,
          f"centres at {eye_z:.2f} x H (render 0.66), mirrored")
    gb = parts["grille"].bounding_box()
    check("Front grille", gb.max.Y < 0 and abs(gb.size.X / H - FEATURES["grille"]["wide_width"]) < 0.02
          and info.get("grille_tiers") == 2,
          f"stepped outline {gb.size.X / H:.2f} x H wide, {gb.size.Z / H:.2f} x H tall (render 0.73 and 0.29); "
          "front only, no rear grille")
    nb = parts["brow_nose"].bounding_box()
    check("Nose", abs(nb.min.Z / H - FEATURES["nose"]["bottom_z"]) < 0.01,
          f"from the crown down to {nb.min.Z / H:.2f} x H, tip {info.get('nose_tip_proud', 0):.1f} mm proud")
    dial2 = _instance_copies(parts)["dial_2"]
    check("Side dials", parts["dial"].center().X > 0 > dial2.center().X,
          f"Ø{FEATURES['dial']['diameter'] * H:.1f} with the stepped cross, one on each side (volume side TBD)")
    rb = parts["rear_panel"].bounding_box()
    check("Rear connection panel", info.get("rear_openings") == ["usb_c", "aux_3_5mm"] and rb.min.Y > 0,
          "USB-C and 3.5 mm aux; no separate power jack (the render's POWER socket is not modelled)")
    return out
