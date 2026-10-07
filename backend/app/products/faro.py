"""Faro, the lighthouse table lamp: its registry entry and the checks only Faro has."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.cad import faro
from app.cad.validation import ValidationResult, WallLimit
from app.products import CheckFn, Product

if TYPE_CHECKING:
    from app.models import Project
    from app.rules.data import RuleSet


def validate(params: dict[str, Any], wall_limits: dict[str, WallLimit], rules: "RuleSet") -> ValidationResult:
    return faro.validate(params, wall_limits, rules.plan("min_stability_ratio"))


def draft(cad_key: str, params: dict[str, Any]) -> tuple[str, float | None] | None:
    """The tower is a tapered cone (its taper is the draft); base, cap and band have vertical walls."""
    if cad_key == "tower":
        return "taper", faro.body_taper_deg(params)
    if cad_key in ("base", "cap", "band_cream"):
        return "vertical", None
    return None


def dfm_checks(project: "Project", params: dict[str, Any], rules: "RuleSet", _check: CheckFn) -> list[dict[str, Any]]:
    """Stability, LED clearance, windows, runtime, construction, twist-lock fit and mass."""
    from app.services.cad import latest_model

    checks: list[dict[str, Any]] = []
    latest = latest_model(project)
    p = {k: float(v) for k, v in params.items()}
    ratio = p["base_diameter"] / p["overall_height"]
    min_ratio = rules.plan("min_stability_ratio")
    checks.append(_check(
        "Geometry", "pass" if ratio >= min_ratio else "warning", "Stability (heuristic)",
        f"Base diameter is {ratio:.0%} of overall height (heuristic minimum {min_ratio:.0%}). "
        "The real requirement is a tilt test on the finished lamp.", unverified=True, part="Base"))

    clearance = faro.led_clearance(params)
    min_clear = rules.plan("min_led_to_lantern_clearance_mm")
    checks.append(_check(
        "Thermal", "pass" if clearance >= min_clear else "warning", "LED to lantern clearance",
        f"About {clearance:.0f} mm between the LED emitter and the frosted glass (heuristic minimum {min_clear} mm). "
        "A 1.5 W LED runs cool; confirm temperatures by test once the LED is chosen.", unverified=True, part="Lantern glass"))

    d = faro.derived({k: float(v) for k, v in params.items()})
    n_win = int(p["window_count"])
    if n_win:
        checks.append(_check(
            "Process", "warning", f"{n_win} tower windows: laser-cut after spinning",
            "The arched windows are cut into the spun cone with a 5-axis laser (or a fixture), then deburred and "
            "masked for lacquer. Ask the spinner whether they cut in-house; scenario b shows what the windows cost.",
            unverified=True, part="Tower"))
        checks.append(_check(
            "Assembly", "info", "Window diffuser and tower light",
            f"One opal borosilicate tube Ø{d['diffuser_od']:.0f} mm stands on a silicone ring behind all {n_win} windows; "
            "the tower light (LED filament strips on a spine) sits inside it. Insert both before the tower is bonded.",
            unverified=True, part="Window diffuser"))

    from app.services.electrical import project_runtime

    rt = project_runtime(project)
    if rt.get("applicable"):
        if rt["hours"] is not None:
            lvl = {"pass": "pass", "close": "warning", "fail": "fail"}.get(rt["status"], "info")
            tgt = f" vs target {rt['target_h']:g} h" if rt.get("target_h") else ""
            checks.append(_check(
                "Electrical", lvl, "Battery runtime at full brightness",
                f"About {rt['hours']:.1f} h{tgt} ({rt['battery_wh']:.1f} Wh battery, {rt['load_w']:.1f} W of LEDs: "
                + ", ".join(f"{ld['name']} {ld['watts']:g} W" for ld in rt["loads"]) + "). " + rt["note"],
                unverified=rt["unverified"], part="Battery pack"))
        for c in rt.get("compliance", []):
            checks.append(_check("Electrical", "warning", "Battery compliance", c, unverified=True, part="Battery pack"))

    checks.append(_check(
        "Assembly", "pass", "Construction (no central rod)",
        "Three M3 screws clamp the weight plate and base to the turned cream band; the tower and gallery are bonded "
        "on turned spigots; the cap twist-locks onto the lantern (four lugs, 20° turn) and lifts off to reach the LED. "
        "The bottom plate is on four M2.5 screws so the battery is user-replaceable.",
        unverified=True, part="Base"))
    if latest is not None:
        try:
            bay = faro.model(latest.parameters).info.get("bayonet", {})
        except Exception:  # pragma: no cover - geometry kernel failure
            bay = {}
        if bay:
            ok = not bay.get("locked_clash_mm3") and not bay.get("entry_clash_mm3") and bay.get("led_lifts_out")
            checks.append(_check(
                "Assembly", "pass" if ok else "fail", "Cap twist-lock fit",
                f"Locked clash {bay.get('locked_clash_mm3', 0):g} mm³, entry clash {bay.get('entry_clash_mm3', 0):g} mm³, "
                f"{bay.get('lug_under_lip_mm', 0):g} mm of lug under the lip; the LED lifts out with the cap off: "
                f"{'yes' if bay.get('led_lifts_out') else 'no'}.", part="Cap bayonet spigot"))
    checks.append(_check(
        "Process", "info", "Prototype features adapted for metal production",
        "; ".join(f"{c['feature']}: {c['production']}" for c in faro.PRODUCTION_CHANGES[:6]) + ". Full list in the CAD tab.",
        part=None))

    from app.services.cad import mass_estimate

    mass = mass_estimate(project)
    if mass and mass["target_kg"]:
        level = {"ok": "pass", "low": "warning", "high": "warning"}.get(mass["status"], "info")
        hint = {"low": " Increase the weight plate thickness or diameter.", "high": " Lighter than this may be fine; check the target."}
        checks.append(_check(
            "Geometry", level, "Lamp mass vs target",
            f"Estimated {mass['total_kg']:.2f} kg vs target {mass['target_kg']:.2f} kg "
            f"(weight plate {mass['parts_kg'].get('weight_plate', 0):.2f} kg).{hint.get(mass['status'], '')}",
            unverified=True, part="Weight plate"))
    return checks


# Rough densities (g/cm³) for bought-in bodies, used only for the lamp-mass estimate.
# Electronics are placeholder envelopes, so their "density" turns the envelope into a
# typical mass (2 x 18650 cells about 95 g; the boards and LED about 10-20 g each).
BOUGHT_IN_DENSITY = {
    "weight_plate": ("steel_s275", 7.85), "base_plate": ("al_5052", 2.68), "felt_pad": (None, 0.5),
    "battery": (None, 2.1), "charge_board": (None, 1.8), "led_module": (None, 2.0),
    "tower_light": (None, 0.6), "dimmer": (None, 2.0),
}

PRODUCT = Product(
    key="faro",
    label="Faro",
    summary="lighthouse lamp",
    noun="lamp",
    generator=faro,
    validate=validate,
    wall_limit_parts={"tower": "aluminium_wall_mm", "lantern_glass": None},
    wall_params={"tower": "wall_thickness", "base": "wall_thickness", "cap": "wall_thickness",
                 "lantern_glass": "glass_wall_thickness"},
    draft=draft,
    dfm_checks=dfm_checks,
    bought_in_density=BOUGHT_IN_DENSITY,
    factory_pack=True,
)
