"""Atelier parametric model: parameters, validation, geometry, mass and stability.

The form is the approved prototype (branch claude/rocket-speaker-3d-model-xav3pn, model.py and
params.py, Sep 2026), ported into `atelier_geometry` with the prototype's parameters kept verbatim
in `atelier_prototype_params`. This module sets what production changes (the Technical
Specification, Oct 2026, and the user's answers) on top of them, and every change is a row in
PRODUCTION_CHANGES.

Coordinate system (as the prototype): Z up, ground at z = 0 (the fin pads' undersides), the
rocket's axis is Z, the front (grille, knob) faces -Y. Units mm. One solid per part; the three
fins and their pads are one part each (quantity 3): `build` returns the fin at 60°, and the STEP
assembly and the GLB preview add the copies at 180° and 300°.
"""

from __future__ import annotations

import copy
import json
import math
import types
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np
from build123d import Box, Color, Compound, Cylinder, Pos, Rot, Shape

from app.cad import atelier_geometry as geo
from app.cad import atelier_prototype_params as proto
from app.cad.validation import ParamDef, ValidationIssue, ValidationResult, WallLimit
from app.config import SEED_DIR

GENERATOR = "atelier"

# ---------------------------------------------------------------------------
# Production values (Technical Specification, Oct 2026, and the user's answers)
# ---------------------------------------------------------------------------
HEX_HOLE = proto.HEX_HOLE  # 2.2 mm across flats (unchanged)
HEX_WEB = proto.HEX_WEB  # 0.7 mm: photo-etching needs webs and holes at least the sheet thickness
FABRIC_T = 0.4  # black acoustic fabric behind the grille (spec), in a pocket under the grille
GRILLE_PROUD = 0.2  # the grille stands this far above the red surface, inside the bezel (as the prototype)
SHADOW_LINE = 0.3  # seams 0.3 ±0.1 mm (spec; prototype 0.4 mm chamfers)
KNOB_GAP = 0.3  # knob to body (spec: gap 0.3 ±0.05)
FIN_PAD_T = 1.0  # TPU pad under each fin tip (spec)
FIN_BOLT_SLOT = 2.0  # vertical travel of the fin-screw slots in the shell
CONE_ORING_GROOVE = (1.6, 0.9)  # width, depth of the O-ring groove on the nose-cone spigot
CONE_SPIGOT_WALL = 2.5  # thicker than the prototype's 2.0 so the groove leaves 1.6 mm
BATTERY_TRAY_T = 3.0  # steel tray plate on the collar spigot (chassis); the collar screws thread into it
COLLAR_SCREWS = 3  # M2.5 countersunk, on a small circle under the foot
COLLAR_SCREW_PCD = 11.0
COLLAR_SCREW_CLEAR = 2.7
COLLAR_SCREW_HEAD = 5.0
COLLAR_SCREW_TAP = 2.1
TRAY_SCREW_DEPTH = 6.0  # the tray plate's two M2.5 screws: tapped this deep into the ballast cup
FOOT_STUD_TAP = 3.3  # M4 stud: tapped in the collar, the foot screws onto it
FOOT_STUD_DEPTH = 6.0
LETTERING_CAP = 2.4  # "ATELIER" etched under the collar (user, Oct 2026: option 1)
LETTERING_DEPTH = 0.15
COLLAR_LETTERING_FILE = SEED_DIR / "artwork" / "A-01_collar_lettering_loops.json"

# Production materials (g/cm³) for the ballast sizing inside the build; the workbench's mass
# estimate uses the rules data's densities for the decided materials.
DENSITY = {"pc_abs": 1.15, "aluminium": 2.70, "zamak_5": 6.70, "stainless_304": 8.00, "brass": 8.50,
           "steel": 7.85, "acoustic_cloth": 0.50, "tpu": 1.20,
           "jesmonite_ac100": 1.745,  # dry density with glass fibre (user, Oct 2026)
           "pu_casting_resin": 1.12}
PART_MATERIALS = {"body": "pc_abs", "nose_cone": "aluminium", "fins": "zamak_5", "foot": "zamak_5",
                  "grille": "stainless_304", "bezel": "aluminium", "knob": "brass", "chassis": "steel",
                  "grille_backing": "acoustic_cloth", "vent_insert": "stainless_304", "ballast": "steel"}
BATTERY_MASS_G = 100.0  # 2 x 18650 1S2P with protection board and wrap
DRIVER_MASS_G = 65.0
PR_MASS_G = 60.0
BOARD_MASS_G = 30.0
# Share of the driver's and radiator's envelopes they actually displace: the air behind the cone (inside the
# basket) and the radiator's travel space is part of the box. Typical values (model-generated); the driver
# supplier's net volume replaces them.
DRIVER_DISPLACEMENT_FRAC = 0.4
PR_DISPLACEMENT_FRAC = 0.3
BOARD_SIZE = (40.0, 8.0, 60.0)  # main board envelope on the chassis spine: width, depth (board + module), height

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
PARAMS: list[ParamDef] = [
    ParamDef("overall_height", "Overall height", "Overall", 240, 320,
             help="Ground to the nose tip (the fins stand on 1 mm TPU pads). Spec 280 ±1."),
    ParamDef("body_max_diameter", "Body diameter at its widest", "Overall", 85, 110, step=0.5,
             help="Spec Ø95 ±0.5 (the prototype was Ø96.8)."),
    ParamDef("target_mass_kg", "Target total mass", "Overall", 1.0, 3.0, step=0.05, unit="kg",
             help="The steel ballast cup is sized to reach it. Spec 1.8 ±0.1 kg."),
    ParamDef("base_clearance", "Body underside above the ground", "Body", 18, 40, step=0.1,
             help="Room for the gold collar cup and the foot."),
    ParamDef("nose_cone_height", "Nose cone height", "Body", 30, 70, step=0.1),
    ParamDef("wall_thickness", "Body wall", "Body", 2.0, 6.0, step=0.1,
             help="Spec 3.0 mm (moulded PC/ABS); about 5 mm for a cast Jesmonite body."),
    ParamDef("grille_height", "Grille centre height", "Front", 120, 220, step=0.1),
    ParamDef("grille_diameter", "Grille diameter", "Front", 50, 90, step=0.1,
             help="Wrapped round the body: full height, narrower seen from the front."),
    ParamDef("grille_thickness", "Grille sheet", "Front", 0.3, 1.2, step=0.1,
             help=f"Photo-etched stainless; at most the {HEX_WEB:g} mm web. Spec 0.5 mm."),
    ParamDef("grille_perforated", "Honeycomb holes", "Front", 0, 1, integer=True, unit="",
             help="1 = cut the 2.2 mm hexagons (slow, about a minute); 0 = plain sheet for quick checks."),
    ParamDef("knob_diameter", "Knob diameter", "Front", 16, 24, step=0.5,
             help="Faro's knurled brass knob with the emblem (Ø20)."),
    ParamDef("fin_tip_radius", "Fin tip distance from the axis", "Fins", 65, 95, step=0.5,
             help="Sets the stance: the fin span is about 1.75 x this."),
    ParamDef("fin_thickness", "Fin thickness", "Fins", 6, 12, step=0.5),
    ParamDef("pr_width", "Passive radiator width", "Rear", 30, 50, step=0.5),
    ParamDef("pr_height", "Passive radiator height", "Rear", 40, 70, step=0.5),
]
PARAM_KEYS = [p.key for p in PARAMS]
PARAM_BY_KEY = {p.key: p for p in PARAMS}

# Parameters that stay fixed when the speaker is scaled to another height.
UNSCALED_PARAMS = {"target_mass_kg", "wall_thickness", "grille_thickness", "grille_perforated", "knob_diameter",
                   "fin_thickness", "pr_width", "pr_height"}

GOLD = (0.77, 0.63, 0.35, 1.0)
RED = (0.54, 0.11, 0.08, 1.0)
DARK = (0.08, 0.08, 0.09, 1.0)
STEEL = (0.55, 0.56, 0.58, 1.0)
PART_COLOURS: dict[str, tuple[float, float, float, float]] = {
    "body": RED, "nose_cone": GOLD, "fin": GOLD, "fin_pad": DARK, "collar": GOLD, "foot": GOLD,
    "grille": GOLD, "grille_fabric": (0.17, 0.16, 0.16, 1.0), "bezel": GOLD, "rear_grille": GOLD,
    "rear_bezel": GOLD, "rear_fabric": (0.17, 0.16, 0.16, 1.0), "knob": GOLD, "chassis": STEEL, "ballast": STEEL, "driver": DARK,
    "passive_radiator": DARK, "battery": (0.2, 0.45, 0.75, 1.0), "main_board": (0.1, 0.35, 0.2, 1.0),
}
PART_KEYS = list(PART_COLOURS)
INSTANCES = {"fin": 3, "fin_pad": 3}  # parts modelled once and fitted several times
PREVIEW_EXTRA_COLOURS = {"knob_logo_floor": (0.72, 0.58, 0.32, 1.0), "collar_etch_floor": (0.72, 0.58, 0.32, 1.0),
                         "led": (1.0, 0.89, 0.69, 1.0)}

# Where production departs from the approved prototype, and why (CAD tab, DFM and, later, the RFQ).
PRODUCTION_CHANGES: list[dict[str, str]] = [
    {"feature": "Body diameter", "prototype": "Ø96.8 at its widest (fitted to the concept)",
     "production": "Ø95 ±0.5 (Technical Specification); the side profile keeps its shape"},
    {"feature": "Body wall", "prototype": "2.5 mm",
     "production": "3.0 mm moulded PC/ABS (spec); primer, colour, two clear coats, polished to 90 GU or more"},
    {"feature": "Passive radiator", "prototype": "Sealed box, no radiator (radiator layouts only for comparison)",
     "production": "Rear passive radiator, about 60 × 40 mm oval, behind a perforated gold cover and bezel matching "
                   "the front (spec, user Oct 2026), with black acoustic fabric behind it like the front grille; the "
                   "concept base (gold cup + small foot) and the sealed collar USB-C port are kept"},
    {"feature": "Grille", "prototype": "1.2 mm photo-etched stainless, 2.2 mm hexagons, 0.7 mm webs, recess floor "
                                       "painted black",
     "production": "0.5 mm stainless (spec), same 2.2 mm hexagons and 0.7 mm webs, so every web and hole is at least "
                   "the sheet thickness (photo-etching limit) and the look is unchanged; black acoustic fabric "
                   "behind it (spec) in a 0.4 mm pocket"},
    {"feature": "Gold parts", "prototype": "Mixed: anodised aluminium, plated zinc, PVD stainless, brass",
     "production": "Gold PVD, fine brushed satin, on every visible metal part, one matched tone (ΔE ≤ 1.5); copper-"
                   "nickel base on zinc, nickel on brass (spec, user Oct 2026)"},
    {"feature": "Knob", "prototype": "Ø18 plain disc, 5 mm proud",
     "production": "Faro's knob: solid brass Ø20, fine straight knurl, smooth R1 front edge, the Bathsheva emblem "
                   "engraved tone-on-tone (gold groove floor under the PVD); the emblem turns with the knob; "
                   "0.3 mm gap to the body (spec)"},
    {"feature": "Fin tips", "prototype": "Bare gold tips on the ground",
     "production": "1 mm TPU pad under each tip (spec); the fins sit 1 mm higher, the height to the nose stays 280"},
    {"feature": "Fin fixing", "prototype": "M4 bolts through round holes in the shell",
     "production": "M4 screws from the chassis through vertical slots in the shell into cast bosses (spec)"},
    {"feature": "Nose cone", "prototype": "Slip-fit spigot",
     "production": "Spigot with an O-ring groove (modelled); bayonet with a hidden detent (spec; not modelled yet)"},
    {"feature": "Joint lines", "prototype": "0.4 mm shadow-line chamfers",
     "production": "0.3 mm (spec: seams 0.3 ±0.1 mm, flush within 0.1 mm)"},
    {"feature": "Base collar", "prototype": "Slip-fit plug; the battery stands on its spigot",
     "production": "Screws up into a 3 mm steel battery-tray plate with three M2.5 countersunk screws on a Ø11 circle, "
                   "hidden under the foot; the foot screws onto an M4 stud by hand. Two more M2.5 countersunk screws at "
                   "the plate's edge hold it to the ballast cup. Battery replaceable after removing the base collar: "
                   "foot off by hand, 3 screws, collar off, 2 screws, the tray drops out with the battery, unplug it "
                   "(1.5 mm hex key only; user, Oct 2026)"},
    {"feature": "Name", "prototype": "None",
     "production": "\"ATELIER\" etched 0.15 mm tone-on-tone round the foot on the collar's underside, Cormorant "
                   "Garamond SemiBold 2.4 mm, seen only when lifted (user, Oct 2026)"},
    {"feature": "Mass", "prototype": "1.8 kg target; ballast auto-sized",
     "production": "1.8 ±0.1 kg (spec) with production materials (Zamak 5 fins and collar, 6061 nose cone and "
                   "bezels, brass knob, PC/ABS body); the steel ballast cup is resized to reach it"},
]
# Design changes from route_changes.yaml that the CAD shows (none for Atelier yet).
IMPLEMENTED_CHANGES: dict[str, set[str]] = {}

# What the model doesn't settle yet: shown in the DFM report and the CAD tab, for the user and suppliers.
OPEN_ITEMS: list[str] = [
    "Driver and radiator mounting: the spec has the chassis carry them; the model keeps the prototype's moulded "
    "seats in the shell. The moulder and the electronics supplier should propose the chassis brackets.",
    "Nose-cone bayonet and hidden detent: specified, not modelled.",
    "Moulding the body: the belly is wider than both openings, so it needs a collapsible core or two welded halves.",
    "Antenna: the Bluetooth module should sit on the spine near the top, behind the red PC/ABS (radio-transparent) "
    "and away from the steel chassis, gold grille and PVD trim; the module supplier must confirm range (10 m).",
]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _coerce(params: dict[str, Any], res: ValidationResult) -> dict[str, float]:
    p: dict[str, float] = {}
    for d in PARAMS:
        if d.key not in params:
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


def _profile_r(t: float, body_max_dia: float) -> float:
    """Body radius at height fraction t (0 = bottom of the red body, 1 = nose-cone joint)."""
    from scipy.interpolate import PchipInterpolator

    tt = [q[0] for q in proto.BODY_PROFILE_POINTS]
    rr = [q[1] for q in proto.BODY_PROFILE_POINTS]
    return body_max_dia / 2 * float(PchipInterpolator(tt, rr)(min(1.0, max(0.0, t))))


def derived(p: dict[str, float]) -> dict[str, float]:
    """Dimensions that follow from the parameters without building (fast)."""
    H, z0, ch = p["overall_height"], p["base_clearance"], p["nose_cone_height"]
    bh = H - z0 - ch
    tg = (p["grille_height"] - z0) / bh
    rg = _profile_r(tg, p["body_max_diameter"])
    return {"body_height": bh, "cone_frac": ch / bh, "grille_frac": tg, "body_r_at_grille": rg,
            "grille_dia_frac": p["grille_diameter"] / (2 * rg), "body_top_r": _profile_r(1.0, p["body_max_diameter"]),
            "body_bottom_r": _profile_r(0.0, p["body_max_diameter"]),
            "fin_span": 2 * p["fin_tip_radius"] * math.sin(math.radians(60)) + p["fin_thickness"]}


def validate(params: dict[str, Any], wall_limits: dict[str, WallLimit] | None = None,
             min_tip_deg: float | None = None) -> ValidationResult:
    """Ranges and inter-dependencies before regeneration (fast: nothing is built). Stability and mass are
    checked on the built model (`stability`)."""
    res = ValidationResult()
    p = _coerce(params, res)
    if res.errors:
        return res
    err = lambda param, msg: res.errors.append(ValidationIssue(param, msg))  # noqa: E731
    warn = lambda param, msg: res.warnings.append(ValidationIssue(param, msg, "warning"))  # noqa: E731
    d = derived(p)
    if d["body_height"] < 120:
        err("nose_cone_height", "The red body would be shorter than 120 mm; lower the base clearance or the nose cone")
    if not 0.12 <= d["cone_frac"] <= 0.35:
        err("nose_cone_height", f"The nose cone is {d['cone_frac']:.0%} of the body height (allowed 12–35%)")
    if not 0.45 <= d["grille_frac"] <= 0.85:
        err("grille_height", "The grille centre must sit in the upper half of the body (45–85% of its height)")
    if not 0.6 <= d["grille_dia_frac"] <= 0.9:
        err("grille_diameter", f"The grille is {d['grille_dia_frac']:.0%} of the body width there (allowed 60–90%)")
    opening = p["grille_diameter"] - 2 * proto.GRILLE_LEDGE
    if opening < proto.DRIVER_DIA + 2 * proto.DRIVER_CLEARANCE:
        err("grille_diameter", f"The sound opening (Ø{opening:.1f}) must pass the {proto.DRIVER_DIA:g} mm driver, "
            "which is fitted from the front")
    if p["grille_thickness"] > HEX_WEB:
        err("grille_thickness", f"Photo-etching needs webs at least the sheet thickness: {HEX_WEB:g} mm webs allow "
            f"{HEX_WEB:g} mm sheet at most")
    if p["fin_tip_radius"] < p["body_max_diameter"] / 2 + 20:
        err("fin_tip_radius", "The fin tips must reach at least 20 mm beyond the body's widest point")
    if abs(p["overall_height"] - 280) > 1:
        warn("overall_height", "The Technical Specification asks for 280 ±1 mm")
    if abs(p["body_max_diameter"] - 95) > 0.5:
        warn("body_max_diameter", "The Technical Specification asks for Ø95 ±0.5 mm")
    if abs(p["target_mass_kg"] - 1.8) > 0.1:
        warn("target_mass_kg", "The Technical Specification asks for 1.8 ±0.1 kg")
    if not 130 <= d["fin_span"] <= 150:
        warn("fin_tip_radius", f"Fin span about {d['fin_span']:.0f} mm; the spec says about 140")
    for key, param in (("body", "wall_thickness"),):
        lim = (wall_limits or {}).get(key)
        if lim is None:
            continue
        v = p[param]
        flag = "" if lim.verified else " (unverified)"
        if not lim.min <= v <= lim.max:
            err(param, f"{v:g} mm is outside what {lim.process_name.lower()} can make ({lim.min:g}–{lim.max:g} mm){flag}")
        elif not lim.typical_min <= v <= lim.typical_max:
            warn(param, f"{v:g} mm is outside the typical {lim.typical_min:g}–{lim.typical_max:g} mm for "
                        f"{lim.process_name.lower()}{flag}")
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
@lru_cache(maxsize=1)
def _lettering() -> list:
    return json.loads(COLLAR_LETTERING_FILE.read_text())["letters"]


# Material variants for the cost-down scenarios: the build sizes the ballast with these densities, and
# stability() reports mass, centre of mass and tip-over for them. Keys are workbench part keys.
VARIANT_PART_KEY = {"body": "body", "fin": "fins", "collar": "foot", "foot": "foot",
                    "nose_cone": "nose_cone"}  # -> PART_MATERIALS keys
# Cast Jesmonite AC100 body (user, Oct 2026): 3.5 mm general wall, thickened locally to 5 mm at the fin roots
# (bolts and inserts) and round the sound openings. A uniform 5 mm wall left too little air and split the
# ballast cup; at 3.5 mm the cup stays one piece.
JESMONITE_WALL = 3.5
JESMONITE_LOCAL_WALL = 5.0
# Cast-in brass inserts for the driver (4), radiator (4) and fin fixings (3 x 2): about 2 g each.
JESMONITE_INSERTS_G = 14 * 2.0
MATERIAL_VARIANTS: dict[str, dict[str, Any]] = {
    "jesmonite_body": {"materials": {"body": "jesmonite_ac100"}, "wall_thickness": JESMONITE_WALL,
                       "ns": {"LOCAL_WALL": JESMONITE_LOCAL_WALL},
                       "extra_g": {"cast-in brass inserts": JESMONITE_INSERTS_G}},
    # All-Jesmonite (user, Oct 2026): body, nose cone, fins, collar and foot cast in Jesmonite. Solid fins
    # (FIN_WALL 0) with cast-in inserts, cone and collar walls thick enough to cast (about 4–5 mm), spigot ring 3 mm.
    # Cast-in inserts: the body's 14 (28 g), two per fin for the fin bolts (6 x 2 g) and four in the collar
    # (three M2.5 tray screws and the M4 stud, 4 x 1.5 g).
    "all_jesmonite": {"materials": {"body": "jesmonite_ac100", "nose_cone": "jesmonite_ac100", "fin": "jesmonite_ac100",
                                    "collar": "jesmonite_ac100", "foot": "jesmonite_ac100"},
                      "wall_thickness": 5.0,  # as costed and reported (reference only); uniform wall
                      "ns": {"FIN_WALL": 0.0, "CONE_WALL": 5.0, "COLLAR_WALL": 4.0, "CONE_SPIGOT_WALL": 3.0},
                      "extra_g": {"cast-in brass inserts": JESMONITE_INSERTS_G + 6 * 2.0 + 4 * 1.5}},
    "pu_body": {"materials": {"body": "pu_casting_resin"}},
    "brass_metalwork": {"materials": {"fin": "brass", "collar": "brass", "foot": "brass"}},
}


def _variant(keys: tuple[str, ...]) -> tuple[dict[str, Any], dict[str, str], dict[str, float]]:
    """Parameter overrides, part materials and extra masses for a combination of material variants."""
    over: dict[str, Any] = {}
    mats: dict[str, str] = {}
    extra: dict[str, float] = {}
    for k in keys:
        v = MATERIAL_VARIANTS[k]
        mats.update(v.get("materials", {}))
        extra.update(v.get("extra_g", {}))
        if "wall_thickness" in v:
            over["wall_thickness"] = v["wall_thickness"]
    return over, mats, extra


def _variant_ns(keys: tuple[str, ...]) -> dict[str, float]:
    """Prototype-parameter overrides (e.g. a solid fin) for a combination of material variants."""
    out: dict[str, float] = {}
    for k in keys:
        out.update(MATERIAL_VARIANTS[k].get("ns", {}))
    return out


def namespace(params: dict[str, Any], variant: tuple[str, ...] = ()) -> types.SimpleNamespace:
    """The prototype's parameters with production values and the workbench parameters applied."""
    p = {k: float(v) for k, v in params.items()}
    d = derived(p)
    ns = types.SimpleNamespace(**{k: copy.deepcopy(getattr(proto, k)) for k in dir(proto) if k.isupper()})
    H = p["overall_height"]
    ns.OVERALL_HEIGHT = H
    ns.BODY_MAX_DIA = p["body_max_diameter"]
    ns.BASE_CLEARANCE_FRAC = p["base_clearance"] / H
    ns.CONE_HEIGHT_FRAC = d["cone_frac"]
    ns.WALL = p["wall_thickness"]
    ns.GRILLE_Z_FRAC = d["grille_frac"]
    ns.GRILLE_DIA_FRAC = d["grille_dia_frac"]
    ns.GRILLE_THICK = p["grille_thickness"]
    ns.GRILLE_RECESS = max(0.1, p["grille_thickness"] - GRILLE_PROUD)
    ns.GRILLE_BACKING, ns.GRILLE_BACKING_THICK = "cloth", FABRIC_T
    ns.HEX_PATTERN_ENABLED = bool(int(p["grille_perforated"]))
    ns.HEX_HOLE, ns.HEX_WEB, ns.PRINT_HEX_WEB = HEX_HOLE, HEX_WEB, HEX_WEB  # no print-only variant
    ns.FIN_TIP_REACH_FRAC = p["fin_tip_radius"] / (p["body_max_diameter"] / 2)
    ns.FIN_ROOT_THICK = ns.FIN_TIP_THICK = p["fin_thickness"]
    ns.FIN_EDGE_FILLET = min(proto.FIN_EDGE_FILLET, p["fin_thickness"] / 2 - 0.2)
    ns.FIN_PAD, ns.FIN_BOLT_SLOT = FIN_PAD_T, FIN_BOLT_SLOT
    ns.KNOB_DIA, ns.KNOB_BODY_GAP = p["knob_diameter"], KNOB_GAP
    ns.PR_POSITION, ns.PR_W, ns.PR_H, ns.PR_MASS = "rear", p["pr_width"], p["pr_height"], PR_MASS_G
    ns.USBC_POSITION = "collar"
    ns.JOINT_SHADOW_LINE = SHADOW_LINE
    ns.CONE_SPIGOT_WALL, ns.CONE_ORING_GROOVE = CONE_SPIGOT_WALL, CONE_ORING_GROOVE
    ns.BATTERY_TRAY_T = BATTERY_TRAY_T
    ns.COLLAR_SCREWS, ns.COLLAR_SCREW_PCD = COLLAR_SCREWS, COLLAR_SCREW_PCD
    ns.COLLAR_SCREW_CLEAR, ns.COLLAR_SCREW_HEAD, ns.COLLAR_SCREW_TAP = COLLAR_SCREW_CLEAR, COLLAR_SCREW_HEAD, COLLAR_SCREW_TAP
    ns.FOOT_STUD_TAP, ns.FOOT_STUD_DEPTH = FOOT_STUD_TAP, FOOT_STUD_DEPTH
    ns.TRAY_SCREW_DEPTH = TRAY_SCREW_DEPTH
    ns.COLLAR_LETTERING, ns.COLLAR_LETTERING_CAP, ns.COLLAR_LETTERING_DEPTH = _lettering(), LETTERING_CAP, LETTERING_DEPTH
    _, mats, extra = _variant(variant)
    # Masses with no body of their own (e.g. cast-in inserts) come off the ballast.
    ns.TARGET_MASS_G = p["target_mass_kg"] * 1000 - sum(extra.values())
    ns.MATERIAL_DENSITY = dict(DENSITY)
    ns.PART_MATERIALS = {**PART_MATERIALS, **{VARIANT_PART_KEY[k]: m for k, m in mats.items()}}
    for name, value in _variant_ns(variant).items():
        setattr(ns, name, value)
    ns.BATTERY_MASS, ns.DRIVER_MASS, ns.PCB_MASS = BATTERY_MASS_G, DRIVER_MASS_G, BOARD_MASS_G
    return ns


@dataclass
class Model:
    parts: dict[str, Shape] = field(default_factory=dict)  # one solid per part key (fin and fin_pad once)
    instances: dict[str, list[Shape]] = field(default_factory=dict)  # fin and fin_pad at 180° and 300°
    preview: dict[str, Shape] = field(default_factory=dict)  # preview-only bodies (groove floors, LED)
    info: dict[str, Any] = field(default_factory=dict)
    envelopes: dict[str, Shape] = field(default_factory=dict)
    geometry: Any = None  # the ported prototype Model (envelopes, profile functions)


def build_model(params: dict[str, Any], variant: tuple[str, ...] = ()) -> Model:
    ns = namespace(params, variant)
    g = geo.build(ns)
    I = g.info
    parts: dict[str, Shape] = {}
    parts["body"] = g.parts["body"]
    parts["nose_cone"] = g.parts["nose_cone"]
    parts["fin"] = g.parts["fin_1"]
    pads = I.get("fin_pads", [])
    parts["fin_pad"] = pads[0]
    parts["collar"] = g.parts["collar"]
    parts["foot"] = g.parts["foot"]
    parts["grille"] = g.parts["grille"]
    parts["grille_fabric"] = g.parts["grille_backing"]
    parts["bezel"] = g.parts["bezel"]
    parts["rear_grille"] = g.parts["rear_grille"]
    parts["rear_bezel"] = g.parts["rear_bezel"]
    parts["rear_fabric"] = g.parts["rear_grille_backing"]
    parts["knob"] = g.parts["knob"]
    parts["chassis"] = g.parts["chassis"]
    parts["ballast"] = g.parts["ballast"]
    parts["driver"] = g.envelopes["driver"]
    parts["passive_radiator"] = g.envelopes["passive_radiator"]
    parts["battery"] = g.envelopes["battery"]
    bw, bd, bhh = BOARD_SIZE
    px, py, pz = I["pcb_pos"]
    parts["main_board"] = Pos(px, py - 6.0 + bd / 2, pz) * Box(bw, bd, bhh)  # on the spine's rear face
    instances = {"fin": [g.parts["fin_2"], g.parts["fin_3"]], "fin_pad": pads[1:]}
    preview = {"knob_logo_floor": g.envelopes["knob_logo_floor"], "led": g.envelopes["led"]}
    if "collar_etch_floor" in g.envelopes:
        preview["collar_etch_floor"] = g.envelopes["collar_etch_floor"]
    return Model(parts=parts, instances=instances, preview=preview, info=I, envelopes=g.envelopes, geometry=g)


@lru_cache(maxsize=4)
def _cached(params_json: str, variant: tuple[str, ...] = ()) -> Model:
    return build_model(json.loads(params_json), variant)


def model(params: dict[str, Any], variant: tuple[str, ...] = ()) -> Model:
    """One build per parameter set and material variant (the honeycomb grilles take about a minute)."""
    over, _, _ = _variant(variant)
    return _cached(json.dumps(normalise({**params, **over}), sort_keys=True), tuple(sorted(variant)))


def build(params: dict[str, Any]) -> dict[str, Shape]:
    return dict(model(params).parts)


def _instance_copies(parts: dict[str, Shape]) -> dict[str, Shape]:
    """The second and third fin and pad: the first rotated by 120° and 240° about the axis."""
    out = {}
    for key, n in INSTANCES.items():
        if key in parts:
            for k in range(1, n):
                out[f"{key}_{k + 1}"] = Rot(0, 0, 360 * k / n) * copy.copy(parts[key])
    return out


def assembly(parts: dict[str, Shape], name: str = "atelier") -> Compound:
    """A labelled, coloured compound for STEP and glTF export, with all three fins and pads."""
    kids = []
    for key, shape in {**parts, **_instance_copies(parts)}.items():
        s = copy.copy(shape)
        s.label = key
        s.color = Color(*PART_COLOURS.get(key.rsplit("_", 1)[0] if key[-1].isdigit() else key, (0.7, 0.7, 0.7, 1.0)))
        kids.append(s)
    return Compound(children=kids, label=name)


def preview_extras(params: dict[str, Any]) -> dict[str, tuple[Shape, tuple]]:
    """Preview-only bodies for the GLB: the other two fins and pads, the knob emblem's and the collar
    lettering's groove floors, and the status LED."""
    m = model(params)
    out = {k: (s, PART_COLOURS[k.rsplit("_", 1)[0]]) for k, s in _instance_copies(m.parts).items()}
    out.update({k: (m.preview[k], col) for k, col in PREVIEW_EXTRA_COLOURS.items() if k in m.preview})
    return out


def preview_two_tone(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {}


def public_derived(params: dict[str, Any]) -> dict[str, Any]:
    """Derived dimensions for the API (fast: from the parameters, no build)."""
    p = {k: float(v) for k, v in params.items()}
    d = derived(p)
    return {k: round(v, 2) for k, v in d.items()}


def derived_traits(part_key: str, params: dict[str, Any]) -> list[str]:
    return []


def implements(change_key: str, cad_key: str | None, bodies: set[str]) -> bool:
    need = IMPLEMENTED_CHANGES.get(change_key)
    return need is not None and need <= bodies


def estimate_mass(part_info: dict[str, Any], densities: dict[str, float]) -> dict[str, Any]:
    """Mass from CAD volumes (mm³) and densities (g/cm³) per part key; fins and pads count three times.

    With the body present it adds what `stability()` also counts but has no body of its own: the butyl
    damping pads and the sealed USB-C receptacle, so the CAD tab and the DFM report give the same mass."""
    per = {k: round(info["volume_mm3"] / 1000 * densities[k] / 1000 * INSTANCES.get(k, 1), 3)
           for k, info in part_info.items() if k in densities}
    if "body" in per:
        per["damping_pads_and_usb"] = round((proto.BUTYL_MASS_G + proto.USBC_RECEPTACLE_MASS) / 1000, 3)
    return {"total_kg": round(sum(per.values()), 3), "parts_kg": per}


# ---------------------------------------------------------------------------
# Mass, centre of mass, tip-over and air volume (on the built model)
# ---------------------------------------------------------------------------
# Production material per part key, for the stability calculation (the build's own densities).
PART_DENSITY_KEY = {"body": "pc_abs", "nose_cone": "aluminium", "fin": "zamak_5", "fin_pad": "tpu",
                    "collar": "zamak_5", "foot": "zamak_5", "grille": "stainless_304", "grille_fabric": "acoustic_cloth",
                    "bezel": "aluminium", "rear_grille": "stainless_304", "rear_bezel": "aluminium",
                    "rear_fabric": "acoustic_cloth", "knob": "brass",
                    "chassis": "steel", "ballast": "steel"}
BOUGHT_IN_MASS_G = {"driver": DRIVER_MASS_G, "passive_radiator": PR_MASS_G, "battery": BATTERY_MASS_G,
                    "main_board": BOARD_MASS_G}


@lru_cache(maxsize=8)
def _stability(params_json: str, variant: tuple[str, ...] = ()) -> dict[str, Any]:
    from build123d import CenterOf

    params = json.loads(params_json)
    m = model(params, variant)
    _, mats, extra = _variant(variant)
    density_key = {**PART_DENSITY_KEY, **mats}
    rows, total, moment = [], 0.0, np.zeros(3)

    def add(name: str, mass: float, c) -> None:
        nonlocal total, moment
        rows.append({"part": name, "mass_g": round(mass, 1)})
        total += mass
        moment += mass * np.array([c.X, c.Y, c.Z])

    for key, shape in m.parts.items():
        if key in density_key:
            rho = DENSITY[density_key[key]]
            for k, s in enumerate([shape] + m.instances.get(key, [])):
                add(key if k == 0 else f"{key}_{k + 1}", s.volume / 1000 * rho, s.center(CenterOf.MASS))
        elif key in BOUGHT_IN_MASS_G:
            add(key, BOUGHT_IN_MASS_G[key], shape.center(CenterOf.MASS))
    body_c = m.parts["body"].center(CenterOf.MASS)
    add("butyl damping pads", proto.BUTYL_MASS_G, body_c)
    for name, grams in extra.items():
        add(name, grams, body_c)
    if "usb_receptacle" in m.envelopes:
        add("USB-C receptacle (sealed)", proto.USBC_RECEPTACLE_MASS, m.envelopes["usb_receptacle"].center(CenterOf.MASS))
    com = moment / total

    # Tip-over: the speaker stands on its three pads; it falls once the centre of mass passes over the line
    # between two of them. Angle = atan(distance from the CoM to that line / CoM height).
    tips = m.info["fin_tips"]
    edges = []
    for i in range(len(tips)):
        (x1, y1), (x2, y2) = tips[i], tips[(i + 1) % len(tips)]
        dist = abs((x2 - x1) * (com[1] - y1) - (y2 - y1) * (com[0] - x1)) / math.hypot(x2 - x1, y2 - y1)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        edges.append({"angle_deg": round(math.degrees(math.atan2(dist, com[2])), 1),
                      "towards_deg": round(math.degrees(math.atan2(mx, -my)) % 360)})
    worst = min(edges, key=lambda e: e["angle_deg"])

    # Air in the box: the body's inner cavity minus everything in it, plus the hollow nose cone (open to the
    # body through its spigot), less the butyl pads.
    air = m.envelopes["body_cavity"]
    for key in ("body", "chassis", "ballast", "driver", "passive_radiator", "battery", "main_board", "collar"):
        air = air - m.parts[key]
    air_envelopes_l = (air.volume + m.info["cone_cavity_volume"]) / 1e6 - proto.BUTYL_MASS_G / proto.BUTYL_DENSITY / 1000
    back = ((1 - DRIVER_DISPLACEMENT_FRAC) * (m.parts["driver"] & m.envelopes["body_cavity"]).volume
            + (1 - PR_DISPLACEMENT_FRAC) * (m.parts["passive_radiator"] & m.envelopes["body_cavity"]).volume)
    air_l = air_envelopes_l + back / 1e6
    bb = Compound(list(m.parts.values()) + [s for v in m.instances.values() for s in v]).bounding_box()
    return {"total_g": round(total, 1), "com_mm": [round(float(v), 1) for v in com], "tip_deg": worst["angle_deg"],
            "tip_towards_deg": worst["towards_deg"], "edges": edges, "air_l": round(air_l, 3),
            "air_envelopes_l": round(air_envelopes_l, 3),
            "height_mm": round(bb.max.Z - bb.min.Z, 2), "footprint_mm": [round(bb.size.X, 1), round(bb.size.Y, 1)],
            "ballast_g": round(m.info.get("ballast_mass", 0.0), 1), "ballast_max_g": round(m.info.get("ballast_max_g", 0.0), 1),
            "parts": rows}


def stability(params: dict[str, Any], variant: tuple[str, ...] = ()) -> dict[str, Any]:
    """Mass, centre of mass, worst tip-over angle, footprint and air volume of the built model.

    `variant` names MATERIAL_VARIANTS (e.g. a cast Jesmonite body): their materials, wall and extra masses
    are applied and the ballast is re-sized to the target mass."""
    over, _, _ = _variant(variant)
    return _stability(json.dumps(normalise({**params, **over}), sort_keys=True), tuple(sorted(variant)))


# Below this much spare ballast (g) the 1.8 kg target is at risk if supplier parts come in lighter than estimated.
MASS_MARGIN_MIN_G = 50.0
# Battery replacement after removing the base collar (user, Oct 2026): every step with standard tools.
BATTERY_SERVICE = [
    "Unscrew the foot by hand (it screws onto an M4 stud).",
    "Undo the three M2.5 countersunk screws under it (1.5 mm hex key) and take off the base collar; unplug the "
    "USB-C lead at its connector.",
    "Undo the two M2.5 countersunk screws at the edge of the steel tray plate (same key); the plate drops out with "
    "the battery standing on it.",
    "Unplug the battery's connector and fit the new pack; reassemble in reverse (threadlocker on the M4 stud only).",
]

# Specification limits checked on the built model.
SPEC = {"height_mm": (279.0, 281.0), "mass_g": (1700.0, 1900.0), "com_max_mm": 98.0, "tip_min_deg": 18.0,
        "air_l": (0.70, 0.80), "foot_clearance_mm": 2.0}


def production_change_checks(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Check the built solids against the PRODUCTION_CHANGES rows (and the spec limits) that geometry can prove."""
    p = {k: float(v) for k, v in params.items()}
    m = model(params)
    parts, I = m.parts, m.info
    s = stability(params)
    out = []

    def check(feature: str, ok: bool, detail: str) -> None:
        out.append({"feature": feature, "ok": bool(ok), "detail": detail})

    bb = parts["body"].bounding_box()
    check("Body diameter", abs(bb.size.X - p["body_max_diameter"]) < 0.3,
          f"body Ø{bb.size.X:.1f} mm at its widest (parameter {p['body_max_diameter']:g})")
    lo, hi = SPEC["height_mm"]
    check("Height", lo <= s["height_mm"] <= hi, f"{s['height_mm']:.1f} mm ground to nose tip (spec 280 ±1)")
    lo, hi = SPEC["mass_g"]
    check("Mass", lo <= s["total_g"] <= hi,
          f"{s['total_g'] / 1000:.2f} kg with production materials (spec 1.8 ±0.1); ballast {s['ballast_g']:.0f} g")
    check("Centre of mass", s["com_mm"][2] <= SPEC["com_max_mm"],
          f"{s['com_mm'][2]:.1f} mm above the ground (spec ≤ {SPEC['com_max_mm']:g})")
    check("Stability", s["tip_deg"] >= SPEC["tip_min_deg"],
          f"tips over at {s['tip_deg']:.1f}° (worst, towards {s['tip_towards_deg']}°; spec ≥ {SPEC['tip_min_deg']:g}°)")
    lo, hi = SPEC["air_l"]
    check("Passive radiator", lo <= s["air_l"] <= hi and "passive_radiator" in parts,
          f"rear radiator {p['pr_width']:g} × {p['pr_height']:g} mm; about {s['air_l']:.2f} L of air (spec 0.7–0.8 L) "
          f"with typical driver and radiator displacement ({s['air_envelopes_l']:.2f} L if they were solid)")
    gt = parts["grille"].bounding_box()
    check("Grille", p["grille_thickness"] <= HEX_WEB and "grille_fabric" in parts and "rear_fabric" in parts,
          f"{p['grille_thickness']:g} mm sheet, {HEX_HOLE:g} mm holes, {HEX_WEB:g} mm webs; fabric behind the front "
          "grille and the rear cover")
    from app.cad import faro as _faro

    check("Knob", I.get("knob_logo_mm3", 0) > 0,
          f"Ø{p['knob_diameter']:g}, {_faro.knurl_teeth(p['knob_diameter'])} knurl teeth, emblem engraved "
          f"({I.get('knob_logo_mm3', 0):.1f} mm³)")
    zmin_fin = min(f.bounding_box().min.Z for f in [parts["fin"]] + m.instances["fin"])
    check("Fin tips", abs(zmin_fin - FIN_PAD_T) < 0.05 and parts["fin_pad"].bounding_box().min.Z < 0.01,
          f"fins stand {zmin_fin:.2f} mm up on {FIN_PAD_T:g} mm pads")
    foot_gap = parts["foot"].bounding_box().min.Z
    check("Foot clearance", abs(foot_gap - SPEC["foot_clearance_mm"]) < 0.05, f"foot {foot_gap:.2f} mm off the ground")
    check("Nose cone", "cone_oring_groove" in I, "O-ring groove on the spigot; bayonet not modelled")
    check("Base collar", len(I.get("collar_screw_xy", [])) == COLLAR_SCREWS and len(I.get("tray_screw_xy", [])) == 2,
          f"{len(I.get('collar_screw_xy', []))} × M2.5 on Ø{COLLAR_SCREW_PCD:g} under the Ø{I['foot_dia']:.1f} foot; "
          f"tray plate on 2 × M2.5 at R{abs(sum(I.get('tray_screw_xy', [(0, 0)])[0])):.1f}, outside the battery")
    check("Name", I.get("collar_lettering_mm3", 0) > 0.3,
          f"\"ATELIER\" etched {LETTERING_DEPTH:g} mm on R{I.get('collar_lettering_radius', 0):.1f} "
          f"({I.get('collar_lettering_mm3', 0):.2f} mm³)")
    return out
