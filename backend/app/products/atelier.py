"""Atelier, the rocket Bluetooth speaker: its registry entry and the checks only Atelier has."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.cad import atelier
from app.cad.validation import ValidationResult, WallLimit
from app.products import CheckFn, Product

if TYPE_CHECKING:
    from app.models import Project
    from app.rules.data import RuleSet


def validate(params: dict[str, Any], wall_limits: dict[str, WallLimit], rules: "RuleSet") -> ValidationResult:
    return atelier.validate(params, wall_limits)


def dfm_checks(project: "Project", params: dict[str, Any], rules: "RuleSet", _check: CheckFn) -> list[dict[str, Any]]:
    """Mass, centre of mass, tip-over and air volume on the built model; runtime; open items."""
    checks: list[dict[str, Any]] = []
    if not atelier.validate(params).ok:
        return checks
    try:
        s = atelier.stability(params)
    except Exception as e:  # pragma: no cover - geometry kernel failure
        return [_check("Geometry", "fail", "Atelier model failed to build", str(e))]
    spec = atelier.SPEC
    target = float(params["target_mass_kg"]) * 1000
    lo, hi = spec["mass_g"]
    checks.append(_check(
        "Geometry", "pass" if lo <= s["total_g"] <= hi else "fail", "Mass vs target",
        f"{s['total_g'] / 1000:.2f} kg with production materials vs {target / 1000:.2f} kg (spec 1.8 ±0.1 kg); the steel "
        f"ballast cup is {s['ballast_g']:.0f} g (at most {s['ballast_max_g']:.0f} g fits below the driver).",
        unverified=True, part="Ballast cup"))
    checks.append(_check(
        "Geometry", "pass" if s["com_mm"][2] <= spec["com_max_mm"] else "fail", "Centre of mass",
        f"{s['com_mm'][2]:.1f} mm above the ground (spec {spec['com_max_mm']:g} mm or lower).", unverified=True))
    checks.append(_check(
        "Geometry", "pass" if s["tip_deg"] >= spec["tip_min_deg"] else "fail", "Stability (static tip-over)",
        f"Tips over at {s['tip_deg']:.1f}° in the worst direction (towards {s['tip_towards_deg']}°, 0 = front) on its "
        f"three fin pads; spec {spec['tip_min_deg']:g}° or more (IEC 62368-1 tilts 10°). Verify on a sample.",
        unverified=True, part="Fin"))
    lo, hi = spec["air_l"]
    checks.append(_check(
        "Acoustics", "pass" if lo <= s["air_l"] <= hi else "warning", "Air volume",
        f"About {s['air_l']:.2f} L of air in the box with the rear passive radiator (spec 0.7–0.8 L): the cavity "
        "less the battery, ballast, chassis and board, plus the hollow nose cone, with the driver displacing about "
        f"{atelier.DRIVER_DISPLACEMENT_FRAC:.0%} of its envelope and the radiator {atelier.PR_DISPLACEMENT_FRAC:.0%} "
        f"(typical; {s['air_envelopes_l']:.2f} L if both were solid). The driver supplier's net volumes replace this.",
        unverified=True, part="Passive radiator"))

    from app.services.electrical import project_runtime

    rt = project_runtime(project)
    if rt.get("applicable") and rt["hours"] is not None:
        lvl = {"pass": "pass", "close": "warning", "fail": "fail"}.get(rt["status"], "info")
        tgt = f" vs target {rt['target_h']:g} h" if rt.get("target_h") else ""
        checks.append(_check(
            "Electrical", lvl, "Playback time at 50% volume",
            f"About {rt['hours']:.1f} h{tgt} ({rt['battery_wh']:.1f} Wh battery, {rt['load_w']:.2f} W average: "
            + ", ".join(f"{ld['name']} {ld['watts']:g} W" for ld in rt["loads"]) + "). Average music power is an "
            "estimate; confirm with the chosen module, amplifier and driver.", unverified=rt["unverified"],
            part="Battery pack"))
        for c in rt.get("compliance", []):
            checks.append(_check("Electrical", "warning", "Compliance", c, unverified=True))
    checks.append(_check(
        "Electrical", "warning", "20 W from a 1S battery",
        "2 x 18650 in parallel give about 3.6 V; 20 W RMS needs a boost converter ahead of the Class-D amplifier and a "
        "driver rated for it. The electronics supplier must confirm (user, Oct 2026).", unverified=True,
        part="Main board"))
    for item in atelier.OPEN_ITEMS:
        checks.append(_check("Assembly", "warning", "Open item", item, unverified=True))
    checks.append(_check(
        "Process", "info", "Prototype features changed for production",
        "; ".join(f"{c['feature']}: {c['production']}" for c in atelier.PRODUCTION_CHANGES[:5]) + ". Full list in the CAD tab."))
    return checks


# Typical densities for bought-in bodies (g/cm³): placeholder envelopes are given the mass of the part they
# stand for (driver 65 g, radiator 60 g, battery 100 g, board 30 g).
BOUGHT_IN_DENSITY = {
    "chassis": ("steel_s275", 7.85), "ballast": ("steel_s275", 7.85), "fin_pad": ("tpu", 1.2),
    "grille_fabric": (None, 0.5), "rear_fabric": (None, 0.5), "driver": (None, 0.85), "passive_radiator": (None, 2.12),
    "battery": (None, 2.19), "main_board": (None, 1.56),
}

PRODUCT = Product(
    key="atelier",
    label="Atelier",
    summary="rocket Bluetooth speaker",
    noun="speaker",
    generator=atelier,
    validate=validate,
    wall_limit_parts={"body": None},
    wall_params={"body": "wall_thickness", "grille": "grille_thickness", "rear_grille": "grille_thickness"},
    dfm_checks=dfm_checks,
    bought_in_density=BOUGHT_IN_DENSITY,
    factory_pack=False,
    cad_note="Atelier as approved in the prototype, with the Technical Specification: lacquered PC/ABS body; gold PVD on "
             "every visible metal part (Zamak fins, collar and foot, 6061 nose cone and bezels, brass knob, stainless "
             "grilles); rear passive radiator. One body per part: each fin and its pad is modelled once and shown three "
             "times. The driver, radiator, battery and board are placeholders showing space and position. The honeycomb "
             "grilles take about a minute to build.",
    mass_part="ballast",
)
