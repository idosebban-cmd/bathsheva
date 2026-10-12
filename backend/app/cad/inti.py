"""INTI parametric model: parameters, validation, geometry and mass.

INTI is a home Bluetooth speaker for Bathsheva London: a sculpted, head-shaped body in cream/ivory cast
Jesmonite with a smooth lacquer-like finish, and real-metal brass/gold parts (a brow-and-nose piece, two eyes,
a stepped front grille, two side dials, a top rim and a base ring). Front grille only; a rear connection
panel carries USB-C (power and charging) and a 3.5 mm aux input.

The only design source so far is the concept render (front, side, rear and detail views) and the user's
design facts (Oct 2026). No dimension has been given, so this model is a **massing placeholder**: every
parameter default is a placeholder chosen to make a buildable model, not a design value, and is listed as
TBD (`TBD_PARAMS`, the template's `tbd` list and the DFM report). The head is an ellipsoid cut flat at the
bottom and top, not the sculpted form; the brass parts are applied layers of `trim_thickness` that follow
the surface. Every simplification relative to the concept is a row in PRODUCTION_CHANGES.

Coordinate system (as Faro and Atelier): Z up, ground at z = 0 (the base ring's underside), the front
(face, grille) faces -Y, the rear panel faces +Y. Units mm. One solid per part; the eyes and the dials are
one part each (quantity 2): `build` returns one, and the STEP assembly and the GLB preview add the mirror
copy (`INSTANCES`).
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from build123d import Align, Box, Color, Compound, Cylinder, Plane, Pos, Rot, Shape, Sphere, scale

from app.cad.validation import ParamDef, ValidationIssue, ValidationResult, WallLimit

GENERATOR = "inti"
MIN = (Align.CENTER, Align.CENTER, Align.MIN)

# ---------------------------------------------------------------------------
# Modelling constants (placeholders for the massing model; none is a design value)
# ---------------------------------------------------------------------------
# The head is an ellipsoid cut flat this far from its centre (as a fraction of its vertical semi-axis): a
# narrower neck at the base ring and a flat crown under the top rim. Placeholder for the sculpted form.
BOTTOM_CUT = 0.85
TOP_CUT = 0.92
GRILLE_LAND = 3.0  # the grille overlaps the body this much round its opening (bonding land; TBD)
RING_INSET = 4.0  # base ring and top rim: radial width inside the body's section (TBD)
# Connector openings in the rear panel and body: typical sizes for a USB-C receptacle and a 3.5 mm jack
# (to be confirmed against the chosen connectors).
USBC_OPENING = (9.2, 3.6)
AUX_OPENING_D = 6.0
CONNECTOR_PITCH = 16.0  # USB-C to aux, centre to centre (placeholder)
# Placeholder envelopes for the bought-in electronics: space only. Sizes TBD (no driver, battery or board
# has been specified).
DRIVER_DEPTH = 40.0
BATTERY_ENVELOPE = (70.0, 40.0, 20.0)
BOARD_ENVELOPE = (60.0, 8.0, 60.0)

# ---------------------------------------------------------------------------
# Parameters (every default is a placeholder: TBD)
# ---------------------------------------------------------------------------
_TBD = "TBD: placeholder, not taken from the concept. "
PARAMS: list[ParamDef] = [
    ParamDef("overall_height", "Overall height", "Overall", 150, 450,
             help=_TBD + "Ground (base ring underside) to the top of the top rim."),
    ParamDef("body_width", "Head width", "Overall", 100, 350, step=0.5, help=_TBD + "At the widest, side to side."),
    ParamDef("body_depth", "Head depth", "Overall", 100, 350, step=0.5, help=_TBD + "At the deepest, front to back."),
    ParamDef("wall_thickness", "Body wall", "Body", 3.0, 15.0, step=0.1,
             help=_TBD + "Cast Jesmonite shell (Atelier's Jesmonite body used 3.5 mm general, 5 mm locally)."),
    ParamDef("base_ring_height", "Base ring height", "Metalwork", 3, 40, step=0.5, help=_TBD),
    ParamDef("top_rim_height", "Top rim height", "Metalwork", 2, 30, step=0.5, help=_TBD),
    ParamDef("trim_thickness", "Metal trim thickness", "Metalwork", 0.8, 8.0, step=0.1,
             help=_TBD + "How far the brow-and-nose piece and the eyes stand proud of the body."),
    ParamDef("brow_height", "Brow centre height", "Face", 60, 420, step=0.5, help=_TBD),
    ParamDef("brow_width", "Brow width", "Face", 30, 300, step=0.5, help=_TBD),
    ParamDef("brow_band", "Brow band height", "Face", 3, 40, step=0.5, help=_TBD),
    ParamDef("nose_width", "Nose width", "Face", 3, 60, step=0.5, help=_TBD),
    ParamDef("nose_length", "Nose length below the brow", "Face", 5, 150, step=0.5, help=_TBD),
    ParamDef("eye_height", "Eye centre height", "Face", 50, 420, step=0.5, help=_TBD),
    ParamDef("eye_spacing", "Eye spacing (centre to centre)", "Face", 20, 250, step=0.5, help=_TBD),
    ParamDef("eye_diameter", "Eye diameter", "Face", 5, 80, step=0.5, help=_TBD),
    ParamDef("grille_height", "Grille centre height", "Grille", 30, 400, step=0.5, help=_TBD),
    ParamDef("grille_diameter", "Grille outer diameter", "Grille", 30, 250, step=0.5, help=_TBD),
    ParamDef("grille_steps", "Grille steps", "Grille", 1, 6, integer=True, unit="",
             help=_TBD + "Number of steps in the stepped grille (modelled as concentric rings)."),
    ParamDef("grille_step_rise", "Grille step rise", "Grille", 0.5, 6, step=0.1, help=_TBD + "Height of each step."),
    ParamDef("grille_step_inset", "Grille step inset", "Grille", 1, 30, step=0.5,
             help=_TBD + "Each step's radius is this much smaller than the one below it."),
    ParamDef("dial_height", "Side dial centre height", "Controls", 30, 420, step=0.5, help=_TBD),
    ParamDef("dial_diameter", "Side dial diameter", "Controls", 10, 80, step=0.5, help=_TBD),
    ParamDef("dial_proud", "Side dial projection", "Controls", 2, 40, step=0.5,
             help=_TBD + "How far the dial stands out from the head at its centre."),
    ParamDef("rear_panel_height", "Rear panel centre height", "Rear", 20, 400, step=0.5, help=_TBD),
    ParamDef("rear_panel_width", "Rear panel width", "Rear", 30, 150, step=0.5, help=_TBD),
    ParamDef("rear_panel_tall", "Rear panel height", "Rear", 15, 120, step=0.5, help=_TBD),
    ParamDef("driver_diameter", "Driver envelope diameter", "Internal", 30, 200, step=0.5,
             help=_TBD + "Space only: no driver has been specified."),
]
PARAM_KEYS = [p.key for p in PARAMS]
PARAM_BY_KEY = {p.key: p for p in PARAMS}
TBD_PARAMS = list(PARAM_KEYS)  # every parameter is a placeholder until the user gives the dimension

# Parameters that stay fixed when the speaker is scaled to another height.
UNSCALED_PARAMS = {"wall_thickness", "trim_thickness", "grille_steps", "grille_step_rise"}

CREAM = (0.93, 0.89, 0.80, 1.0)  # cream/ivory (render reference; colour standard TBD)
BRASS = (0.78, 0.64, 0.36, 1.0)
DARK = (0.08, 0.08, 0.09, 1.0)
PART_COLOURS: dict[str, tuple[float, float, float, float]] = {
    "body": CREAM, "brow_nose": BRASS, "eye": BRASS, "grille": BRASS, "dial": BRASS, "top_rim": BRASS,
    "base_ring": BRASS, "rear_panel": (0.55, 0.52, 0.48, 1.0), "driver": DARK,
    "battery": (0.2, 0.45, 0.75, 1.0), "main_board": (0.1, 0.35, 0.2, 1.0),
}
PART_KEYS = list(PART_COLOURS)
INSTANCES = {"eye": 2, "dial": 2}  # parts modelled once and fitted twice (mirrored left/right)

# Where the model departs from the concept render, and why (CAD tab and DFM report). INTI has no approved
# prototype model yet: the "prototype" column is the concept render.
PRODUCTION_CHANGES: list[dict[str, str]] = [
    {"feature": "Head form", "prototype": "Concept render: sculpted head-shaped body",
     "production": "Massing placeholder: an ellipsoid cut flat at the base and crown. The sculpt (a 3D scan or "
                   "surface model of the master) replaces it; overall dimensions TBD"},
    {"feature": "Dimensions", "prototype": "Concept render (no dimensions given)",
     "production": "Every dimension is a placeholder (TBD) so that a model can be built; none is a design value"},
    {"feature": "Brow-and-nose piece and eyes", "prototype": "Sculpted brass/gold features on the face",
     "production": "Modelled as flat-outlined layers that follow the head's surface (trim_thickness proud); "
                   "true form, fixing and fit TBD"},
    {"feature": "Front grille", "prototype": "Stepped brass/gold grille",
     "production": "Modelled as solid concentric steps over the sound opening; step form, perforation pattern, "
                   "open area and sheet thickness TBD"},
    {"feature": "Side dials", "prototype": "Two brass/gold dials, one the volume control",
     "production": "Modelled as two plain cylinders; the second dial's function, knurl or detailing, travel and "
                   "detents TBD"},
    {"feature": "Rear connection panel", "prototype": "USB-C (power and charging) and 3.5 mm aux; no rear grille",
     "production": "Rectangular panel with a USB-C and a 3.5 mm opening at typical connector sizes; panel "
                   "material, size and fixing TBD. No rear grille and no separate power jack, as the concept"},
    {"feature": "Electronics", "prototype": "Bluetooth speaker",
     "production": "Driver, battery and main board are space-only placeholder envelopes; none is specified"},
]

IMPLEMENTED_CHANGES: dict[str, set[str]] = {}

# What the model doesn't settle yet: shown in the DFM report and the CAD tab, for the user and suppliers.
OPEN_ITEMS: list[str] = [
    "Sculpted form: the head is a placeholder ellipsoid until the sculpt's surface model or scan is supplied.",
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


def derived(p: dict[str, float]) -> dict[str, float]:
    """The head ellipsoid and its sections, from the parameters without building (fast)."""
    hb, ht = p["base_ring_height"], p["top_rim_height"]
    body_h = p["overall_height"] - hb - ht
    c = body_h / (BOTTOM_CUT + TOP_CUT)
    zc = hb + BOTTOM_CUT * c
    a, b = p["body_width"] / 2, p["body_depth"] / 2
    return {"body_height": body_h, "a": a, "b": b, "c": c, "zc": zc, "z_bottom": hb, "z_top": hb + body_h,
            "bottom_section": math.sqrt(1 - BOTTOM_CUT ** 2), "top_section": math.sqrt(1 - TOP_CUT ** 2)}


def _section(d: dict[str, float], z: float) -> float:
    """The head's section scale at height z (1 at its widest, 0 beyond it)."""
    u = (z - d["zc"]) / d["c"]
    return math.sqrt(max(0.0, 1 - u * u))


def validate(params: dict[str, Any], wall_limits: dict[str, WallLimit] | None = None, *args: Any) -> ValidationResult:
    """Ranges and inter-dependencies before regeneration (fast: nothing is built)."""
    res = ValidationResult()
    p = _coerce(params, res)
    if res.errors:
        return res
    err = lambda param, msg: res.errors.append(ValidationIssue(param, msg))  # noqa: E731
    d = derived(p)
    lo, hi = d["z_bottom"] + 0.1 * d["body_height"], d["z_top"] - 0.1 * d["body_height"]
    if d["body_height"] < 80:
        err("overall_height", "The head would be shorter than 80 mm between the base ring and the top rim")
    for key in ("brow_height", "eye_height", "grille_height", "dial_height", "rear_panel_height"):
        if not lo <= p[key] <= hi:
            err(key, f"{PARAM_BY_KEY[key].label} must sit on the head, between {lo:.0f} and {hi:.0f} mm")
    if res.errors:
        return res
    half_w = lambda z: d["a"] * _section(d, z)  # noqa: E731
    r_g = p["grille_diameter"] / 2
    if r_g > 0.8 * half_w(p["grille_height"]):
        err("grille_diameter", "The grille is wider than the face at its height (at most 80% of the head's width)")
    if p["grille_steps"] > 1 and r_g - (p["grille_steps"] - 1) * p["grille_step_inset"] < 5:
        err("grille_step_inset", "The innermost grille step would be smaller than Ø10")
    if r_g - GRILLE_LAND < 5:
        err("grille_diameter", "The sound opening under the grille would be smaller than Ø10")
    r_e = p["eye_diameter"] / 2
    if p["eye_spacing"] < p["eye_diameter"] + p["nose_width"]:
        err("eye_spacing", "The eyes would touch each other or the nose")
    if p["eye_spacing"] / 2 + r_e > 0.85 * half_w(p["eye_height"]):
        err("eye_spacing", "The eyes run off the face at their height")
    brow_lo = p["brow_height"] - p["brow_band"] / 2
    if p["eye_height"] + r_e > brow_lo:
        err("eye_height", "The eyes must sit below the brow")
    nose_bottom = brow_lo - p["nose_length"]
    if nose_bottom < p["grille_height"] + r_g:
        err("nose_length", "The nose would run into the grille")
    if p["eye_height"] - r_e < p["grille_height"] + r_g:
        err("eye_height", "The eyes would overlap the grille")
    if p["brow_width"] / 2 > 0.85 * half_w(p["brow_height"]):
        err("brow_width", "The brow runs off the face at its height")
    if p["brow_height"] + p["brow_band"] / 2 > d["z_top"] - 2:
        err("brow_height", "The brow would run into the top rim")
    if p["dial_diameter"] / 2 > 0.6 * d["b"] * _section(d, p["dial_height"]):
        err("dial_diameter", "The side dial is too large for the head's side at its height")
    if p["rear_panel_width"] / 2 > 0.6 * half_w(p["rear_panel_height"]):
        err("rear_panel_width", "The rear panel is wider than the back of the head at its height")
    if p["rear_panel_width"] < CONNECTOR_PITCH + USBC_OPENING[0] + 6 or p["rear_panel_tall"] < 2 * AUX_OPENING_D:
        err("rear_panel_width", "The rear panel must fit the USB-C and 3.5 mm openings with 3 mm round them")
    if p["wall_thickness"] * 2 + 10 > 2 * min(d["a"], d["b"]) * d["bottom_section"]:
        err("wall_thickness", "The wall would close the bottom opening")
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
    """Saved parameters plus any parameter added since (taken from the template defaults)."""
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


def _ellipsoid(d: dict[str, float], grow: float = 0.0) -> Shape:
    """The head ellipsoid, every semi-axis grown by `grow` (an approximate offset)."""
    return Pos(0, 0, d["zc"]) * scale(Sphere(1), by=(d["a"] + grow, d["b"] + grow, d["c"] + grow))


def _slab(z0: float, z1: float) -> Shape:
    return Pos(0, 0, z0) * Box(2000, 2000, z1 - z0, align=MIN)


def _y_prism(x: float, z: float, w: float, h: float, front: bool = True) -> Shape:
    """A box through the front (-Y) or rear (+Y) half, centred on (x, z), w wide and h tall."""
    return Pos(x, -500 if front else 500, z) * Box(w, 1000, h)


def _y_cyl(x: float, z: float, r: float, front: bool = True) -> Shape:
    return Pos(x, -250 if front else 250, z) * Rot(90, 0, 0) * Cylinder(r, 500)


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
    d = derived(p)
    w, t = p["wall_thickness"], p["trim_thickness"]
    z0, z1 = d["z_bottom"], d["z_top"]
    outer = _ellipsoid(d)
    skin = _ellipsoid(d, t) - outer  # the layer the applied metal parts occupy
    info: dict[str, Any] = {}

    # Body: hollow head, open at the bottom (closure TBD), closed crown under the top rim.
    body = (outer & _slab(z0, z1)) - (_ellipsoid(d, -w) & _slab(z0 - 1, z1 - w))

    # Front grille: concentric steps over the sound opening; the body is cut for the opening.
    gz, rg = p["grille_height"], p["grille_diameter"] / 2
    steps = int(p["grille_steps"])
    grille = None
    for k in range(steps):
        layer = _ellipsoid(d, (k + 1) * p["grille_step_rise"]) - outer
        ring = layer & _y_cyl(0, gz, rg - k * p["grille_step_inset"])
        grille = ring if grille is None else grille + ring
    body = body - (_y_cyl(0, gz, rg - GRILLE_LAND) & _slab(z0, z1))
    info["grille_steps"] = steps
    info["sound_opening_dia"] = 2 * (rg - GRILLE_LAND)

    # Brow-and-nose piece: one T-shaped part.
    bz, band = p["brow_height"], p["brow_band"]
    nose_top = bz - band / 2
    nose_bottom = nose_top - p["nose_length"]
    t_shape = _y_prism(0, bz, p["brow_width"], band) + _y_prism(0, (nose_top + nose_bottom) / 2 + 0.5,
                                                               p["nose_width"], p["nose_length"] + 1)
    brow_nose = skin & t_shape

    # Eyes: the viewer's left eye (-X); the other is its mirror image.
    eye = skin & _y_cyl(-p["eye_spacing"] / 2, p["eye_height"], p["eye_diameter"] / 2)

    # Side dials: the right dial (+X) as a cylinder standing out of the side; the left is its mirror image.
    dz, rd = p["dial_height"], p["dial_diameter"] / 2
    x_side = d["a"] * _section(d, dz)
    dial = (Pos(0, 0, dz) * Rot(0, 90, 0) * Cylinder(rd, x_side + p["dial_proud"], align=MIN)) - outer
    info["dial_x"] = x_side

    # Top rim and base ring: flat elliptical rings on the crown and under the neck.
    def ring(z_section: float, za: float, zb: float) -> Shape:
        s = _section(d, z_section)
        a_o, b_o = d["a"] * s, d["b"] * s
        outer_r = Pos(0, 0, za) * scale(Cylinder(1, zb - za, align=MIN), by=(a_o, b_o, 1))
        inner_r = Pos(0, 0, za - 1) * scale(Cylinder(1, zb - za + 2, align=MIN),
                                            by=(a_o - RING_INSET, b_o - RING_INSET, 1))
        return outer_r - inner_r

    top_rim = ring(z1, z1, z1 + p["top_rim_height"])
    base_ring = ring(z0, 0.0, z0)

    # Rear connection panel: USB-C and 3.5 mm aux openings through the panel and the body.
    rz = p["rear_panel_height"]
    panel = skin & _y_prism(0, rz, p["rear_panel_width"], p["rear_panel_tall"], front=False)
    usbc = Pos(-CONNECTOR_PITCH / 2, 250, rz) * Box(USBC_OPENING[0], 500, USBC_OPENING[1])
    aux = _y_cyl(CONNECTOR_PITCH / 2, rz, AUX_OPENING_D / 2, front=False)
    holes = usbc + aux
    panel = panel - holes
    body = body - (holes & _slab(z0, z1))
    info["rear_openings"] = ["usb_c", "aux_3_5mm"]

    # Bought-in placeholders (space only; sizes TBD).
    r_drv = min(p["driver_diameter"], 2 * (rg - GRILLE_LAND)) / 2
    y_front_in = -(d["b"] - w) * _section(d, gz)
    driver = Pos(0, y_front_in + 2 + DRIVER_DEPTH, gz) * Rot(90, 0, 0) * Cylinder(r_drv, DRIVER_DEPTH, align=MIN)
    bw, bd, bh = BATTERY_ENVELOPE
    battery = Pos(0, 0, z0 + 2) * Box(bw, bd, bh, align=MIN)
    ow, od, oh = BOARD_ENVELOPE
    y_rear_in = (d["b"] - w) * _section(d, rz)
    board = Pos(0, y_rear_in - od - 6, rz - oh / 2) * Box(ow, od, oh, align=(Align.CENTER, Align.MIN, Align.MIN))

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
    return {"body_height": round(d["body_height"], 2), "neck_width": round(2 * d["a"] * d["bottom_section"], 2),
            "crown_width": round(2 * d["a"] * d["top_section"], 2)}


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
    """Check the built solids against what the concept fixes (the PRODUCTION_CHANGES rows geometry can prove)."""
    m = model(params)
    parts, info = m.parts, m.info
    out = []

    def check(feature: str, ok: bool, detail: str) -> None:
        out.append({"feature": feature, "ok": bool(ok), "detail": detail})

    metal = ["brow_nose", "eye", "grille", "dial", "top_rim", "base_ring"]
    check("Metal parts", all(k in parts and parts[k].volume > 0 for k in metal),
          "brow-and-nose piece, two eyes, stepped grille, two side dials, top rim and base ring are separate parts")
    check("Front grille", info.get("grille_steps", 0) >= 1 and parts["grille"].bounding_box().max.Y < 0,
          f"{info.get('grille_steps', 0)} steps on the front; sound opening Ø{info.get('sound_opening_dia', 0):.1f}")
    check("No rear grille", parts["grille"].bounding_box().max.Y < 0 and "rear_grille" not in parts,
          "front grille only; the rear has the connection panel")
    check("Rear connection panel", info.get("rear_openings") == ["usb_c", "aux_3_5mm"]
          and parts["rear_panel"].bounding_box().min.Y > 0,
          "USB-C (power and charging) and 3.5 mm aux; no separate power jack")
    eyes = [parts["eye"], *_instance_copies(parts).get("eye_2", parts["eye"]).solids()]
    check("Eyes", len(eyes) == 2 and eyes[0].center().X < 0 < eyes[1].center().X, "two eyes, mirrored")
    dial2 = _instance_copies(parts)["dial_2"]
    check("Side dials", parts["dial"].center().X > 0 > dial2.center().X, "one on each side (volume side TBD)")
    return out
