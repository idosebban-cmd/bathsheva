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
SEAT_DEPTH = 3.0  # recess in the top cap that locates the lantern
BAND_PROUD = 3.0  # how far the decorative band stands off the body surface
LED_PLATE_THICKNESS = 3.0
LED_PUCK_HEIGHT = 8.0
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
    ParamDef("overall_height", "Overall height", "Overall", 200, 900, help="Base underside to top of cap."),
    ParamDef("base_diameter", "Base diameter", "Base", 80, 400),
    ParamDef("base_height", "Base height", "Base", 10, 80),
    ParamDef("body_diameter", "Body diameter (bottom)", "Body", 50, 300),
    ParamDef("body_top_diameter", "Body diameter (top)", "Body", 40, 300,
             help="Smaller than the bottom gives the lighthouse taper; equal makes a straight tube."),
    ParamDef("wall_thickness", "Wall thickness (aluminium parts)", "Body", 0.5, 10, step=0.1),
    ParamDef("band_height", "Decorative band height", "Band", 5, 100),
    ParamDef("band_position", "Band position (fraction of body height)", "Band", 0.1, 0.9, step=0.01, unit="",
             help="0 = bottom of body, 1 = top."),
    ParamDef("lantern_height", "Lantern height", "Lantern", 20, 250),
    ParamDef("lantern_diameter", "Lantern diameter", "Lantern", 30, 300),
    ParamDef("lantern_wall_thickness", "Lantern wall thickness", "Lantern", 1, 8, step=0.1),
    ParamDef("top_cap_diameter", "Top cap diameter", "Top cap", 30, 320),
    ParamDef("top_cap_height", "Top cap height", "Top cap", 10, 150),
    ParamDef("cable_hole_diameter", "Cable hole diameter", "Cable & mounting", 3, 20, step=0.5),
    ParamDef("mounting_hole_count", "Mounting hole count", "Cable & mounting", 2, 8, integer=True),
    ParamDef("mounting_hole_diameter", "Mounting hole diameter", "Cable & mounting", 2, 10, step=0.1),
    ParamDef("mounting_hole_pcd", "Mounting hole pitch-circle diameter", "Cable & mounting", 20, 300,
             help="Diameter of the circle the mounting holes sit on."),
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
}
PART_KEYS = list(PART_COLOURS)


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


def derived(p: dict[str, float]) -> dict[str, float]:
    """Dimensions computed from parameters."""
    body_height = p["overall_height"] - p["base_height"] - p["lantern_height"] - p["top_cap_height"] + SEAT_DEPTH
    return {
        "body_height": body_height,
        "body_bottom_z": p["base_height"],
        "body_top_z": p["base_height"] + body_height,
        "central_hole_diameter": p["cable_hole_diameter"] + 4.0,
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

    if p["body_top_diameter"] > p["body_diameter"]:
        err("body_top_diameter", "Body top diameter must not exceed the body bottom diameter")
    if p["lantern_diameter"] > p["body_diameter"]:
        err("lantern_diameter", "Lantern diameter must not exceed the body diameter")
    elif p["lantern_diameter"] > p["body_top_diameter"]:
        err("lantern_diameter", "Lantern diameter must not exceed the body top diameter (it sits on top of the body)")
    if p["top_cap_diameter"] < p["lantern_diameter"] + 4:
        err("top_cap_diameter", "Top cap must be at least 4 mm wider than the lantern so it can cover and locate it")
    if p["base_diameter"] < p["body_diameter"] + 10:
        err("base_diameter", "Base must be at least 10 mm wider than the body")
    if d["body_height"] < MIN_BODY_HEIGHT:
        err("overall_height",
            f"Body would be only {d['body_height']:.0f} mm tall; increase overall height or reduce base/lantern/cap heights "
            f"(minimum body height {MIN_BODY_HEIGHT:g} mm)")
    if 2 * w >= p["body_top_diameter"] - 10:
        err("wall_thickness", "Wall thickness is too large for the body top diameter")
    if p["lantern_wall_thickness"] * 2 >= p["lantern_diameter"] - 10:
        err("lantern_wall_thickness", "Lantern wall is too thick for the lantern diameter")
    if p["top_cap_height"] <= SEAT_DEPTH + 2:
        err("top_cap_height", f"Top cap must be taller than {SEAT_DEPTH + 2:g} mm to hold the lantern seat")

    if d["body_height"] >= MIN_BODY_HEIGHT:
        band_centre = p["band_position"] * d["body_height"]
        if band_centre - p["band_height"] / 2 < 0 or band_centre + p["band_height"] / 2 > d["body_height"]:
            err("band_position", "Decorative band would extend beyond the body; move it or make it shorter")

    # Base features.
    if p["base_height"] <= w + 2:
        err("base_height", "Base height must be more than the wall thickness + 2 mm")
    cavity_h = p["base_height"] - w
    if p["cable_hole_diameter"] + 2 > cavity_h:
        err("cable_hole_diameter", f"Cable hole must be at least 2 mm smaller than the base cavity height ({cavity_h:.1f} mm)")
    r_pcd = p["mounting_hole_pcd"] / 2
    r_h = p["mounting_hole_diameter"] / 2
    if r_pcd + r_h > p["body_diameter"] / 2 - w:
        err("mounting_hole_pcd", "Mounting holes must sit inside the body footprint (pitch circle too large)")
    if r_pcd - r_h < d["central_hole_diameter"] / 2 + 2:
        err("mounting_hole_pcd", "Mounting holes overlap the central cable pass-through (pitch circle too small)")
    n = int(p["mounting_hole_count"])
    if n >= 2 and 2 * r_pcd * math.sin(math.pi / n) < 2 * r_h + 2:
        err("mounting_hole_count", "Mounting holes are too close together on this pitch circle")

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


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def _revolve(points: list[tuple[float, float]]) -> cq.Workplane:
    """Revolve an (r, z) profile 360° around the Z axis."""
    return cq.Workplane("XZ").polyline(points).close().revolve(360, (0, 0, 0), (0, 1, 0))


def build(params: dict[str, Any]) -> dict[str, cq.Workplane]:
    """Build one solid per part. Assumes `validate(params).ok`."""
    p = {k: float(v) for k, v in params.items()}
    d = derived(p)
    w = p["wall_thickness"]
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

    parts: dict[str, cq.Workplane] = {}

    # Base: disc with filleted top edge, hollow underneath, mounting holes,
    # central cable pass-through and a side cable hole.
    # Keep the fillet small enough not to break through into the hollow underside.
    fillet_r = min(bh * 0.4, 8.0, (rb - r_bot) * 0.8, 1.5 * w)
    base = cq.Workplane("XY").circle(rb).extrude(bh).faces(">Z").edges().fillet(fillet_r)
    base = base.cut(cq.Workplane("XY").circle(rb - w).extrude(bh - w))
    n = int(p["mounting_hole_count"])
    r_pcd = p["mounting_hole_pcd"] / 2
    holes = (
        cq.Workplane("XY")
        .polarArray(r_pcd, 0, 360, n)
        .circle(p["mounting_hole_diameter"] / 2)
        .extrude(bh + 2)
        .translate((0, 0, -1))
    )
    base = base.cut(holes)
    base = base.cut(cq.Workplane("XY").circle(d["central_hole_diameter"] / 2).extrude(bh + 2).translate((0, 0, -1)))
    z_cable = (bh - w) / 2
    side_hole = cq.Workplane("YZ", origin=(0, 0, z_cable)).circle(p["cable_hole_diameter"] / 2).extrude(rb + 5)
    base = base.cut(side_hole)
    parts["base"] = base

    # Main body: tapered thin-walled tube (open both ends).
    body = _revolve([(r_bot, 0), (r_top, H), (r_top - w, H), (r_bot - w, 0)]).translate((0, 0, bh))
    parts["main_body"] = body

    # Decorative band: ring whose inner face follows the body taper.
    def r_at(z_local: float) -> float:
        return r_bot + (r_top - r_bot) * z_local / H

    zc = p["band_position"] * H
    z1, z2 = zc - p["band_height"] / 2, zc + p["band_height"] / 2
    r1, r2 = r_at(z1), r_at(z2)
    band = _revolve([(r1, z1), (r1 + BAND_PROUD, z1), (r1 + BAND_PROUD, z2), (r2, z2)]).translate((0, 0, bh))
    parts["band"] = band

    # Lantern: transparent tube sitting on the body top.
    lantern = cq.Workplane("XY").circle(rl).circle(rl - lw).extrude(lh).translate((0, 0, z_top))
    parts["lantern"] = lantern

    # Top cap: domed cap with a recess that locates the lantern.
    z_cap = z_top + lh - SEAT_DEPTH
    dome_r = min(ch - SEAT_DEPTH - 1, rc - 1, max(rc, ch) * 0.8)
    cap = cq.Workplane("XY").circle(rc).extrude(ch).faces(">Z").edges().fillet(dome_r)
    cap = cap.cut(cq.Workplane("XY").circle(rl + 0.5).extrude(SEAT_DEPTH))
    parts["top_cap"] = cap.translate((0, 0, z_cap))

    # LED module and mounting: plate closing the body top, a stem, and an LED puck.
    r_plate = r_top - w - 0.2
    plate = cq.Workplane("XY").circle(r_plate).extrude(LED_PLATE_THICKNESS).translate((0, 0, z_top - LED_PLATE_THICKNESS))
    stem_h = max(lh * 0.5 - LED_PUCK_HEIGHT / 2, 2.0)
    stem = cq.Workplane("XY").circle(min(6.0, r_plate * 0.5)).extrude(stem_h).translate((0, 0, z_top))
    puck_r = _puck_radius(rl, lw)
    puck = cq.Workplane("XY").circle(puck_r).extrude(LED_PUCK_HEIGHT).translate((0, 0, z_top + stem_h))
    parts["led_module"] = plate.union(stem).union(puck)

    # Cable / power entry: grommet in the base side hole plus a short cable stub.
    rh = p["cable_hole_diameter"] / 2
    grommet = cq.Workplane("YZ", origin=(rb - w - 1, 0, z_cable)).circle(rh).extrude(w + 2)
    flange = cq.Workplane("YZ", origin=(rb, 0, z_cable)).circle(min(rh + 2, z_cable)).extrude(3)
    cable_r = max(rh - 1.0, 1.0)
    stub = cq.Workplane("YZ", origin=(rb + 3, 0, z_cable)).circle(cable_r).extrude(60)
    parts["cable"] = grommet.union(flange).union(stub)

    return parts


def assembly(parts: dict[str, cq.Workplane], name: str = "faro") -> cq.Assembly:
    asm = cq.Assembly(name=name)
    for key, shape in parts.items():
        asm.add(shape, name=key, color=cq.Color(*PART_COLOURS.get(key, (0.7, 0.7, 0.7, 1.0))))
    return asm


def derived_traits(part_key: str, params: dict[str, Any]) -> list[str]:
    """Geometry traits implied by the current parameters, for the rules engine."""
    p = {k: float(v) for k, v in params.items()}
    tapered = p["body_top_diameter"] < p["body_diameter"] - 0.5
    if part_key in ("main_body", "band"):
        return ["tapered"] if tapered else ["constant_section"]
    if part_key == "lantern":
        return ["constant_section"]
    return []


def _puck_radius(lantern_r: float, lantern_wall: float) -> float:
    """Placeholder LED puck: up to 40 mm across, keeping ~10 mm from the lantern wall."""
    return max(min(20.0, lantern_r - lantern_wall - 10.0), 5.0)


def led_clearance(params: dict[str, Any]) -> float:
    """Radial gap between the LED puck and the inside of the lantern wall (mm)."""
    p = {k: float(v) for k, v in params.items()}
    rl = p["lantern_diameter"] / 2
    lw = p["lantern_wall_thickness"]
    return rl - lw - _puck_radius(rl, lw)


def body_taper_deg(params: dict[str, Any]) -> float:
    p = {k: float(v) for k, v in params.items()}
    h = derived(p)["body_height"]
    return math.degrees(math.atan2((p["body_diameter"] - p["body_top_diameter"]) / 2, h))
