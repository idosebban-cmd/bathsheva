"""Faro parametric model (build123d): parameter definitions, validation and geometry.

The form, proportions and features are ported from the approved prototype model
(branch claude/rocket-speaker-3d-model-xav3pn, faro/lamp.py and faro/params.py):
black base with a brass nameplate, cream band, cream tower with a red lower
section and five arched windows spiralling up it, brass gallery with a railing,
brass-framed frosted lantern, red domed cap with a twist-lock (bayonet) fit and a
brass ball finial. Cordless: 2 x 18650 cells in the base, USB-C on the rear.

Production adaptations (see PRODUCTION_CHANGES): spun aluminium shells with a
real wall, an opal borosilicate diffuser tube behind the windows and a tower
light, a frosted borosilicate lantern tube in a brass frame, a photo-etched
railing, a turned brass bayonet spigot in the cap and a laser-cut steel weight
plate around the battery.

Coordinate system: Z up, origin at the centre of the base underside (the felt
pad stands below it), front faces -Y, units mm. One solid per part; keys match
Part.cad_key.
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from build123d import (
    Align,
    Axis,
    Box,
    Circle,
    Color,
    Compound,
    Cylinder,
    Edge,
    Face,
    GeomType,
    Plane,
    Polygon,
    Pos,
    Rectangle,
    RectangleRounded,
    Rot,
    Shape,
    SlotOverall,
    Sphere,
    Vector,
    Wire,
    extrude,
    fillet,
    offset,
    revolve,
)

GENERATOR = "faro"
MIN = (Align.CENTER, Align.CENTER, Align.MIN)

# ---------------------------------------------------------------------------
# Fixed construction constants (not user parameters). From the prototype unless noted.
# ---------------------------------------------------------------------------
FELT_T = 1.5  # self-adhesive felt...
FELT_BACKING = 0.4  # ...laminated to a steel disc that the magnets hold
FELT_INSET = 3.0
BOTTOM_PLATE_T = 2.0  # laser-cut aluminium bottom plate (production; prototype 3 mm printed)
PLATE_CLEAR = 0.2
BATTERY = (70.0, 38.0, 19.5)  # pre-certified 2 x 18650 pack lying flat, incl. protection board and wrap
BATTERY_Y = -4.0
USBC_W, USBC_H = 8.94 + 0.7, 3.26 + 0.7  # receptacle opening + clearance
USBC_Z = 11.0  # low on the rear (+Y) of the base
WIRE_HOLE_D = 20.0  # base top: tower-light spine and wiring
BAND_WIDTH = 8.0  # cream band: radial width of the ring
BAND_ROUND = 1.0
BAND_SCREWS = 3  # M3 from below: weight plate + base top -> tapped holes in the band
BAND_SCREW_CLEAR = 3.4
BAND_SCREW_HEAD = 5.5
TOWER_SPIGOT_H = 2.0  # locating spigot on the band, inside the tower foot
GALLERY_SPIGOT_H = 4.0  # spigot under the gallery, inside the tower top
STANDOFFS = 4  # M2.5 hex standoffs: bottom plate -> weight plate
STANDOFF_R = 40.0
STANDOFF_ANGLE0 = 45.0
STANDOFF_HEX = 5.0
SCREW_CS_D, SCREW_CLEAR_D = 4.7, 2.9  # M2.5 countersunk
MAGNETS = 4
MAGNET_D, MAGNET_T = 6.0, 2.0
NAMEPLATE_W, NAMEPLATE_H = 37.0, 11.5
NAMEPLATE_T = 0.8  # etched brass, bonded on the surface (prototype: 1.2 mm in a 0.6 mm recess)
NAMEPLATE_Z = 14.0
KNOB_PROUD = 6.0
KNOB_GAP = 0.5
POT_D, POT_DEPTH = 12.0, 9.0  # slim 9 mm-class rotary pot behind the tower wall
POT_HOLE_D = 7.5  # M7 bushing
POT_STANDOFF = 1.5  # curved spacer washer between the conical wall and the pot face
GALLERY_ROUND = 1.0
GALLERY_SHEET = 1.0  # spun brass gallery shell
GALLERY_BORE_INSET = 4.0  # gallery bore radius = lantern radius - this
LEDGE_BORE = 34.0
LEDGE_T = 1.6
RAIL_T = 0.6  # photo-etched brass sheet
RAIL_POST_W = 1.6
RAIL_BAR_H = 1.6
RAIL_FOOT_H = 1.2  # etched strip's bottom band, soldered to the gallery
RAIL_MID_FRAC = 0.5
RAIL_INSET = 1.0  # railing outer face inside the gallery edge
LANTERN_RING_H = 2.5
TOP_BAND_H = 6.0
LIP_H = 2.5
MULLION_W = 2.2
MULLION_DEPTH = 2.2
LOCK_LUGS = 4
LOCK_LUG_W = 6.0
LOCK_LUG_H = 2.6
LOCK_TURN_DEG = -20.0  # clockwise seen from above
SPIGOT_WALL = 1.5
FIT_CLEAR = 0.2
CAP_FILLET = 2.0
CAP_BOSS_H = 4.5
FINIAL_STUD_D = 4.0  # M4 stud through the cap; nut inside
LED_BOARD_D = 38.0  # LED board on an aluminium spreader, resting on the gallery ledge
LED_H = 5.0
LED_EMITTER_D = 20.0
SPINE_D = 10.0  # tower-light spine
FILAMENTS = 4
FILAMENT_D = 2.5
DIFFUSER_WALL = 2.0
DIFFUSER_TOP_GAP = 7.0  # diffuser top below the tower top (gallery spigot + silicone ring)
DIFFUSER_RING = 1.5  # silicone ring that centres the diffuser top in the tower
DIFFUSER_OVERLAP = 5.0  # diffuser runs this far past the lowest and highest window
SPIDER_T = 1.5  # spider on the tower-light spine that carries the diffuser
MIN_TOWER_HEIGHT = 60.0


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
    ParamDef("overall_height", "Overall height", "Overall", 200, 600,
             help="Base underside to the top of the finial ball (the felt pad adds 1.9 mm below)."),
    ParamDef("target_mass_kg", "Target total lamp mass", "Overall", 0.3, 10, step=0.1, unit="kg",
             help="Checks that the weight plate gives the lamp a solid, planted feel."),
    ParamDef("base_diameter", "Base diameter", "Base", 70, 250),
    ParamDef("base_height", "Base height", "Base", 18, 60),
    ParamDef("base_top_round", "Base top edge radius", "Base", 1, 15, step=0.5,
             help="Generous rounding on the base's top edge (spun)."),
    ParamDef("weight_plate_thickness", "Weight plate thickness", "Base", 2, 20, step=0.5,
             help="Laser-cut steel plate inside the base, around the battery."),
    ParamDef("band_diameter", "Cream band diameter", "Bands", 60, 240),
    ParamDef("band_height", "Cream band height", "Bands", 2, 20, step=0.5),
    ParamDef("red_section_height", "Red lower section height", "Bands", 0, 150,
             help="Red lacquer on the lower tower, masked line above it (two-tone). 0 = all cream."),
    ParamDef("tower_bottom_diameter", "Tower diameter (bottom)", "Tower", 50, 220),
    ParamDef("tower_top_diameter", "Tower diameter (top)", "Tower", 40, 220,
             help="Smaller than the bottom gives the lighthouse taper."),
    ParamDef("wall_thickness", "Wall thickness (spun aluminium shells)", "Tower", 0.5, 3, step=0.1,
             help="Base, tower and cap are spun aluminium."),
    ParamDef("window_count", "Tower windows", "Windows", 0, 8, unit="", integer=True,
             help="Arched windows spiralling up the tower; 0 = none."),
    ParamDef("window_width", "Window width", "Windows", 5, 30, step=0.1),
    ParamDef("window_height", "Window height (incl. arch)", "Windows", 8, 50, step=0.5),
    ParamDef("window_first_z", "Lowest window centre height", "Windows", 40, 500,
             help="Above the base underside (front window)."),
    ParamDef("window_last_z", "Highest window centre height", "Windows", 40, 550),
    ParamDef("window_turn_deg", "Turn between windows", "Windows", -180, 180, unit="°",
             help="Positive spirals towards the right side; 90 with 5 windows puts the first and last on the front."),
    ParamDef("knob_diameter", "Dimmer knob diameter", "Dimmer", 10, 30, step=0.5),
    ParamDef("knob_z", "Dimmer knob centre height", "Dimmer", 30, 300,
             help="On the front of the red section."),
    ParamDef("gallery_diameter", "Gallery diameter", "Gallery", 50, 250),
    ParamDef("gallery_height", "Gallery ring height", "Gallery", 4, 30, step=0.1),
    ParamDef("railing_height", "Railing height", "Gallery", 6, 30, step=0.5),
    ParamDef("railing_posts", "Railing posts", "Gallery", 8, 32, unit="", integer=True),
    ParamDef("lantern_diameter", "Lantern diameter (frame)", "Lantern", 35, 200),
    ParamDef("lantern_height", "Lantern height", "Lantern", 20, 150, step=0.1,
             help="Gallery top to the top of the lantern's brass top band."),
    ParamDef("lantern_mullions", "Lantern mullions", "Lantern", 4, 16, unit="", integer=True),
    ParamDef("glass_wall_thickness", "Lantern glass wall", "Lantern", 1, 6, step=0.1,
             help="Frosted borosilicate tube; stock walls are about 1.8–2.5 mm at this size."),
    ParamDef("cap_rim_diameter", "Cap rim diameter", "Cap", 40, 260),
    ParamDef("cap_rim_height", "Cap rim height", "Cap", 3, 20, step=0.5),
    ParamDef("cap_dome_diameter", "Cap dome diameter", "Cap", 30, 240, step=0.5),
    ParamDef("cap_height", "Cap height (rim to dome top)", "Cap", 15, 100),
    ParamDef("finial_diameter", "Finial ball diameter", "Cap", 8, 30),
    ParamDef("finial_height", "Finial height (dome top to ball top)", "Cap", 8, 40),
]
PARAM_KEYS = [p.key for p in PARAMS]
PARAM_BY_KEY = {p.key: p for p in PARAMS}

# Colours for the STEP/GLB export (sRGB, alpha). The 3D preview maps these parts to
# PBR materials by name (frontend ModelViewer).
RED, CREAM, BLACK, BRASS = (0.541, 0.110, 0.082, 1.0), (0.976, 0.949, 0.882, 1.0), (0.07, 0.07, 0.07, 1.0), (0.769, 0.631, 0.353, 1.0)
PART_COLOURS: dict[str, tuple[float, float, float, float]] = {
    "base": BLACK,
    "base_plate": (0.15, 0.15, 0.15, 1.0),
    "felt_pad": (0.18, 0.18, 0.17, 1.0),
    "weight_plate": (0.45, 0.47, 0.50, 1.0),
    "nameplate": BRASS,
    "band_cream": CREAM,
    "tower": CREAM,
    "diffuser": (0.97, 0.96, 0.93, 0.85),
    "tower_light": (0.75, 0.75, 0.78, 1.0),
    "dimmer": (0.25, 0.25, 0.27, 1.0),
    "knob": BRASS,
    "gallery": BRASS,
    "railing": BRASS,
    "lantern_frame": BRASS,
    "lantern_glass": (0.96, 0.95, 0.92, 0.75),
    "led_module": (0.85, 0.85, 0.85, 1.0),
    "cap": RED,
    "cap_spigot": BRASS,
    "finial": BRASS,
    "battery": (0.20, 0.35, 0.55, 1.0),
    "charge_board": (0.10, 0.40, 0.20, 1.0),
}
PART_KEYS = list(PART_COLOURS)


NAMEPLATE_FILL = (0.05, 0.05, 0.05, 1.0)


def preview_extras(params: dict[str, Any]) -> dict[str, tuple[Shape, tuple]]:
    """Preview-only bodies for the GLB: the black fill in the nameplate's lettering and the knob logo."""
    m = model(params)
    return {k: (m.preview[k], NAMEPLATE_FILL) for k in ("nameplate_fill", "knob_logo_fill") if k in m.preview}


def preview_two_tone(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The tower's red lower section is the same part lacquered in two colours (masked line)."""
    p = {k: float(v) for k, v in params.items()}
    if p.get("red_section_height", 0) <= 0:
        return {}
    return {"tower": {"lower": RED, "upper": CREAM, "split_z": derived(p)["red_top_z"]}}


# Where the production design departs from the 3D-printed prototype, and why. Shown
# in the CAD tab and the factory pack so nothing changes silently.
PRODUCTION_CHANGES: list[dict[str, str]] = [
    {"feature": "Shell walls", "prototype": "Printed, 2.5 mm tower wall; solid printed cap and base",
     "production": "Spun aluminium base, tower and cap with a real wall (default 1.5 mm, typical spinning 1.0–2.0 mm)"},
    {"feature": "Red lower tower", "prototype": "Separate printed red band glued under the tower",
     "production": "One spun cone lacquered in two colours with a masked line; removes a joint"},
    {"feature": "Window diffusers", "prototype": "Five frosted resin inserts, numbered, glued behind the windows",
     "production": "One opal borosilicate tube inside the tower behind all five windows (glass, no plastic on view); "
                   "no numbering needed. It covers only the window zone (5 mm past the lowest and highest window) and "
                   "stands on a spider on the tower-light spine, so it is about half the full tower height"},
    {"feature": "Window glow", "prototype": "Fairy lights coiled in the tower",
     "production": "Tower light: LED filament strips on a central spine inside the diffuser tube (bought-in)"},
    {"feature": "Windows", "prototype": "Printed openings",
     "production": "Laser-cut after spinning (5-axis laser or fixture); adds a process and a fixture"},
    {"feature": "Railing", "prototype": "Printed 1.6 mm round posts and rails",
     "production": "Photo-etched brass strip (0.6 mm) rolled into a ring and soldered; flat posts read the same at "
                   "arm's length. Alternatives: soldered brass wire, or lost-wax cast"},
    {"feature": "Gallery", "prototype": "Printed solid ring",
     "production": "Spun brass shell, 1.0 mm (flat top that is also the LED ledge, outer skirt, open underneath) "
                   "with a turned brass locating ring soldered under it; same look from above and the side, far less "
                   "brass than a solid turned ring"},
    {"feature": "Lantern frame", "prototype": "One printed frame with the bayonet lip",
     "production": "Brass bottom ring and top band turned from tube (bayonet slots and lip machined) with brass "
                   "mullion bars soldered or brazed between them"},
    {"feature": "Small turned parts", "prototype": "Printed",
     "production": "Cream band, cap spigot, finial and knob turned from near-net stock (tube, ring blanks or "
                   "close-fitting bar) rather than solid bar, to cut material and cycle time"},
    {"feature": "Lantern glass", "prototype": "Printed/frosted 1.2 mm ring",
     "production": "Frosted (acid-etched) borosilicate tube, 2.0 mm wall (1.2 mm is thinner than stock tube)"},
    {"feature": "Cap twist-lock", "prototype": "Lugs printed on a spigot under the cap",
     "production": "Lugs can't be spun: a turned brass spigot ring with the 4 lugs, bonded inside the spun cap"},
    {"feature": "Cap collar", "prototype": "Printed red collar on the dome",
     "production": "Spun into the cap as a small neck (verify with the spinner); fallback: separate turned "
                   "aluminium collar lacquered red"},
    {"feature": "Nameplate", "prototype": "1.2 mm plate in a 0.6 mm recess, raised lettering",
     "production": "0.8 mm etched brass plate bonded on the surface (a recess can't be spun); lettering etched"},
    {"feature": "Base fixing", "prototype": "Glued plate, coins for weight",
     "production": "Laser-cut steel weight plate screwed up into the cream band; aluminium bottom plate on 4 M2.5 "
                   "screws into standoffs so the battery is user-replaceable; felt on a steel disc held by magnets"},
    {"feature": "Knob logo", "prototype": "Plain knob face",
     "production": "Logo (half sun with seven rays over two waves) engraved 0.2 mm into the brass knob face and filled "
                   "black: medallion Ø16 mm with a rim groove, 0.4 mm grooves; upright with the knob at its off stop"},
    {"feature": "Battery bay", "prototype": "Sized for the bare cells (65 × 37 × 19 mm)",
     "production": "Sized for a pre-certified 2 x 18650 pack with its protection board and wrap: 70 × 38 × 19.5 mm; "
                   "weight plate cut-out enlarged to match"},
    {"feature": "Construction", "prototype": "Stacked and glued",
     "production": "No central rod: band screwed to the base through the weight plate, tower and gallery bonded on "
                   "turned spigots, cap twist-locks onto the lantern"},
]

# Design changes from seed/cost/route_changes.yaml that this generator already shows,
# and the bodies that prove a generated model has them.
IMPLEMENTED_CHANGES: dict[str, set[str]] = {
    "thin_shell_needs_mass": {"weight_plate"},  # spun base shell with a steel weight plate
    "thin_wall_inserts": {"weight_plate", "band_cream"},  # screws go into the turned band, not the thin shell
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


# ---------------------------------------------------------------------------
# Derived dimensions
# ---------------------------------------------------------------------------


def windows(p: dict[str, float]) -> list[tuple[float, float]]:
    """(centre height, angle from the front in degrees) per window, lowest first."""
    n = int(p["window_count"])
    out = []
    for i in range(n):
        f = i / (n - 1) if n > 1 else 0.0
        out.append((p["window_first_z"] + f * (p["window_last_z"] - p["window_first_z"]), i * p["window_turn_deg"]))
    return out


def derived(p: dict[str, float]) -> dict[str, Any]:
    """Dimensions computed from parameters (z from the base underside)."""
    hb, w = p["base_height"], p["wall_thickness"]
    tower_bottom = hb + p["band_height"]
    tower_top = p["overall_height"] - p["finial_height"] - p["cap_height"] - p["lantern_height"] - p["gallery_height"]
    tower_h = tower_top - tower_bottom
    r0, r1 = p["tower_bottom_diameter"] / 2, p["tower_top_diameter"] / 2
    gallery_top = tower_top + p["gallery_height"]
    lantern_top = gallery_top + p["lantern_height"]
    rl = p["lantern_diameter"] / 2
    glass_r = rl - MULLION_DEPTH - 0.1
    r_lip = rl - 3.0
    diffuser_max_top = tower_top - DIFFUSER_TOP_GAP
    wins = windows(p)
    if wins:  # the diffuser only needs to sit behind the window zone
        diffuser_bottom = max(wins[0][0] - p["window_height"] / 2 - DIFFUSER_OVERLAP, hb + 1.0)
        diffuser_top = min(max(z for z, _ in wins) + p["window_height"] / 2 + DIFFUSER_OVERLAP, diffuser_max_top)
    else:
        diffuser_bottom, diffuser_top = hb + 1.0, diffuser_max_top

    def r_out(z: float) -> float:
        return r0 + (r1 - r0) * (z - tower_bottom) / tower_h if tower_h > 0 else r0

    diffuser_r = math.floor((r_out(diffuser_top) - w - DIFFUSER_RING) * 2) / 2  # to 0.5 mm
    wp_top = hb - w
    rb = p["base_diameter"] / 2
    return {
        "felt_bottom_z": -(FELT_T + FELT_BACKING),
        "height_on_felt": p["overall_height"] + FELT_T + FELT_BACKING,
        "tower_bottom_z": tower_bottom,
        "tower_top_z": tower_top,
        "tower_height": tower_h,
        "red_top_z": tower_bottom + p["red_section_height"],
        "gallery_top_z": gallery_top,
        "lantern_top_z": lantern_top,
        "lantern_band_bottom_z": lantern_top - TOP_BAND_H,
        "cap_bottom_z": lantern_top,
        "cap_top_z": lantern_top + p["cap_height"],
        "glass_od": 2 * glass_r,
        "glass_height": lantern_top - TOP_BAND_H - gallery_top,
        "glass_inner_r": glass_r - p["glass_wall_thickness"],
        "lip_r": r_lip,
        "led_access_dia": 2 * (r_lip - FIT_CLEAR - SPIGOT_WALL),
        "gallery_bore_r": rl - GALLERY_BORE_INSET,
        "diffuser_od": 2 * diffuser_r,
        "diffuser_bottom_z": diffuser_bottom,  # on a spider on the tower-light spine
        "diffuser_top_z": diffuser_top,
        "diffuser_max_top_z": diffuser_max_top,
        "diffuser_length": diffuser_top - diffuser_bottom,
        "weight_plate_diameter": 2 * (rb - p["base_top_round"] - 0.5),
        "weight_plate_top_z": wp_top,
        "weight_plate_bottom_z": wp_top - p["weight_plate_thickness"],
        "base_inner_height": hb - w - BOTTOM_PLATE_T,
        "band_screw_pcd": p["band_diameter"] - BAND_WIDTH,
        "tower_taper_deg": math.degrees(math.atan2(r0 - r1, tower_h)) if tower_h > 0 else 0.0,
        "windows": [(round(z, 1), a % 360) for z, a in windows(p)],
        "r_out": r_out,
    }


def _public_derived(d: dict[str, Any]) -> dict[str, Any]:
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items() if not callable(v)}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _coerce(params: dict[str, Any], res: ValidationResult) -> dict[str, float]:
    p: dict[str, float] = {}
    for d in PARAMS:
        if d.key not in params or params[d.key] is None:
            res.errors.append(ValidationIssue(d.key, f"{d.label} is required"))
            continue
        try:
            v = float(params[d.key])
        except (TypeError, ValueError):
            res.errors.append(ValidationIssue(d.key, f"{d.label} must be a number"))
            continue
        if math.isnan(v) or math.isinf(v):
            res.errors.append(ValidationIssue(d.key, f"{d.label} must be a finite number"))
            continue
        if d.integer and v != int(v):
            res.errors.append(ValidationIssue(d.key, f"{d.label} must be a whole number"))
            continue
        if not d.min <= v <= d.max:
            res.errors.append(ValidationIssue(d.key, f"{d.label} must be between {d.min:g} and {d.max:g} {d.unit}".rstrip()))
            continue
        p[d.key] = v
    for k in sorted(set(params) - set(PARAM_KEYS)):
        res.errors.append(ValidationIssue(k, f"Unknown parameter {k!r}"))
    return p


def validate(
    params: dict[str, Any],
    wall_limits: dict[str, WallLimit] | None = None,
    min_stability_ratio: float | None = None,
) -> ValidationResult:
    """Validate ranges and inter-dependencies before regeneration.

    wall_limits maps part key ("tower", "lantern_glass", ...) to the process wall
    limits; outside min/max is an error, outside the typical range a warning.
    """
    res = ValidationResult()
    err = lambda param, msg: res.errors.append(ValidationIssue(param, msg))  # noqa: E731
    warn = lambda param, msg: res.warnings.append(ValidationIssue(param, msg, "warning"))  # noqa: E731
    p = _coerce(params, res)
    if len(p) != len(PARAMS) or res.errors:
        return res

    d = derived(p)
    w = p["wall_thickness"]
    rb = p["base_diameter"] / 2
    rl = p["lantern_diameter"] / 2
    r_out = d["r_out"]

    # Stack and proportions.
    if d["tower_height"] < MIN_TOWER_HEIGHT:
        err("overall_height", f"The tower would be only {d['tower_height']:.0f} mm tall (minimum {MIN_TOWER_HEIGHT:g} mm); "
                              "increase the overall height or reduce the lantern, cap or finial")
    if p["tower_top_diameter"] > p["tower_bottom_diameter"]:
        err("tower_top_diameter", "Tower top diameter must not exceed the bottom diameter")
    if p["band_diameter"] < p["tower_bottom_diameter"] + 2:
        err("band_diameter", "The cream band must be at least 2 mm wider than the tower foot so it shows")
    if p["band_diameter"] / 2 > rb - p["base_top_round"]:
        err("band_diameter", "The cream band must sit on the flat top of the base (inside the rounded edge)")
    if p["band_diameter"] / 2 - BAND_WIDTH > p["tower_bottom_diameter"] / 2 - w - 3:
        err("band_diameter", "The cream band ring is too wide for the tower to sit on it")
    if p["red_section_height"] > d["tower_height"] - 10:
        err("red_section_height", "The red section must end at least 10 mm below the tower top")
    if p["gallery_diameter"] < p["tower_top_diameter"] + 10:
        err("gallery_diameter", "The gallery must overhang the tower top by at least 5 mm all round")
    if p["gallery_diameter"] < p["lantern_diameter"] + 10:
        err("gallery_diameter", "The gallery must be at least 10 mm wider than the lantern (room for the railing)")
    if d["gallery_bore_r"] < LEDGE_BORE / 2 + 2:
        err("lantern_diameter", "Lantern is too narrow for the LED ledge inside the gallery")
    if r_out(d["tower_top_z"]) - w - 0.1 - 1.5 < d["gallery_bore_r"] + 0.5:
        err("lantern_diameter", "The gallery's spigot can't fit inside the tower top; make the tower top wider or the "
                                "lantern narrower")
    if p["lantern_height"] < LANTERN_RING_H + TOP_BAND_H + 10:
        err("lantern_height", f"Lantern must be at least {LANTERN_RING_H + TOP_BAND_H + 10:g} mm tall (brass rings plus glass)")
    if d["glass_inner_r"] < d["gallery_bore_r"] - 1:
        err("glass_wall_thickness", "Lantern glass wall is too thick: the glass must stand on the gallery top, outside the bore")
    if d["led_access_dia"] < LED_BOARD_D + 1:
        err("lantern_diameter", f"With the cap off the opening ({d['led_access_dia']:.0f} mm) must let the "
                                f"{LED_BOARD_D:g} mm LED board lift out")
    if p["railing_height"] < 2 * RAIL_BAR_H + RAIL_FOOT_H + 2:
        err("railing_height", "Railing is too low for its rails")

    # Cap.
    if p["cap_rim_diameter"] < p["lantern_diameter"] + 4:
        err("cap_rim_diameter", "Cap rim must overhang the lantern by at least 2 mm all round")
    if p["cap_dome_diameter"] > p["cap_rim_diameter"] - 2 * CAP_FILLET:
        err("cap_dome_diameter", "Cap dome must be narrower than the rim (by twice the rim radius)")
    if p["cap_dome_diameter"] / 2 - w < d["lip_r"] - FIT_CLEAR + 1:
        err("cap_dome_diameter", "Cap dome is too narrow for the bayonet spigot inside it")
    if p["cap_dome_diameter"] < p["finial_diameter"] + 8:
        err("cap_dome_diameter", "Cap dome is too small for the finial collar")
    if p["cap_height"] < p["cap_rim_height"] + 8:
        err("cap_height", "Cap must be at least 8 mm taller than its rim (room for the dome)")
    if p["cap_rim_height"] < 2 * CAP_FILLET + 0.5:
        err("cap_rim_height", f"Cap rim must be at least {2 * CAP_FILLET + 0.5:g} mm tall for its rounded edges")
    if p["finial_height"] < CAP_BOSS_H + p["finial_diameter"] * 0.6:
        err("finial_height", "Finial height must clear the collar and most of the ball")

    # Windows, diffuser, dimmer.
    wins = windows(p)
    if wins:
        if p["window_last_z"] < p["window_first_z"]:
            err("window_last_z", "Highest window must not be below the lowest")
        lo = p["window_first_z"] - p["window_height"] / 2
        hi = max(z for z, _ in wins) + p["window_height"] / 2
        if lo < d["red_top_z"] + 3 and p["red_section_height"] > 0:
            warn("window_first_z", "The lowest window cuts into the red section")
        if lo < d["tower_bottom_z"] + 5:
            err("window_first_z", "Windows must start at least 5 mm above the tower foot")
        if hi > d["diffuser_max_top_z"] - 2:
            err("window_last_z", "The highest window must sit below the diffuser top (8 mm under the tower top)")
        if p["window_width"] < 6 or p["window_width"] >= p["window_height"]:
            err("window_width", "Windows must be at least 6 mm wide and taller than they are wide (arched top)")
        for z, a in wins:
            if abs(((a + 180) % 360) - 180) < 15 and abs(z - p["knob_z"]) < (p["window_height"] + p["knob_diameter"]) / 2 + 3:
                err("knob_z", "The dimmer knob overlaps a front window")
                break
    if d["diffuser_od"] < 30:
        err("tower_top_diameter", "Tower is too narrow for the diffuser tube and tower light")
    if not d["tower_bottom_z"] + p["knob_diameter"] / 2 + 3 <= p["knob_z"] <= d["tower_top_z"] - p["knob_diameter"] / 2 - 8:
        err("knob_z", "Dimmer knob must sit on the tower")
    else:
        # Behind the knob is the diffuser tube if it reaches that high, otherwise the tower-light spine.
        rk = p["knob_diameter"] / 2
        behind_diffuser = d["diffuser_bottom_z"] - SPIDER_T - rk < p["knob_z"] < d["diffuser_top_z"] + rk
        inner_r, what = ((d["diffuser_od"] / 2, "the diffuser tube") if behind_diffuser else
                         (SPINE_D / 2 + FILAMENT_D + 0.5, "the tower-light spine"))
        room = r_out(p["knob_z"]) - w - inner_r
        if room < POT_DEPTH + POT_STANDOFF + 1:
            err("knob_z", f"No room for the dimmer behind the knob: {room:.1f} mm between the tower wall and {what}, "
                          f"{POT_DEPTH + POT_STANDOFF + 1:g} mm needed; move the knob lower")

    # Base: battery, weight plate, USB-C.
    if d["base_inner_height"] < BATTERY[2] + 1:
        err("base_height", f"Base is too shallow for the {BATTERY[2]:g} mm battery (inside height {d['base_inner_height']:.1f} mm)")
    if d["weight_plate_bottom_z"] < USBC_Z + USBC_H / 2 + 1.5:
        err("weight_plate_thickness", "Weight plate is too thick: it must stay above the USB-C board; make the base taller "
                                      "or the plate thinner")
    bx, by = BATTERY[0] / 2 + 1, abs(BATTERY_Y) + BATTERY[1] / 2 + 1
    if math.hypot(bx, by) > rb - w - 2:
        err("base_diameter", "Base is too small for the battery")
    if d["weight_plate_diameter"] / 2 < STANDOFF_R + STANDOFF_HEX:
        err("base_diameter", "Weight plate is too small for the bottom-plate standoffs")
    if USBC_Z + USBC_H / 2 > p["base_height"] - p["base_top_round"] - 1:
        err("base_top_round", "The USB-C port must sit below the base's rounded edge")
    if p["base_top_round"] > p["base_height"] - w - 2:
        err("base_top_round", "Base top radius is too large for the base height")

    # Process wall limits from the rules data.
    for part_key, param_key in (("tower", "wall_thickness"), ("lantern_glass", "glass_wall_thickness")):
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
    """Parameters saved by an older generator.

    Parameters from the pre-prototype Faro (no tower) describe a different design, so
    they are replaced by the defaults; otherwise new keys come from the defaults and
    removed ones are dropped.
    """
    if "tower_bottom_diameter" not in params:
        return {k: defaults[k] for k in PARAM_KEYS if k in defaults}
    out = {k: v for k, v in params.items() if k in PARAM_BY_KEY}
    for k in PARAM_KEYS:
        if k not in out and k in defaults:
            out[k] = defaults[k]
    return out


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _v(r: float, z: float) -> Vector:
    return Vector(r, 0, z)


def _poly(points: list[tuple[float, float]]) -> Face:
    """Closed (r, z) polygon in the XZ plane."""
    return Face(Wire.make_polygon([_v(r, z) for r, z in points], close=True))


def _one_face(shape: Any) -> Face:
    faces = shape.faces() if hasattr(shape, "faces") else [shape]
    return max(faces, key=lambda f: f.area)


def _one(shape: Any) -> Shape:
    sols = shape.solids()
    return sols[0] if len(sols) == 1 else max(sols, key=lambda s: s.volume)


def _fillet_at(face: Face, corners: list[tuple[float, float]], radius: float) -> Face:
    """2D fillet at the section vertices nearest the given (r, z) corners."""
    if radius <= 0:
        return face
    verts = [v for v in face.vertices() if any(math.hypot(v.X - r, v.Z - z) < 1e-4 for r, z in corners)]
    return _one_face(fillet(verts, radius)) if verts else face


def _splined(face: Face, n: int = 24) -> Face:
    """Replace offset curves in a planar section with B-splines through them: a revolved offset
    curve is not written reliably to STEP (the face is dropped on re-import)."""
    edges = []
    changed = False
    for e in face.outer_wire().edges():
        if e.geom_type == GeomType.OFFSET:
            pts = [e.position_at(i / n) for i in range(n + 1)]
            edges.append(Edge.make_spline(pts))
            changed = True
        else:
            edges.append(e)
    return Face(Wire(edges)) if changed else face


def _shell_section(outer: Face, w: float, bottom_z: float, bottom_r: float, hole_r: float, top_z: float) -> Face:
    """A spun shell's half-section: the outer region minus its inward offset, open at the
    bottom and with a centre hole (hole_r must exceed w)."""
    inner = _one_face(offset(outer, -w))
    opening = _poly([(-1, bottom_z - 1), (bottom_r - w, bottom_z - 1), (bottom_r - w, bottom_z + w + 0.01), (-1, bottom_z + w + 0.01)])
    hole = _poly([(-1, bottom_z - 1), (hole_r, bottom_z - 1), (hole_r, top_z + 1), (-1, top_z + 1)])
    return _splined(_one_face(outer - inner - opening - hole))


def _revolve(section: Face) -> Shape:
    return revolve(section, Axis.Z, 360)


def _dir(angle_deg: float) -> Vector:
    """Unit vector in XY at an angle from the front (-Y)."""
    a = math.radians(angle_deg)
    return Vector(math.sin(a), -math.cos(a), 0)


def _front_prism(face_on_xz: Any, depth: float = 400.0) -> Shape:
    """A sketch drawn in the XZ plane (as seen from the front), pushed along -Y."""
    return extrude(Plane.XZ * face_on_xz, amount=depth)


def _arch(wd: float, ht: float) -> Any:
    """Arched window outline (round top), centred on its middle, in sketch coordinates."""
    rr = wd / 2
    rect = Pos(0, -(ht / 2) + (ht - rr) / 2) * Rectangle(wd, ht - rr)
    top = Pos(0, ht / 2 - rr) * Circle(rr)
    return rect + top


def _wedge(a0_deg: float, a1_deg: float, r: float, z0: float, h: float) -> Shape:
    """Angular sector from a0 to a1 (degrees from the front, -Y), z0..z0+h."""
    n = max(2, int(abs(a1_deg - a0_deg) / 10) + 2)
    pts = [(0.0, 0.0)]
    for i in range(n + 1):
        d = _dir(a0_deg + (a1_deg - a0_deg) * i / n)
        pts.append((d.X * r, d.Y * r))
    return Pos(0, 0, z0) * extrude(Polygon(*pts, align=None), amount=h)


@lru_cache(maxsize=8)
def _engraved_knob(knob_diameter: float) -> tuple[Shape, Shape]:
    """The brass knob (back face at y = 0, front face at y = -KNOB_PROUD, axis through the origin) with the
    logo engraved in its face, and the engraved volume (shown black in the preview). Cached per diameter;
    build_model moves it into place.

    The logo is the same artwork as the vector files and the drawing, upright as modelled: the RFQ asks
    for it upright with the knob at its off stop."""
    from app.factory import logo as art

    rk = knob_diameter / 2
    knob = Rot(90, 0, 0) * Cylinder(rk, KNOB_PROUD, align=MIN)
    knob = fillet(knob.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Y)[:1], art.EDGE_FILLET)
    cutter = Pos(0, -KNOB_PROUD + art.ENGRAVE_DEPTH, 0) * _front_prism(art.grooves(art.logo_radius(knob_diameter)),
                                                                     depth=art.ENGRAVE_DEPTH + 1.0)
    fill = knob & cutter
    return _one(knob - cutter), Compound(fill.solids())


@lru_cache(maxsize=4)
def _nameplate(rb: float, hb: float) -> tuple[Shape, Shape]:
    """The nameplate and its etched lettering (the fill shown black in the preview); depends only on the base.

    Its curved faces are 0.5° facets (chord error 0.0005 mm): the lettering's many small faces cut reliably
    into flat facets. The lettering is the same artwork as the SVG / DXF files and the drawing."""
    from app.factory import nameplate as art

    zn = NAMEPLATE_Z
    half = math.degrees(NAMEPLATE_W / 2 / rb) + 3
    plate = _one(_arc_shell(rb + 0.01, rb + NAMEPLATE_T, 0, hb, -90 - half, -90 + half)
                 & (Pos(0, 0, zn) * _front_prism(RectangleRounded(NAMEPLATE_W, NAMEPLATE_H, 1.2))))
    etch_shell = _arc_shell(rb + NAMEPLATE_T - art.ETCH_DEPTH, rb + NAMEPLATE_T, 0, hb, -90 - half, -90 + half)
    letters = []
    for face in art.shapes()[1].faces():  # one boolean per letter
        letters += (etch_shell & (Pos(0, 0, zn) * _front_prism(face))).solids()
    for sol in letters:
        plate = plate - sol
    return _one(plate), Compound(letters)


def _arc_shell(ri: float, ro: float, z0: float, h: float, a0: float = -135.0, a1: float = -45.0, step: float = 0.5) -> Shape:
    """A faceted cylindrical shell segment round the front (-Y), angles in degrees from +X."""
    n = int(round((a1 - a0) / step))
    angs = [math.radians(a0 + i * (a1 - a0) / n) for i in range(n + 1)]
    pts = [Vector(ro * math.cos(a), ro * math.sin(a), z0) for a in angs] + \
          [Vector(ri * math.cos(a), ri * math.sin(a), z0) for a in reversed(angs)]
    return extrude(Face(Wire.make_polygon(pts, close=True)), amount=h)


def _annulus(ro: float, ri: float, z0: float, h: float) -> Shape:
    return Pos(0, 0, z0) * (Cylinder(ro, h, align=MIN) - Cylinder(ri, h + 2, align=MIN))


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


@dataclass
class Model:
    parts: dict[str, Shape]
    sections: dict[str, Face]  # half-sections (r, z in the XZ plane) of the revolved made parts
    info: dict[str, Any]
    preview: dict[str, Shape] = field(default_factory=dict)  # preview-only bodies (e.g. the nameplate's black fill)


def _sections(p: dict[str, float], d: dict[str, Any]) -> dict[str, Face]:
    w = p["wall_thickness"]
    rb, hb, R = p["base_diameter"] / 2, p["base_height"], p["base_top_round"]
    out: dict[str, Face] = {}

    # Base: spun inverted cup with a generous top edge radius and a centre hole.
    base_outer = _fillet_at(_poly([(0, 0), (rb, 0), (rb, hb), (0, hb)]), [(rb, hb)], R)
    out["base"] = _shell_section(base_outer, w, 0.0, rb, WIRE_HOLE_D / 2, hb)

    # Cream band: turned ring with a rounded top edge and a spigot that locates the tower.
    rc = p["band_diameter"] / 2
    z0, z1 = hb, d["tower_bottom_z"]
    r_sp_out = d["r_out"](z1 + TOWER_SPIGOT_H) - w - 0.1
    band = _fillet_at(_poly([(rc - BAND_WIDTH, z0), (rc, z0), (rc, z1), (rc - BAND_WIDTH, z1)]), [(rc, z1)], BAND_ROUND)
    spigot = _poly([(rc - BAND_WIDTH, z1 - 0.01), (r_sp_out, z1 - 0.01), (r_sp_out, z1 + TOWER_SPIGOT_H),
                    (rc - BAND_WIDTH, z1 + TOWER_SPIGOT_H)])
    out["band_cream"] = _one_face(band + spigot)

    # Tower: spun cone, open both ends.
    r_out = d["r_out"]
    zt0, zt1 = d["tower_bottom_z"], d["tower_top_z"]
    out["tower"] = _poly([(r_out(zt0) - w, zt0), (r_out(zt0), zt0), (r_out(zt1), zt1), (r_out(zt1) - w, zt1)])

    # Gallery: spun brass shell (flat top that doubles as the LED ledge, outer skirt, open underneath)
    # with a turned brass locating ring soldered under it that sits on the tower top and spigots inside it.
    rg, zg0, zg1, t = p["gallery_diameter"] / 2, zt1, d["gallery_top_z"], GALLERY_SHEET
    shell = _poly([(LEDGE_BORE / 2, zg1 - t), (rg - t, zg1 - t), (rg - t, zg0), (rg, zg0), (rg, zg1), (LEDGE_BORE / 2, zg1)])
    shell = _fillet_at(shell, [(rg, zg1)], min(GALLERY_ROUND, p["gallery_height"] / 2 - 0.1))
    sp_o = r_out(zt1) - w - 0.1
    ring = _poly([(sp_o - 1.5, zg0 - GALLERY_SPIGOT_H), (sp_o, zg0 - GALLERY_SPIGOT_H), (sp_o, zg0), (r_out(zt1), zg0),
                  (r_out(zt1), zg1 - t + 0.01), (sp_o - 1.5, zg1 - t + 0.01)])
    out["gallery"] = _one_face(shell + ring)

    # Lantern glass and diffuser: stock borosilicate tubes.
    gr = d["glass_od"] / 2
    zl0, ztb = d["gallery_top_z"], d["lantern_band_bottom_z"]
    out["lantern_glass"] = _poly([(gr - p["glass_wall_thickness"], zl0), (gr, zl0), (gr, ztb), (gr - p["glass_wall_thickness"], ztb)])
    dr = d["diffuser_od"] / 2
    out["diffuser"] = _poly([(dr - DIFFUSER_WALL, d["diffuser_bottom_z"]), (dr, d["diffuser_bottom_z"]),
                             (dr, d["diffuser_top_z"]), (dr - DIFFUSER_WALL, d["diffuser_top_z"])])

    # Cap: spun shell: rim, dome and a small neck (collar) for the finial.
    zc0 = d["cap_bottom_z"]
    rcr, hcr = p["cap_rim_diameter"] / 2, p["cap_rim_height"]
    rd = p["cap_dome_diameter"] / 2
    zd0, zd1 = zc0 + hcr - 0.5, d["cap_top_z"]
    rbo = p["finial_diameter"] / 2
    rim = _poly([(0, zc0), (rcr, zc0), (rcr, zc0 + hcr), (0, zc0 + hcr)])
    dome_curve = Edge.make_spline([_v(rd, zd0), _v(0, zd1)], tangents=[Vector(0, 0, 1), Vector(-1, 0, 0)])
    dome = Face(Wire([Edge.make_line(_v(0, zd0), _v(rd, zd0)), dome_curve, Edge.make_line(_v(0, zd1), _v(0, zd0))]))
    neck = _poly([(0, zd1 - 2.0), (rbo, zd1 - 2.0), (rbo, zd1 - 0.5), (rbo * 0.6, zd1 + CAP_BOSS_H), (0, zd1 + CAP_BOSS_H)])
    cap_outer = _one_face(rim + dome + neck)
    cap_outer = _fillet_at(cap_outer, [(rcr, zc0 + hcr)], min(CAP_FILLET, hcr / 2 - 0.1))
    cap_outer = _fillet_at(cap_outer, [(rcr, zc0)], 0.6)  # edge break on the trimmed rim edge
    out["cap"] = _shell_section(cap_outer, w, zc0, rcr, FINIAL_STUD_D / 2 + 0.25, zd1 + CAP_BOSS_H)
    return out


def build_model(params: dict[str, Any]) -> Model:
    """Build every part. Assumes `validate(params).ok`."""
    p = {k: float(v) for k, v in params.items()}
    d = derived(p)
    w = p["wall_thickness"]
    rb, hb = p["base_diameter"] / 2, p["base_height"]
    r_out = d["r_out"]
    sec = _sections(p, d)
    parts: dict[str, Shape] = {}
    info: dict[str, Any] = {}
    preview: dict[str, Shape] = {}

    # ---- base: spun shell + holes ------------------------------------------------
    base = _revolve(sec["base"])
    pcd_r = d["band_screw_pcd"] / 2
    screw_angles = [90.0 + k * 360 / BAND_SCREWS for k in range(BAND_SCREWS)]  # clear of the front and the rear port
    for a in screw_angles:
        u = _dir(a)
        base = base - Pos(u.X * pcd_r, u.Y * pcd_r, hb - w - 1) * Cylinder(BAND_SCREW_CLEAR / 2, w + 2, align=MIN)
    base = base - Pos(0, 0, USBC_Z) * extrude(Plane.XZ * SlotOverall(USBC_W, USBC_H), amount=-rb - 5)  # rear port
    parts["base"] = _one(base)

    # Bottom plate (aluminium, laser-cut): countersunk screws into the standoffs, magnet holes.
    rp = rb - w - PLATE_CLEAR
    plate = Cylinder(rp, BOTTOM_PLATE_T, align=MIN)
    for k in range(STANDOFFS):
        u = _dir(STANDOFF_ANGLE0 + k * 360 / STANDOFFS)
        x, y = u.X * STANDOFF_R, u.Y * STANDOFF_R
        sink = (SCREW_CS_D - SCREW_CLEAR_D) / 2
        plate = plate - Pos(x, y, -1) * Cylinder(SCREW_CLEAR_D / 2, BOTTOM_PLATE_T + 2, align=MIN)
        plate = plate - Pos(x, y, -0.01) * revolve(_poly([(0, 0), (SCREW_CS_D / 2, 0), (SCREW_CLEAR_D / 2, sink), (0, sink)]), Axis.Z, 360)
        um = _dir(STANDOFF_ANGLE0 + (k + 0.5) * 360 / STANDOFFS)
        plate = plate - Pos(um.X * STANDOFF_R, um.Y * STANDOFF_R, -1) * Cylinder(MAGNET_D / 2 + 0.05, BOTTOM_PLATE_T + 2, align=MIN)
    parts["base_plate"] = _one(plate)
    felt_t = FELT_T + FELT_BACKING
    parts["felt_pad"] = Pos(0, 0, -felt_t) * Cylinder(rp - FELT_INSET, felt_t, align=MIN)

    # Weight plate (laser-cut steel) against the underside of the base top, round the battery.
    wpr, wpt = d["weight_plate_diameter"] / 2, p["weight_plate_thickness"]
    z_wp = d["weight_plate_bottom_z"]
    wp = Pos(0, 0, z_wp) * Cylinder(wpr, wpt, align=MIN)
    bl, bw, bt = BATTERY
    wp = wp - Pos(0, BATTERY_Y, z_wp - 1) * extrude(RectangleRounded(bl + 2, bw + 2, 3.0), amount=wpt + 2)
    wp = wp - Pos(0, 0, z_wp - 1) * Cylinder(WIRE_HOLE_D / 2, wpt + 2, align=MIN)
    for a in screw_angles:
        u = _dir(a)
        wp = wp - Pos(u.X * pcd_r, u.Y * pcd_r, z_wp - 1) * Cylinder(BAND_SCREW_CLEAR / 2, wpt + 2, align=MIN)
        wp = wp - Pos(u.X * pcd_r, u.Y * pcd_r, z_wp - 1) * Cylinder(BAND_SCREW_HEAD / 2 + 0.3, 1 + min(3.2, wpt / 2), align=MIN)
    for k in range(STANDOFFS):  # M2.5 tapped holes for the standoffs
        u = _dir(STANDOFF_ANGLE0 + k * 360 / STANDOFFS)
        wp = wp - Pos(u.X * STANDOFF_R, u.Y * STANDOFF_R, z_wp - 1) * Cylinder(1.05, min(6.0, wpt) + 1, align=MIN)
    parts["weight_plate"] = _one(wp)
    parts["battery"] = Pos(0, BATTERY_Y, BOTTOM_PLATE_T + 0.5) * Box(bl, bw, bt, align=MIN)
    board = Pos(0, rb - w - 2 - 12.5, BOTTOM_PLATE_T + 0.5) * Box(40, 25, 1.6, align=MIN)  # charger + LED driver
    rec = Pos(0, rb - w - 0.3, USBC_Z) * Box(9.0, 7.5, 3.3, align=(Align.CENTER, Align.MAX, Align.CENTER))
    stand = Pos(0, rb - w - 7.8, BOTTOM_PLATE_T + 2.1) * Box(9.0, 3.0, USBC_Z - BOTTOM_PLATE_T - 2.1 - 1.0, align=MIN)
    parts["charge_board"] = _one(board + rec + stand)
    info["battery_headroom"] = round(d["base_inner_height"] - bt - 0.5, 2)

    # Nameplate: etched brass, curved to the base, bonded on the front, with the FARO lettering etched in.
    plate, etch = _nameplate(rb, hb)
    parts["nameplate"] = plate
    preview["nameplate_fill"] = etch
    info["nameplate_etch_mm3"] = round(etch.volume, 3)

    # ---- cream band -------------------------------------------------------------
    band = _revolve(sec["band_cream"])
    for a in screw_angles:  # M3 tapped blind holes from below
        u = _dir(a)
        band = band - Pos(u.X * pcd_r, u.Y * pcd_r, hb - 0.01) * Cylinder(1.25, min(5.0, p["band_height"] - 1), align=MIN)
    parts["band_cream"] = _one(band)

    # ---- tower: spun cone, windows, dimmer hole -----------------------------------
    tower = _revolve(sec["tower"])
    ww, wh = p["window_width"], p["window_height"]
    for zw, ang in windows(p):
        tower = tower - Rot(0, 0, ang) * Pos(0, 0, zw) * _front_prism(_arch(ww, wh), depth=200)
    zk = p["knob_z"]
    tower = tower - Pos(0, 0, zk) * Rot(90, 0, 0) * Cylinder(POT_HOLE_D / 2, 200, align=MIN)
    parts["tower"] = _one(tower)
    info["windows"] = d["windows"]

    # Diffuser: opal borosilicate tube behind the windows; tower light on a central spine.
    parts["diffuser"] = _revolve(sec["diffuser"])
    z_s0, z_s1 = hb, d["gallery_top_z"] - LEDGE_T - 0.5
    spine = Pos(0, 0, z_s0) * Cylinder(SPINE_D / 2, z_s1 - z_s0, align=MIN)
    # spider (disc) on the spine that carries the diffuser tube
    spine = spine + Pos(0, 0, d["diffuser_bottom_z"] - SPIDER_T) * Cylinder(d["diffuser_od"] / 2, SPIDER_T, align=MIN)
    wz = [z for z, _ in windows(p)] or [(d["tower_bottom_z"] + d["tower_top_z"]) / 2]
    zf0 = max(min(wz) - wh / 2 - 5, z_s0 + 5)
    zf1 = min(max(wz) + wh / 2 + 5, z_s1 - 5)
    for k in range(FILAMENTS):
        u = _dir(45 + k * 360 / FILAMENTS)
        rr = SPINE_D / 2 + FILAMENT_D / 2 + 0.5
        spine = spine + Pos(u.X * rr, u.Y * rr, zf0) * Cylinder(FILAMENT_D / 2, zf1 - zf0, align=MIN)
    parts["tower_light"] = _one(spine)

    # Dimmer: slim rotary pot behind the wall, brass knob on the front.
    y_out = -r_out(zk)
    y_in = y_out + w
    # the pot's flat face stands off the curved, leaning wall on a curved spacer washer
    pot = Pos(0, y_in + POT_STANDOFF, zk) * Rot(-90, 0, 0) * Cylinder(POT_D / 2, POT_DEPTH, align=MIN)
    bushing = Pos(0, y_out - 2.0, zk) * Rot(-90, 0, 0) * Cylinder(POT_HOLE_D / 2 - 0.25, w + 2.0, align=MIN)
    parts["dimmer"] = _one(pot + bushing)
    rk = p["knob_diameter"] / 2
    # the conical wall leans back by the taper, so the knob's back sits clear of it at its lowest point
    lean = rk * math.tan(math.radians(d["tower_taper_deg"]))
    knob, logo_fill = _engraved_knob(p["knob_diameter"])
    at = Pos(0, y_out - KNOB_GAP - lean, zk)
    parts["knob"] = _one(at * knob)
    preview["knob_logo_fill"] = at * logo_fill
    info["knob_logo_mm3"] = round(logo_fill.volume, 3)

    # ---- gallery and railing ----------------------------------------------------
    parts["gallery"] = _revolve(sec["gallery"])
    zg1 = d["gallery_top_z"]
    rro = p["gallery_diameter"] / 2 - RAIL_INSET
    rri = rro - RAIL_T
    rh = p["railing_height"]
    n_posts = int(p["railing_posts"])
    rail = _annulus(rro, rri, zg1, rh)
    post_half = math.degrees(RAIL_POST_W / 2 / rro)
    z_mid = zg1 + rh * RAIL_MID_FRAC
    bands = [(zg1 + RAIL_FOOT_H, z_mid - RAIL_BAR_H / 2), (z_mid + RAIL_BAR_H / 2, zg1 + rh - RAIL_BAR_H)]
    for k in range(n_posts):
        a0 = k * 360 / n_posts + post_half
        a1 = (k + 1) * 360 / n_posts - post_half
        for za, zb in bands:
            rail = rail - _wedge(a0, a1, rro + 2, za, zb - za)
    parts["railing"] = _one(rail)

    # ---- lantern: brass frame + frosted glass + LED -------------------------------
    rl = p["lantern_diameter"] / 2
    zl0, zl1 = d["gallery_top_z"], d["lantern_top_z"]
    ztb = d["lantern_band_bottom_z"]
    r_lip = d["lip_r"]
    groove_r = rl - 1.2
    rgl = d["glass_od"] / 2
    frame = _annulus(rl, rgl + FIT_CLEAR, zl0, LANTERN_RING_H)
    frame = frame + _annulus(rl, groove_r, ztb, TOP_BAND_H)
    frame = frame + _annulus(groove_r + 0.01, r_lip, zl1 - LIP_H, LIP_H)
    lug_half = math.degrees(LOCK_LUG_W / 2 / r_lip)
    slot_half = math.degrees((LOCK_LUG_W + 2 * FIT_CLEAR) / 2 / r_lip)
    for k in range(LOCK_LUGS):
        a0 = k * 360 / LOCK_LUGS
        seg = _annulus(groove_r, r_lip - 0.5, zl1 - LIP_H - 0.5, LIP_H + 1.0)
        frame = frame - (seg & _wedge(a0 - slot_half, a0 + slot_half, groove_r + 5, zl1 - LIP_H - 1, LIP_H + 2))
        sgn = 1 if LOCK_TURN_DEG >= 0 else -1
        a_stop = a0 + LOCK_TURN_DEG + sgn * (lug_half + math.degrees(1.0 / r_lip))
        frame = frame + Rot(0, 0, a_stop) * Pos(0, -(groove_r + r_lip) / 2, ztb) * Box(
            1.5, groove_r - r_lip + 0.2, TOP_BAND_H - LIP_H + 0.2, align=MIN)
    for k in range(int(p["lantern_mullions"])):
        ang = (k + 0.5) * 360 / p["lantern_mullions"]  # a panel faces the front
        frame = frame + Rot(0, 0, ang) * Pos(0, -(rl - MULLION_DEPTH / 2), zl0) * Box(
            MULLION_W, MULLION_DEPTH, ztb - zl0 + 0.5, align=MIN)
    parts["lantern_frame"] = _one(frame)
    parts["lantern_glass"] = _revolve(sec["lantern_glass"])
    led = Pos(0, 0, zl0) * Cylinder(LED_BOARD_D / 2, 1.6, align=MIN)
    led = led + Pos(0, 0, zl0 + 1.6) * Cylinder(LED_EMITTER_D / 2, LED_H - 1.6, align=MIN)
    parts["led_module"] = _one(led)

    # ---- cap, bayonet spigot and finial ------------------------------------------
    parts["cap"] = _revolve(sec["cap"])
    r_sp = r_lip - FIT_CLEAR
    z_lug_top = zl1 - LIP_H - FIT_CLEAR
    z_sp0 = z_lug_top - LOCK_LUG_H
    rcr_in = p["cap_rim_diameter"] / 2 - w - 0.2
    spig = _annulus(r_sp, r_sp - SPIGOT_WALL, z_sp0, zl1 - z_sp0 + 0.5)
    spig = spig + _annulus(rcr_in, r_sp - SPIGOT_WALL, zl1 + 0.5, 1.5)  # flange bonded under the cap shoulder

    def lugs(turn: float) -> Shape:
        out = None
        for k in range(LOCK_LUGS):
            lg = Rot(0, 0, k * 360 / LOCK_LUGS + turn) * Pos(0, -(r_sp - 0.2), z_sp0) * Box(
                LOCK_LUG_W, groove_r - FIT_CLEAR - (r_sp - 0.2), LOCK_LUG_H, align=(Align.CENTER, Align.MAX, Align.MIN))
            out = lg if out is None else out + lg
        return out

    parts["cap_spigot"] = _one(spig + lugs(LOCK_TURN_DEG))  # modelled locked
    rf = p["finial_diameter"] / 2
    z_top = p["overall_height"]
    z_neck = d["cap_top_z"] + CAP_BOSS_H  # the finial sits on the collar, held by its stud
    finial = Pos(0, 0, z_top - rf) * Sphere(rf) + Pos(0, 0, z_neck) * Cylinder(rf * 0.45, z_top - rf - z_neck, align=MIN)
    finial = finial + Pos(0, 0, d["cap_top_z"] - 8.0) * Cylinder(FINIAL_STUD_D / 2, z_neck - d["cap_top_z"] + 8.5, align=MIN)
    parts["finial"] = _one(finial)

    clash = lambda a_, b_: 0.0 if (a_ & b_) is None else round((a_ & b_).volume, 3)  # noqa: E731
    info["bayonet"] = {"locked_clash_mm3": clash(parts["cap_spigot"], parts["lantern_frame"]),
                       "entry_clash_mm3": clash(lugs(0.0), parts["lantern_frame"]),
                       "lug_under_lip_mm": round((groove_r - FIT_CLEAR) - r_lip, 2),
                       "led_lifts_out": d["led_access_dia"] > LED_BOARD_D}
    info["glass_frame_clash_mm3"] = clash(parts["lantern_glass"], parts["lantern_frame"])
    return Model(parts={k: _one(parts[k]) for k in PART_KEYS}, sections=sec, info=info, preview=preview)


@lru_cache(maxsize=8)
def _cached(params_json: str) -> Model:
    return build_model(json.loads(params_json))


def model(params: dict[str, Any]) -> Model:
    """Cached build: the drawings, costing and export share one build per parameter set."""
    return _cached(json.dumps({k: float(v) for k, v in params.items()}, sort_keys=True))


def build(params: dict[str, Any]) -> dict[str, Shape]:
    """One solid per part. Assumes `validate(params).ok`."""
    return model(params).parts


def _sample(face: Face, n_curve: int = 16) -> list[tuple[float, float]]:
    """The section's outer boundary as (r, z) points; curved edges are sampled."""
    pts: list[tuple[float, float]] = []
    for e in face.outer_wire().edges():
        n = 1 if e.geom_type == GeomType.LINE else n_curve
        for i in range(n):
            q = e.position_at(i / n)
            pts.append((round(q.X, 3), round(q.Z, 3)))
    return pts


def section_profiles(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Half-section outlines (r, z) of the made-to-drawing revolved parts, z from each part's bottom.

    Taken from the same 2D sections the solids are revolved from, so drawings match `build()`.
    """
    m = model(params)
    out: dict[str, dict[str, Any]] = {}
    for key, face in m.sections.items():
        bb = face.bounding_box()
        z0 = bb.min.Z
        pts = [(r, round(z - z0, 3)) for r, z in _sample(face)]
        out[key] = {"outline": pts, "height": round(bb.max.Z - z0, 3), "diameter": round(2 * bb.max.X, 3), "z0": round(z0, 3)}
    return out


def assembly(parts: dict[str, Shape], name: str = "faro") -> Compound:
    """A labelled, coloured compound for STEP and glTF export."""
    kids = []
    for key, shape in parts.items():
        s = copy.copy(shape)
        s.label = key
        s.color = Color(*PART_COLOURS.get(key, (0.7, 0.7, 0.7, 1.0)))
        kids.append(s)
    return Compound(children=kids, label=name)


def production_change_checks(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Check the built solids against the PRODUCTION_CHANGES rows that geometry can prove."""
    p = {k: float(v) for k, v in params.items()}
    d = derived(p)
    m = model(params)
    parts, info = m.parts, m.info
    w = p["wall_thickness"]
    out = []

    def check(feature: str, ok: bool, detail: str) -> None:
        out.append({"feature": feature, "ok": bool(ok), "detail": detail})

    walls = {}
    for key in ("base", "tower", "cap"):
        sec = m.sections[key]
        walls[key] = sec.area / (sum(e.length for e in sec.outer_wire().edges()) / 2)
    check("Shell walls", all(abs(v - w) <= 0.25 * w for v in walls.values()),
          "spun shells " + ", ".join(f"{k} {v:.2f} mm" for k, v in walls.items()) + f" (wall {w:g} mm)")
    bb = parts["diffuser"].bounding_box()
    check("Window diffusers", abs(bb.min.Z - d["diffuser_bottom_z"]) < 0.05 and abs(bb.max.Z - d["diffuser_top_z"]) < 0.05,
          f"opal tube z {bb.min.Z:.1f}–{bb.max.Z:.1f} mm, length {d['diffuser_length']:.1f} mm (window zone ± "
          f"{DIFFUSER_OVERLAP:g} mm)")
    check("Windows", len(info.get("windows", [])) == int(p["window_count"]), f"{len(info.get('windows', []))} windows cut")
    rg = p["gallery_diameter"] / 2
    solid = math.pi * (rg**2 - d["gallery_bore_r"] ** 2) * p["gallery_height"]
    check("Gallery", parts["gallery"].volume < 0.4 * solid,
          f"spun shell {parts['gallery'].volume / 1000:.1f} cm³ vs {solid / 1000:.1f} cm³ for a solid ring")
    bay = info.get("bayonet", {})
    check("Cap twist-lock", bay.get("locked_clash_mm3") == 0 and bay.get("entry_clash_mm3") == 0 and bay.get("lug_under_lip_mm", 0) > 1,
          f"4 lugs, no clash locked or at entry, {bay.get('lug_under_lip_mm', 0):.1f} mm under the lip")
    gb = parts["lantern_glass"].bounding_box()
    vol = parts["lantern_glass"].volume
    h = gb.max.Z - gb.min.Z
    ro = (gb.max.X - gb.min.X) / 2
    wall = ro - math.sqrt(max(ro**2 - vol / (math.pi * h), 0))
    check("Lantern glass", abs(wall - p["glass_wall_thickness"]) < 0.05, f"tube wall {wall:.2f} mm")
    check("Base fixing", {"weight_plate", "base_plate", "felt_pad"} <= set(parts), "weight plate, bottom plate and felt pad modelled")
    return out


def derived_traits(part_key: str, params: dict[str, Any]) -> list[str]:
    """Geometry traits implied by the current parameters, for the rules engine."""
    p = {k: float(v) for k, v in params.items()}
    if part_key == "tower":
        tapered = p["tower_top_diameter"] < p["tower_bottom_diameter"] - 0.5
        traits = ["tapered"] if tapered else ["constant_section"]
        if int(p.get("window_count", 0)) > 0:
            traits.append("side_hole")
        return traits
    if part_key in ("band_cream", "lantern_glass", "diffuser", "gallery", "railing"):
        return ["constant_section"]
    return []


def led_clearance(params: dict[str, Any]) -> float:
    """Radial gap between the LED emitter and the inside of the lantern glass (mm)."""
    p = {k: float(v) for k, v in params.items()}
    return derived(p)["glass_inner_r"] - LED_EMITTER_D / 2


def estimate_mass(part_info: dict[str, Any], densities: dict[str, float]) -> dict[str, Any]:
    """Lamp mass from CAD volumes (mm³) and densities (g/cm³) per part key."""
    per = {k: round(info["volume_mm3"] / 1000 * densities[k] / 1000, 3)
           for k, info in part_info.items() if k in densities}
    return {"total_kg": round(sum(per.values()), 3), "parts_kg": per}


def body_taper_deg(params: dict[str, Any]) -> float:
    p = {k: float(v) for k, v in params.items()}
    return derived(p)["tower_taper_deg"]


def public_derived(params: dict[str, Any]) -> dict[str, Any]:
    """Derived dimensions for the API (no functions)."""
    return _public_derived(derived({k: float(v) for k, v in params.items()}))
