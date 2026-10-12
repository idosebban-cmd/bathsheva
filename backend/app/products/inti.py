"""INTI, the head-shaped home Bluetooth speaker: its registry entry and the checks only INTI has."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.cad import inti
from app.cad.validation import ValidationResult, WallLimit
from app.products import CheckFn, Product
from app.services.templates import load_template

if TYPE_CHECKING:
    from app.models import Project
    from app.rules.data import RuleSet


def validate(params: dict[str, Any], wall_limits: dict[str, WallLimit], rules: "RuleSet") -> ValidationResult:
    return inti.validate(params, wall_limits)


def dfm_checks(project: "Project", params: dict[str, Any], rules: "RuleSet", _check: CheckFn) -> list[dict[str, Any]]:
    """What the concept leaves open: placeholder dimensions, the template's TBD list and the model's open items."""
    checks: list[dict[str, Any]] = [_check(
        "Geometry", "warning", "Placeholder dimensions",
        "No dimension has been given for INTI: every CAD parameter is a placeholder so the massing model builds, "
        "and the head is an ellipsoid stand-in for the sculpt. Volumes, masses and costs from the CAD are "
        "indicative only.", unverified=True)]
    for t in load_template("inti").get("tbd", []):
        checks.append(_check("Specification", "warning", f"TBD: {t['topic']}", f"{t['item']}. {t['why']}",
                             unverified=True))
    from app.services.electrical import project_runtime

    rt = project_runtime(project)
    if not rt.get("applicable"):
        checks.append(_check("Electrical", "info", "Playback time", rt.get("reason", "Not estimated."), part="Battery pack"))
    for c in rt.get("compliance", []):
        checks.append(_check("Electrical", "warning", "Compliance", c, unverified=True))
    for item in inti.OPEN_ITEMS:
        checks.append(_check("Assembly", "warning", "Open item", item, unverified=True))
    checks.append(_check(
        "Process", "info", "Model simplifications relative to the concept",
        "; ".join(f"{c['feature']}: {c['production']}" for c in inti.PRODUCTION_CHANGES[:4]) + ". Full list in the CAD tab."))
    return checks


PRODUCT = Product(
    key="inti",
    label="INTI",
    summary="head-shaped home Bluetooth speaker",
    noun="speaker",
    generator=inti,
    validate=validate,
    wall_limit_parts={"body": None},
    wall_params={"body": "wall_thickness"},
    dfm_checks=dfm_checks,
    # The driver, battery and board have no specified mass: left out of the estimate (TBD).
    bought_in_density={},
    factory_pack="",
    cad_note="INTI massing placeholder from the concept render: cream Jesmonite head (an ellipsoid stand-in for the "
             "sculpt) with the brass/gold brow-and-nose piece, two eyes, stepped front grille, two side dials, top "
             "rim and base ring, and the rear USB-C and aux panel. Every dimension is a placeholder (TBD). Each eye "
             "and dial is modelled once and mirrored. The driver, battery and board are space-only placeholders.",
)
