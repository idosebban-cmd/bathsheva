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
        f"{s['total_g'] / 1000:.2f} kg with production materials vs {target / 1000:.2f} kg (spec 1.75 ±0.1 kg); the steel "
        f"ballast cup is {s['ballast_g']:.0f} g (at most {s['ballast_max_g']:.0f} g fits below the driver).",
        unverified=True, part="Ballast cup"))
    headroom = s["ballast_max_g"] - s["ballast_g"]
    margin = s["total_g"] + headroom - lo  # how much lighter supplier parts can be before dropping below the spec
    checks.append(_check(
        "Geometry", "pass" if margin >= atelier.MASS_MARGIN_MIN_G else "warning", "Risk: mass margin",
        f"The driver, battery, board and metal parts can come in about {margin:.0f} g lighter than estimated before the "
        f"speaker drops below {lo / 1000:.2f} kg (the spec's lower limit), counting {headroom:.0f} g of ballast that can "
        f"still be added (the cup is {s['ballast_g']:.0f} g of at most {s['ballast_max_g']:.0f} g). Recheck once supplier "
        "part weights arrive; if it gets tight, a denser ballast (brass or copper) or a heavier collar adds margin.",
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
        f"About {s['air_l']:.2f} L of air in the sealed box (spec 0.7–0.8 L): the cavity less the battery, ballast, "
        "chassis and board, plus the hollow nose cone, with the driver displacing about "
        f"{atelier.DRIVER_DISPLACEMENT_FRAC:.0%} of its envelope (typical; {s['air_envelopes_l']:.2f} L if it were "
        "solid). The driver supplier's net volume replaces this.", unverified=True, part="Driver"))

    from app.services.electrical import project_runtime

    rt = project_runtime(project)
    if rt.get("applicable") and rt["hours"] is not None:
        lvl = {"pass": "pass", "close": "warning", "fail": "fail"}.get(rt["status"], "info")
        tgt = f" vs target {rt['target_h']:g} h" if rt.get("target_h") else ""
        checks.append(_check(
            "Electrical", lvl, "Playback time at 50% volume",
            f"About {rt['hours']:.1f} h{tgt} ({rt['battery_wh']:.1f} Wh battery, {rt['load_w']:.2f} W average: "
            + ", ".join(f"{ld['name']} {ld['watts']:g} W" for ld in rt["loads"]) + "). " + rt["note"],
            unverified=rt["unverified"],
            part="Battery pack"))
        for c in rt.get("compliance", []):
            checks.append(_check("Electrical", "warning", "Compliance", c, unverified=True))
    from app.services.audio import project_audio

    au = project_audio(project)
    if au.get("applicable"):
        uv = au["unverified"]
        checks.append(_check(
            "Acoustics", "pass" if au["spl_ok"] and au["driver_power_ok"] else "fail", "Loudness (amplifier-limited)",
            f"About {au['thermal_spl_db']:.0f} dB SPL at 1 m from 20 W into the driver (sensitivity × power; spec "
            f"{au['target_spl_db']:.0f} dB or more). The driver must be rated for the full 20 W.", unverified=uv,
            part="Driver"))
        b_low = next(b for b in au["bass"] if b["f_hz"] == round(au["target_low_hz"]))
        checks.append(_check(
            "Acoustics", "info", "Bass at full volume (excursion)",
            f"The driver reaches {au['target_spl_db']:.0f} dB within its excursion from about {au['full_spl_from_hz']} Hz "
            f"up; at {b_low['f_hz']} Hz it can make about {b_low['driver_db']:.0f} dB. The DSP bass enhancement "
            f"(up to +{au['dsp_bass_boost_db']:g} dB) works at normal listening levels; its excursion limiter holds back "
            "the bass at high volume.", unverified=uv, part="Driver"))
        checks.append(_check(
            "Acoustics", "info", "Box tuning (sealed)",
            f"{au['box_l']:.2f} L sealed box: fc {au['fc_hz']} Hz, Qtc {au['qtc']:.2f}; −3 dB at about {au['f3_hz']} Hz "
            f"and −6 dB at about {au['f6_hz']} Hz from the box alone, about {au['f3_dsp_hz']} Hz and {au['f6_dsp_hz']} Hz "
            f"with the DSP bass enhancement (+{au['dsp_bass_boost_db']:g} dB). The supplier confirms it with the "
            "driver's Thiele-Small values.", unverified=uv, part="Driver"))
        if "peak_current_a" in au:
            checks.append(_check(
                "Electrical", "pass" if au["current_ok"] else "fail", "20 W from a 1S battery",
                f"20 W RMS needs about {au['peak_input_w']:.0f} W in through a boost converter ahead of the Class-D "
                f"amplifier: about {au['peak_current_a']:.1f} A from the battery, {au['peak_cell_current_a']:.1f} A per "
                f"cell (typical limit {au['cell_max_a']:g} A). The electronics supplier must confirm the boost stage, "
                "the cells' rating and the driver (user, Oct 2026).", unverified=True, part="Main board"))
            checks.append(_check(
                "Electrical", "pass" if au["charge_ok"] else "fail", "Charge time",
                f"About {au['charge_h']:.1f} h at {au['charge_power_w']:.1f} W into the cells (USB-C PD up to 20 W, "
                f"limited by the cells' charge rate), spec {au['charge_target_h']:g} h or less; play while charging.",
                unverified=True, part="Battery pack"))
    checks.append(_check(
        "Assembly", "pass", "Battery replacement (standard tools)",
        "Battery replaceable after removing the base collar: " + " ".join(
            f"{i + 1}. {step}" for i, step in enumerate(atelier.BATTERY_SERVICE)) + " Needs a plug-in battery lead and "
        "a USB-C lead connector at the collar (main-board RFQ).", unverified=True, part="Battery pack"))
    for item in atelier.OPEN_ITEMS:
        checks.append(_check("Assembly", "warning", "Open item", item, unverified=True))
    checks.append(_check(
        "Process", "info", "Prototype features changed for production",
        "; ".join(f"{c['feature']}: {c['production']}" for c in atelier.PRODUCTION_CHANGES[:5]) + ". Full list in the CAD tab."))
    return checks


# Typical densities for bought-in bodies (g/cm³): placeholder envelopes are given the mass of the part they
# stand for (driver 65 g, battery 100 g, board 30 g; the radiator 60 g in the comparison variant).
BOUGHT_IN_DENSITY = {
    "chassis": ("steel_s275", 7.85), "ballast": ("steel_s275", 7.85), "fin_pad": ("tpu", 1.2),
    "grille_fabric": (None, 0.5), "driver": (None, 0.85),
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
    wall_params={"body": "wall_thickness", "grille": "grille_thickness"},
    dfm_checks=dfm_checks,
    bought_in_density=BOUGHT_IN_DENSITY,
    factory_pack="app.factory.atelier_pack",
    cad_note="Atelier as approved in the prototype, with the Technical Specification: lacquered PC/ABS body; gold PVD on "
             "every visible metal part (Zamak fins, collar and foot, 6061 nose cone and bezels, brass knob, stainless "
             "grille); sealed box with only the front grille, as the prototype. One body per part: each fin and its pad "
             "is modelled once and shown three times. The driver, battery and board are placeholders showing space and "
             "position. The honeycomb "
             "grilles take about a minute to build.",
    mass_part="ballast",
    box_volume_l=lambda params: atelier.stability(params)["air_l"],
)
