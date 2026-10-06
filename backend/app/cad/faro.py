"""Faro parametric model: parameter definitions, validation and geometry.

Coordinate system: Z up, origin at the centre of the underside of the base,
units in millimetres. One CadQuery solid per part; keys match Part.cad_key.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import cadquery as cq

GENERATOR = "faro"

# Fixed construction constants (not user parameters).
PLATE_FLANGE = 1.5  # LED plate flange that sits on the body's top edge
LED_PLATE_THICKNESS = 3.0  # LED plate spigot inside the body top
LED_PUCK_HEIGHT = 8.0
SLEEVE_WALL = 3.0  # threaded LED holder sleeve on the lamp tube
GASKET_T = 2.0  # silicone gasket thickness (each end of the glass)
GASKET_OVERHANG = 0.5  # gasket ring extends this far past the glass wall on both sides
MIN_GLASS_IN_CAP = 3.0  # how far the glass must reach up inside the cap
BAND_CLEARANCE = 0.2  # radial clearance between the band ring and the body step
WASHER_T = 1.5
NUT_H = 5.0  # thin lamp nut
TUBE_BELOW_NUT = 2.0
CAP_NUT_H = 12.0
SCREW_CLEARANCE = 4.5  # M4 screws through the weight plate into the base rivet nuts
POT_BODY_D = 17.0  # rotary potentiometer body
POT_DEPTH = 20.0  # potentiometer depth inside the base skirt
KNOB_D = 20.0
KNOB_L = 14.0
MIN_BODY_HEIGHT = 60.0


@dataclass(frozen=True)
class ParamDef:
    key: str
    label: str
    group: str
    min: float
    max: float
    step: float = 1.0
    unit: str = "mm"
    integer: bool = False
    help: str = ""


PARAMS: list[ParamDef] = [
    ParamDef("overall_height", "Overall height", "Overall", 200, 900, help="Base underside to the top of the cap nut."),
    ParamDef("target_mass_kg", "Target total lamp mass", "Overall", 0.3, 10, step=0.1, unit="kg",
             help="Used to check the weight plate gives the lamp a solid, planted feel."),
    ParamDef("base_diameter", "Base diameter", "Base", 80, 400),
    ParamDef("base_height", "Base height", "Base", 10, 80),
    ParamDef("weight_plate_diameter", "Weight plate diameter", "Base", 30, 380,
             help="Laser-cut steel plate inside the base shell."),
    ParamDef("weight_plate_thickness", "Weight plate thickness", "Base", 2, 25, step=0.5),
    ParamDef("body_diameter", "Body diameter (bottom)", "Body", 50, 300),
    ParamDef("body_top_diameter", "Body diameter (top)", "Body", 40, 300,
             help="Smaller than the bottom gives the lighthouse taper; equal makes a straight tube."),
    ParamDef("wall_thickness", "Wall thickness (spun aluminium parts)", "Body", 0.5, 10, step=0.1),
    ParamDef("step_depth", "Band locating step depth", "Band", 0.5, 6, step=0.1,
             help="The body steps in by this much at the bottom of the band; the ring sits on the step."),
    ParamDef("band_height", "Decorative band height", "Band", 5, 100),
    ParamDef("band_position", "Band position (fraction of body height)", "Band", 0.1, 0.9, step=0.01, unit="",
             help="0 = bottom of body, 1 = top."),
    ParamDef("band_wall_thickness", "Band ring wall (stock tube)", "Band", 1, 6, step=0.1),
    ParamDef("lantern_height", "Lantern height (visible)", "Lantern", 20, 250,
             help="Visible glass between the LED plate and the cap; the glass runs on up inside the cap."),
    ParamDef("lantern_diameter", "Lantern diameter", "Lantern", 30, 300),
    ParamDef("lantern_wall_thickness", "Lantern wall thickness", "Lantern", 1, 8, step=0.1,
             help="Borosilicate stock tube: 90 mm OD comes in 2.5 or 3.5 mm walls."),
    ParamDef("top_cap_diameter", "Top cap diameter", "Top cap", 30, 320),
    ParamDef("top_cap_height", "Top cap height", "Top cap", 10, 150),
    ParamDef("tube_diameter", "Lamp tube diameter", "Construction", 8, 16, step=0.5,
             help="Hollow threaded lamp tube; 10 = M10x1."),
    ParamDef("cable_hole_diameter", "Cable hole diameter", "Construction", 3, 20, step=0.5),
    ParamDef("dimmer_hole_diameter", "Dimmer hole diameter (0 = no in-base dimmer)", "Construction", 0, 12, step=0.5,
             help="Hole in the base side for the rotary dimmer bushing; 0 for a touch or inline dimmer."),
    ParamDef("mounting_hole_count", "Rivet-nut count (weight plate fixing)", "Construction", 2, 8, unit="", integer=True),
    ParamDef("mounting_hole_diameter", "Rivet-nut hole diameter", "Construction", 2, 10, step=0.1,
             help="M4 aluminium rivet nuts usually need a 6.0 mm hole."),
    ParamDef("mounting_hole_pcd", "Rivet-nut pitch-circle diameter", "Construction", 20, 300,
             help="Diameter of the circle the rivet nuts sit on (hidden under the body foot)."),
]
PARAM_KEYS = [p.key for p in PARAMS]
PARAM_BY_KEY = {p.key: p for p in PARAMS}

PART_COLOURS: dict[str, tuple[float, float, float, float]] = {
    "base": (0.05, 0.05, 0.05, 1.0),
    "main_body": (0.80, 0.26, 0.22, 1.0),
    "band": (0.93, 0.89, 0.80, 1.0),
    "lantern": (0.80, 0.90, 0.95, 0.35),
    "top_cap": (0.80, 0.26, 0.22, 1.0),
    "led_module": (0.55, 0.55, 0.58, 1.0),
    "cable": (0.92, 0.92, 0.90, 1.0),
    "dimmer": (0.72, 0.70, 0.66, 1.0),
    "weight_plate": (0.45, 0.47, 0.50, 1.0),
    "lamp_tube": (0.70, 0.70, 0.72, 1.0),
    "lamp_nut": (0.70, 0.70, 0.72, 1.0),
    "cap_nut": (0.78, 0.64, 0.32, 1.0),
    "gasket_lower": (0.95, 0.95, 0.95, 0.9),
    "gasket_upper": (0.95, 0.95, 0.95, 0.9),
}
PART_KEYS = list(PART_COLOURS)

# Design changes from seed/cost/route_changes.yaml that this generator already shows,
# and the bodies that prove a generated model has them.
IMPLEMENTED_CHANGES: dict[str, set[str]] = {
    "thin_shell_needs_mass": {"weight_plate"},  # base shell with cavity and weight plate
    "thin_wall_inserts": {"weight_plate", "lamp_tube"},  # rivet-nut holes + central lamp tube
}


def implements(change_key: str, cad_key: str | None, bodies: set[str]) -> bool:
    """Whether a CAD model with these bodies shows the design change a process route needs."""
    need = IMPLEMENTED_CHANGES.get(change_key)
    return need is not None and need <= bodies


@dataclass
class ValidationIssue:
    param: str | None
    message: str
    level: str = "error"  # error | warning

    def as_dict(self) -> dict[str, Any]:
        return {"param": self.param, "message": self.message, "level": self.level}


@dataclass
class ValidationResult:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [e.as_dict() for e in self.errors],
            "warnings": [w.as_dict() for w in self.warnings],
        }


@dataclass(frozen=True)
class WallLimit:
    """Wall thickness limits from the rules data for the process chosen for a part."""

    process_name: str
    min: float
    max: float
    typical_min: float
    typical_max: float
    verified: bool = False


def _cap_fillets(p: dict[str, float]) -> tuple[float, float]:
    """Outer and inner fillet radii of the spun cap shell."""
    rc, ch, w = p["top_cap_diameter"] / 2, p["top_cap_height"], p["wall_thickness"]
    nut_r = p["tube_diameter"] * 0.8
    fo = max(min(ch - w - 1.0, rc - nut_r - 1.0, max(rc, ch) * 0.8), 0.0)
    fi = fo - w if fo - w > 0.3 else 0.0
    return fo, fi


def cap_inner_height(p: dict[str, float], r: float) -> float:
    """Height of the cap's inside surface above the cap's bottom edge, at radius r."""
    rc, ch, w = p["top_cap_diameter"] / 2, p["top_cap_height"], p["wall_thickness"]
    _, fi = _cap_fillets(p)
    ri, hi = rc - w, ch - w
    if fi <= 0 or r <= ri - fi:
        return hi
    dx = min(r - (ri - fi), fi)
    return hi - fi + math.sqrt(max(fi * fi - dx * dx, 0.0))


def derived(p: dict[str, float]) -> dict[str, float]:
    """Dimensions computed from parameters."""
    bh, w = p["base_height"], p["wall_thickness"]
    body_height = p["overall_height"] - bh - PLATE_FLANGE - p["lantern_height"] - p["top_cap_height"] - CAP_NUT_H
    body_top_z = bh + body_height
    plate_top_z = body_top_z + PLATE_FLANGE
    cap_bottom_z = plate_top_z + p["lantern_height"]
    rl = p["lantern_diameter"] / 2
    glass_top_z = cap_bottom_z + cap_inner_height(p, rl) - GASKET_T
    plate_bottom_z = bh - w - p["weight_plate_thickness"]
    r_bot, r_top, s = p["body_diameter"] / 2, p["body_top_diameter"] / 2, p["step_depth"]
    zc = p["band_position"] * body_height
    z1 = zc - p["band_height"] / 2
    r_nom_top = r_top + s  # the lower section's taper line meets the top radius plus the step
    r_z1 = r_bot + (r_nom_top - r_bot) * z1 / body_height if body_height > 0 else r_bot
    band_inner_r = r_z1 - s + BAND_CLEARANCE
    return {
        "body_height": body_height,
        "body_bottom_z": bh,
        "body_top_z": body_top_z,
        "plate_top_z": plate_top_z,
        "cap_bottom_z": cap_bottom_z,
        "cap_top_z": cap_bottom_z + p["top_cap_height"],
        "glass_bottom_z": plate_top_z + GASKET_T,
        "glass_top_z": glass_top_z,
        "glass_length": glass_top_z - (plate_top_z + GASKET_T),
        "glass_in_cap": glass_top_z - cap_bottom_z,
        "weight_plate_bottom_z": plate_bottom_z,
        "cable_z": plate_bottom_z / 2,
        "band_bottom_local_z": z1,
        "band_inner_diameter": 2 * band_inner_r,
        "band_outer_diameter": 2 * (band_inner_r + p["band_wall_thickness"]),
        "central_hole_diameter": p["tube_diameter"] + 0.5,
        "tube_bottom_z": plate_bottom_z - WASHER_T - NUT_H - TUBE_BELOW_NUT,
        "tube_top_z": cap_bottom_z + p["top_cap_height"] + CAP_NUT_H - 3.0,
    }


def validate(
    params: dict[str, Any],
    wall_limits: dict[str, WallLimit] | None = None,
    min_stability_ratio: float | None = None,
) -> ValidationResult:
    """Validate ranges and inter-dependencies before regeneration.

    wall_limits maps part key ("main_body", "lantern", ...) to the process wall
    limits; outside min/max is an error, outside typical range a warning.
    """
    res = ValidationResult()
    err = lambda param, msg: res.errors.append(ValidationIssue(param, msg))  # noqa: E731
    warn = lambda param, msg: res.warnings.append(ValidationIssue(param, msg, "warning"))  # noqa: E731

    p: dict[str, float] = {}
    for d in PARAMS:
        if d.key not in params or params[d.key] is None:
            err(d.key, f"{d.label} is required")
            continue
        try:
            v = float(params[d.key])
        except (TypeError, ValueError):
            err(d.key, f"{d.label} must be a number")
            continue
        if math.isnan(v) or math.isinf(v):
            err(d.key, f"{d.label} must be a finite number")
            continue
        if d.integer and v != int(v):
            err(d.key, f"{d.label} must be a whole number")
            continue
        if not d.min <= v <= d.max:
            err(d.key, f"{d.label} must be between {d.min:g} and {d.max:g} {d.unit}".rstrip())
            continue
        p[d.key] = v
    unknown = set(params) - set(PARAM_KEYS)
    for k in sorted(unknown):
        err(k, f"Unknown parameter {k!r}")
    if len(p) != len(PARAMS):
        return res  # can't check relationships without every value

    d = derived(p)
    w = p["wall_thickness"]
    rb = p["base_diameter"] / 2
    rl = p["lantern_diameter"] / 2

    if p["body_top_diameter"] > p["body_diameter"]:
        err("body_top_diameter", "Body top diameter must not exceed the body bottom diameter")
    if p["lantern_diameter"] > p["body_diameter"]:
        err("lantern_diameter", "Lantern diameter must not exceed the body diameter")
    elif p["lantern_diameter"] + 2 * GASKET_OVERHANG + 1 > p["body_top_diameter"]:
        err("lantern_diameter", "Lantern must be at least 2 mm narrower than the body top so its gasket sits on the LED plate")
    if p["top_cap_diameter"] / 2 - w < rl + GASKET_OVERHANG + 0.5:
        err("top_cap_diameter", "Top cap must be wide enough for the glass and its gasket to fit up inside it "
                                "(at least lantern diameter + 2 × wall + 2 mm)")
    if p["base_diameter"] < p["body_diameter"] + 10:
        err("base_diameter", "Base must be at least 10 mm wider than the body")
    if d["body_height"] < MIN_BODY_HEIGHT:
        err("overall_height",
            f"Body would be only {d['body_height']:.0f} mm tall; increase overall height or reduce base/lantern/cap heights "
            f"(minimum body height {MIN_BODY_HEIGHT:g} mm)")
    if 2 * (w + p["step_depth"]) >= p["body_top_diameter"] - 10:
        err("wall_thickness", "Wall thickness and step are too large for the body top diameter")
    if p["lantern_wall_thickness"] * 2 >= p["lantern_diameter"] - 10:
        err("lantern_wall_thickness", "Lantern wall is too thick for the lantern diameter")
    if p["top_cap_height"] <= w + GASKET_T + MIN_GLASS_IN_CAP:
        err("top_cap_height", f"Top cap must be taller than {w + GASKET_T + MIN_GLASS_IN_CAP:g} mm to hold the glass and gasket")
    elif d["glass_in_cap"] < MIN_GLASS_IN_CAP:
        err("top_cap_height", "The glass can't reach far enough up inside the cap; make the cap taller or wider")

    if d["body_height"] >= MIN_BODY_HEIGHT:
        band_centre = p["band_position"] * d["body_height"]
        if band_centre - p["band_height"] / 2 < 0 or band_centre + p["band_height"] / 2 > d["body_height"]:
            err("band_position", "Decorative band would extend beyond the body; move it or make it shorter")
        elif d["band_bottom_local_z"] < w + 2:
            err("band_position", "Band step is too close to the body foot")
    if p["step_depth"] >= p["band_wall_thickness"] + 3:
        warn("step_depth", "Step is much deeper than the band wall, so the body above the band looks recessed")

    # Lamp tube and central construction.
    if p["tube_diameter"] + 6 >= p["body_top_diameter"] / 2:
        err("tube_diameter", "Lamp tube is too large for the body")
    nut_r = p["tube_diameter"] * 0.8
    fo, _ = _cap_fillets(p)
    if p["top_cap_diameter"] / 2 - fo < nut_r + 1:
        err("top_cap_diameter", "Cap top is too small to seat the cap nut")

    # Base features: shell, weight plate, cable and dimmer.
    if p["base_height"] <= w + 2:
        err("base_height", "Base height must be more than the wall thickness + 2 mm")
    fb = _base_fillet(p)
    fi_b = fb - w if fb - w > 0.3 else 0.0
    if p["weight_plate_diameter"] / 2 > rb - w - fi_b - 0.5:
        err("weight_plate_diameter", "Weight plate must fit flat inside the base shell (diameter too large)")
    if p["weight_plate_diameter"] / 2 < p["mounting_hole_pcd"] / 2 + SCREW_CLEARANCE / 2 + 2:
        err("weight_plate_diameter", "Weight plate must reach past the rivet-nut screws (diameter too small for the pitch circle)")
    if d["tube_bottom_z"] < 1:
        err("weight_plate_thickness", "Base is too shallow for the weight plate plus the lamp nut and washer below it; "
                                      "make the base taller or the plate thinner")
    below = d["weight_plate_bottom_z"]
    if p["cable_hole_diameter"] + 2 > below:
        err("cable_hole_diameter", f"Cable hole must fit below the weight plate ({below:.1f} mm of space)")
    if 0 < p["dimmer_hole_diameter"] < 5:
        err("dimmer_hole_diameter", "Dimmer hole must be 0 (no in-base dimmer) or at least 5 mm")
    if p["dimmer_hole_diameter"] > 0 and POT_BODY_D + 1 > below:
        err("dimmer_hole_diameter", f"The rotary dimmer ({POT_BODY_D:g} mm body) must fit below the weight plate "
                                    f"({below:.1f} mm of space); make the base taller or the plate thinner")
    r_pcd = p["mounting_hole_pcd"] / 2
    r_h = p["mounting_hole_diameter"] / 2
    if r_pcd + r_h > p["body_diameter"] / 2 - w:
        err("mounting_hole_pcd", "Rivet nuts must sit inside the body footprint so they are hidden (pitch circle too large)")
    if r_pcd - r_h < d["central_hole_diameter"] / 2 + 6:
        err("mounting_hole_pcd", "Rivet nuts overlap the lamp tube and nut (pitch circle too small)")
    n = int(p["mounting_hole_count"])
    if n >= 2 and 2 * r_pcd * math.sin(math.pi / n) < 2 * r_h + 2:
        err("mounting_hole_count", "Rivet nuts are too close together on this pitch circle")

    # Process wall limits from the rules data.
    for part_key, param_key in (("main_body", "wall_thickness"), ("lantern", "lantern_wall_thickness")):
        lim = (wall_limits or {}).get(part_key)
        if lim is None:
            continue
        v = p[param_key]
        tag = "" if lim.verified else " (unverified rule data)"
        if not lim.min <= v <= lim.max:
            err(param_key, f"{PARAM_BY_KEY[param_key].label} {v:g} mm is outside the {lim.process_name} limit of "
                           f"{lim.min:g}–{lim.max:g} mm{tag}")
        elif not lim.typical_min <= v <= lim.typical_max:
            warn(param_key, f"{PARAM_BY_KEY[param_key].label} {v:g} mm is outside the typical {lim.process_name} range "
                            f"of {lim.typical_min:g}–{lim.typical_max:g} mm{tag}")

    if min_stability_ratio is not None:
        ratio = p["base_diameter"] / p["overall_height"]
        if ratio < min_stability_ratio:
            warn("base_diameter", f"Base diameter is {ratio:.0%} of overall height; below the {min_stability_ratio:.0%} "
                                  "stability heuristic. Check tip-over stability.")
    return res


def normalise(params: dict[str, Any]) -> dict[str, float | int]:
    out: dict[str, float | int] = {}
    for d in PARAMS:
        v = float(params[d.key])
        out[d.key] = int(v) if d.integer else v
    return out


def upgrade(params: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Parameters saved by an older generator: add new keys from the defaults, drop removed ones."""
    out = {k: v for k, v in params.items() if k in PARAM_BY_KEY}
    for k in PARAM_KEYS:
        if k not in out and k in defaults:
            out[k] = defaults[k]
    return out


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def _revolve(points: list[tuple[float, float]]) -> cq.Workplane:
    """Revolve an (r, z) profile 360° around the Z axis."""
    return cq.Workplane("XZ").polyline(points).close().revolve(360, (0, 0, 0), (0, 1, 0))


def _base_fillet(p: dict[str, float]) -> float:
    rb, bh = p["base_diameter"] / 2, p["base_height"]
    return max(min(bh * 0.4, 8.0, (rb - p["body_diameter"] / 2) * 0.8), 0.5)


def _ring(r_out: float, r_in: float, z0: float, h: float) -> cq.Workplane:
    return cq.Workplane("XY").circle(r_out).circle(r_in).extrude(h).translate((0, 0, z0))


def _hex_nut(af: float, hole_r: float, z0: float, h: float) -> cq.Workplane:
    across_corners = af / math.cos(math.pi / 6)
    return cq.Workplane("XY").polygon(6, across_corners).circle(hole_r).extrude(h).translate((0, 0, z0))


def build(params: dict[str, Any]) -> dict[str, cq.Workplane]:
    """Build one solid per part. Assumes `validate(params).ok`."""
    p = {k: float(v) for k, v in params.items()}
    d = derived(p)
    w = p["wall_thickness"]
    s = p["step_depth"]
    rb = p["base_diameter"] / 2
    bh = p["base_height"]
    r_bot = p["body_diameter"] / 2
    r_top = p["body_top_diameter"] / 2
    H = d["body_height"]
    z_top = d["body_top_z"]
    rl = p["lantern_diameter"] / 2
    lw = p["lantern_wall_thickness"]
    lh = p["lantern_height"]
    rc = p["top_cap_diameter"] / 2
    ch = p["top_cap_height"]
    rt = p["tube_diameter"] / 2
    bore_r = d["central_hole_diameter"] / 2
    wpt = p["weight_plate_thickness"]
    z_wp = d["weight_plate_bottom_z"]
    z_cable = d["cable_z"]

    parts: dict[str, cq.Workplane] = {}

    # Base: spun shell (inverted cup) with a cavity for the weight plate, central bore for the
    # lamp tube, rivet-nut holes (hidden under the body foot), cable hole and dimmer hole.
    fb = _base_fillet(p)
    fi_b = fb - w if fb - w > 0.3 else 0.0
    base = cq.Workplane("XY").circle(rb).extrude(bh).faces(">Z").edges().fillet(fb)
    cavity = cq.Workplane("XY").circle(rb - w).extrude(bh - w)
    if fi_b:
        cavity = cavity.faces(">Z").edges().fillet(fi_b)
    base = base.cut(cavity)
    n = int(p["mounting_hole_count"])
    r_pcd = p["mounting_hole_pcd"] / 2
    holes = (cq.Workplane("XY").polarArray(r_pcd, 0, 360, n).circle(p["mounting_hole_diameter"] / 2)
             .extrude(bh + 2).translate((0, 0, -1)))
    base = base.cut(holes)
    base = base.cut(cq.Workplane("XY").circle(bore_r).extrude(bh + 2).translate((0, 0, -1)))
    base = base.cut(cq.Workplane("YZ", origin=(0, 0, z_cable)).circle(p["cable_hole_diameter"] / 2).extrude(rb + 5))
    if p["dimmer_hole_diameter"] > 0:
        base = base.cut(cq.Workplane("YZ", origin=(-rb - 5, 0, z_cable)).circle(p["dimmer_hole_diameter"] / 2).extrude(rb + 5))
    parts["base"] = base

    # Main body: spun tapered shell with an upward-facing step at the bottom of the band.
    z1 = d["band_bottom_local_z"]
    zc = p["band_position"] * H
    z2 = zc + p["band_height"] / 2
    r_nom_top = r_top + s

    def r_n(z: float) -> float:  # lower section's taper line
        return r_bot + (r_nom_top - r_bot) * z / H

    body = _revolve([
        (r_bot, 0), (r_n(z1), z1), (r_n(z1) - s, z1), (r_top, H),
        (r_top - w, H), (r_n(z1 - w) - s - w, z1 - w), (r_n(z1 - w) - w, z1 - w), (r_bot - w, 0),
    ]).translate((0, 0, bh))
    parts["main_body"] = body

    # Decorative band: straight ring cut from stock tube, resting on the body step.
    r_in = d["band_inner_diameter"] / 2
    parts["band"] = _ring(r_in + p["band_wall_thickness"], r_in, bh + z1, z2 - z1)

    # Lantern: borosilicate glass tube from the lower gasket up inside the cap.
    parts["lantern"] = _ring(rl, rl - lw, d["glass_bottom_z"], d["glass_length"])
    g_out, g_in = rl + GASKET_OVERHANG, rl - lw - GASKET_OVERHANG
    parts["gasket_lower"] = _ring(g_out, g_in, d["plate_top_z"], GASKET_T)
    parts["gasket_upper"] = _ring(g_out, g_in, d["glass_top_z"], GASKET_T)

    # Top cap: spun domed shell with a centre hole for the lamp tube.
    fo, fi = _cap_fillets(p)
    cap = cq.Workplane("XY").circle(rc).extrude(ch)
    if fo > 0.3:
        cap = cap.faces(">Z").edges().fillet(fo)
    inner = cq.Workplane("XY").circle(rc - w).extrude(ch - w)
    if fi:
        inner = inner.faces(">Z").edges().fillet(fi)
    cap = cap.cut(inner).cut(cq.Workplane("XY").circle(bore_r).extrude(ch + 2).translate((0, 0, -1)))
    parts["top_cap"] = cap.translate((0, 0, d["cap_bottom_z"]))

    # Cap nut (finial): domed nut on top of the cap.
    nut_r = rt * 1.6
    cap_nut = cq.Workplane("XY").circle(nut_r).circle(rt).extrude(CAP_NUT_H * 0.45)
    dome = cq.Workplane("XY").circle(nut_r).extrude(CAP_NUT_H * 0.55).faces(">Z").edges().fillet(min(nut_r * 0.9, CAP_NUT_H * 0.55 - 0.5))
    cap_nut = cap_nut.union(dome.translate((0, 0, CAP_NUT_H * 0.45)))
    cap_nut = cap_nut.cut(cq.Workplane("XY").circle(rt).extrude(CAP_NUT_H - 3.0))
    parts["cap_nut"] = cap_nut.translate((0, 0, d["cap_top_z"]))

    # LED module and mounting: flanged LED plate on the body top, a threaded holder sleeve on
    # the tube (it clamps the plate) and a placeholder LED ring at mid-lantern.
    r_plate = r_top - w - 0.2
    plate = cq.Workplane("XY").circle(r_plate).extrude(LED_PLATE_THICKNESS).translate((0, 0, z_top - LED_PLATE_THICKNESS))
    plate = plate.union(cq.Workplane("XY").circle(r_top).extrude(PLATE_FLANGE).translate((0, 0, z_top)))
    plate = plate.cut(cq.Workplane("XY").circle(rt + 0.05).extrude(LED_PLATE_THICKNESS + PLATE_FLANGE + 2)
                      .translate((0, 0, z_top - LED_PLATE_THICKNESS - 1)))
    r_sleeve = rt + SLEEVE_WALL
    z_mid = d["plate_top_z"] + lh / 2
    puck_top = z_mid + LED_PUCK_HEIGHT / 2
    sleeve = _ring(r_sleeve, rt + 0.05, d["plate_top_z"], puck_top - d["plate_top_z"])
    puck = _ring(_puck_radius(rl, lw, rt), r_sleeve - 0.1, z_mid - LED_PUCK_HEIGHT / 2, LED_PUCK_HEIGHT)
    parts["led_module"] = plate.union(sleeve).union(puck)

    # Lamp tube: hollow threaded tube from below the lamp nut to inside the cap nut.
    parts["lamp_tube"] = _ring(rt, rt - 1.5, d["tube_bottom_z"], d["tube_top_z"] - d["tube_bottom_z"])

    # Lamp nut and washer under the weight plate.
    washer = _ring(rt * 2, rt + 0.25, z_wp - WASHER_T, WASHER_T)
    nut = _hex_nut(p["tube_diameter"] * 1.4, rt + 0.05, z_wp - WASHER_T - NUT_H, NUT_H)
    parts["lamp_nut"] = washer.union(nut)

    # Weight plate: steel disc against the underside of the base top.
    plate_w = cq.Workplane("XY").circle(p["weight_plate_diameter"] / 2).circle(bore_r).extrude(wpt).translate((0, 0, z_wp))
    screw_holes = (cq.Workplane("XY").polarArray(r_pcd, 0, 360, n).circle(SCREW_CLEARANCE / 2)
                   .extrude(wpt + 2).translate((0, 0, z_wp - 1)))
    parts["weight_plate"] = plate_w.cut(screw_holes)

    # Cable / power entry: grommet in the base side hole plus a short cable stub (+X side).
    rh = p["cable_hole_diameter"] / 2
    grommet = cq.Workplane("YZ", origin=(rb - w - 1, 0, z_cable)).circle(rh).extrude(w + 2)
    flange = cq.Workplane("YZ", origin=(rb + 1, 0, z_cable)).circle(min(rh + 2, z_cable)).extrude(3)
    cable_r = max(rh - 1.0, 1.0)
    stub = cq.Workplane("YZ", origin=(rb + 4, 0, z_cable)).circle(cable_r).extrude(60)
    parts["cable"] = grommet.union(flange).union(stub)

    # Dimmer: rotary potentiometer inside the skirt, bushing through the hole, solid metal knob (-X side).
    if p["dimmer_hole_diameter"] > 0:
        knob = cq.Workplane("YZ", origin=(-rb - 1 - KNOB_L, 0, z_cable)).circle(KNOB_D / 2).extrude(KNOB_L)
        bushing = cq.Workplane("YZ", origin=(-rb - 1, 0, z_cable)).circle(p["dimmer_hole_diameter"] / 2 - 0.25).extrude(w + 1)
        pot = cq.Workplane("YZ", origin=(-(rb - w), 0, z_cable)).circle(POT_BODY_D / 2).extrude(POT_DEPTH)
        parts["dimmer"] = knob.union(bushing).union(pot)
    else:
        # Touch or inline dimmer: a small touch-sensor board under the base top (placeholder).
        parts["dimmer"] = (cq.Workplane("XY").rect(30, 20).extrude(1.6)
                           .translate((-(rb - w) * 0.6, 0, z_wp - 6)))

    return {k: parts[k] for k in PART_KEYS}


def _arc(cx: float, cz: float, r: float, a0: float, a1: float, n: int = 12) -> list[tuple[float, float]]:
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def section_profiles(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Half-section outlines (r, z) of the made-to-drawing revolved parts, z from each part's bottom.

    Used for 2D quotation drawings; matches `build()` (fillets approximated by arcs).
    """
    p = {k: float(v) for k, v in params.items()}
    d = derived(p)
    w, s = p["wall_thickness"], p["step_depth"]
    rb, bh = p["base_diameter"] / 2, p["base_height"]
    bore = d["central_hole_diameter"] / 2
    out: dict[str, dict[str, Any]] = {}

    fb = _base_fillet(p)
    fi = fb - w if fb - w > 0.3 else 0.0
    base = [(rb - w, 0.0), (rb, 0.0), (rb, bh - fb)] + _arc(rb - fb, bh - fb, fb, 0, 90)[1:] + [(bore, bh), (bore, bh - w)]
    base += (_arc(rb - w - fi, bh - w - fi, fi, 90, 0)[:-1] if fi else [(rb - w, bh - w)]) + [(rb - w, bh - w - fi)]
    out["base"] = {"outline": base, "height": bh, "diameter": 2 * rb}

    H = d["body_height"]
    r_bot, r_top = p["body_diameter"] / 2, p["body_top_diameter"] / 2
    z1 = d["band_bottom_local_z"]
    r_nom_top = r_top + s
    r_n = lambda z: r_bot + (r_nom_top - r_bot) * z / H  # noqa: E731
    out["main_body"] = {"outline": [
        (r_bot - w, 0), (r_bot, 0), (r_n(z1), z1), (r_n(z1) - s, z1), (r_top, H), (r_top - w, H),
        (r_n(z1 - w) - s - w, z1 - w), (r_n(z1 - w) - w, z1 - w),
    ], "height": H, "diameter": 2 * r_bot, "step_z": z1}

    r_in = d["band_inner_diameter"] / 2
    bw, bhh = p["band_wall_thickness"], p["band_height"]
    out["band"] = {"outline": [(r_in, 0), (r_in + bw, 0), (r_in + bw, bhh), (r_in, bhh)], "height": bhh,
                   "diameter": 2 * (r_in + bw)}

    rl, lw = p["lantern_diameter"] / 2, p["lantern_wall_thickness"]
    L = d["glass_length"]
    out["lantern"] = {"outline": [(rl - lw, 0), (rl, 0), (rl, L), (rl - lw, L)], "height": L, "diameter": 2 * rl}

    rc, ch = p["top_cap_diameter"] / 2, p["top_cap_height"]
    fo, fi_c = _cap_fillets(p)
    cap = [(rc - w, 0.0), (rc, 0.0), (rc, ch - fo)] + _arc(rc - fo, ch - fo, fo, 0, 90)[1:] + [(bore, ch), (bore, ch - w)]
    cap += (_arc(rc - w - fi_c, ch - w - fi_c, fi_c, 90, 0)[:-1] if fi_c else [(rc - w, ch - w)]) + [(rc - w, ch - w - fi_c)]
    out["top_cap"] = {"outline": cap, "height": ch, "diameter": 2 * rc}

    wpr, wpt = p["weight_plate_diameter"] / 2, p["weight_plate_thickness"]
    out["weight_plate"] = {"outline": [(bore, 0), (wpr, 0), (wpr, wpt), (bore, wpt)], "height": wpt, "diameter": 2 * wpr}
    return out


def assembly(parts: dict[str, cq.Workplane], name: str = "faro") -> cq.Assembly:
    asm = cq.Assembly(name=name)
    for key, shape in parts.items():
        asm.add(shape, name=key, color=cq.Color(*PART_COLOURS.get(key, (0.7, 0.7, 0.7, 1.0))))
    return asm


def derived_traits(part_key: str, params: dict[str, Any]) -> list[str]:
    """Geometry traits implied by the current parameters, for the rules engine."""
    p = {k: float(v) for k, v in params.items()}
    tapered = p["body_top_diameter"] < p["body_diameter"] - 0.5
    if part_key == "main_body":
        return ["tapered"] if tapered else ["constant_section"]
    if part_key in ("band", "lantern"):
        return ["constant_section"]  # band is a straight ring cut from stock tube
    return []


def _puck_radius(lantern_r: float, lantern_wall: float, tube_r: float = 5.0) -> float:
    """Placeholder LED ring: up to 40 mm across, keeping ~10 mm from the lantern wall, around the tube sleeve."""
    return max(min(20.0, lantern_r - lantern_wall - 10.0), tube_r + SLEEVE_WALL + 3.0)


def led_clearance(params: dict[str, Any]) -> float:
    """Radial gap between the LED ring and the inside of the lantern wall (mm)."""
    p = {k: float(v) for k, v in params.items()}
    rl = p["lantern_diameter"] / 2
    lw = p["lantern_wall_thickness"]
    return rl - lw - _puck_radius(rl, lw, p.get("tube_diameter", 10.0) / 2)


def estimate_mass(part_info: dict[str, Any], densities: dict[str, float]) -> dict[str, Any]:
    """Lamp mass from CAD volumes (mm³) and densities (g/cm³) per part key."""
    per = {k: round(info["volume_mm3"] / 1000 * densities[k] / 1000, 3)
           for k, info in part_info.items() if k in densities}
    return {"total_kg": round(sum(per.values()), 3), "parts_kg": per}


def body_taper_deg(params: dict[str, Any]) -> float:
    p = {k: float(v) for k, v in params.items()}
    h = derived(p)["body_height"]
    return math.degrees(math.atan2((p["body_diameter"] - p["body_top_diameter"]) / 2, h))
