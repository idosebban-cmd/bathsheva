"""Battery runtime for a project: the template's electrical model against the runtime requirement."""

from __future__ import annotations

from typing import Any

from app import electrical
from app.models import Project
from app.services.templates import load_template


def electrical_spec(project: Project) -> dict[str, Any] | None:
    return load_template(project.template).get("electrical") if project.template else None


def project_runtime(project: Project) -> dict[str, Any]:
    """Estimated runtime at full brightness, the target, and the battery compliance flags."""
    spec = electrical_spec(project)
    req = project.requirements or {}
    power = req.get("power_type", "undecided")
    if spec is None:
        return {"applicable": False, "reason": "This project has no electrical model."}
    if power not in ("battery", "undecided"):
        return {"applicable": False, "reason": f"Power type is {power}: no battery runtime.", "compliance": []}
    present = {p.cad_key for p in project.parts if p.cad_key}
    removed = {ld["part"] for ld in spec.get("loads", []) if ld.get("part") and ld["part"] not in present}
    target = req.get("battery_runtime_h")
    est = electrical.estimate(spec, target, removed)
    has_tower_light = any(ld.get("part") == "tower_light" and ld["part"] not in removed for ld in spec.get("loads", []))
    lantern_only = electrical.estimate(spec, target, removed | {"tower_light"}) if has_tower_light else {"hours": None}
    return {
        "applicable": True,
        **est,
        "target_assumed": "battery_runtime_h" in (project.assumed_fields or []),
        "without_tower_light_h": lantern_only["hours"],
        "compliance": list(spec.get("compliance", [])),
    }
