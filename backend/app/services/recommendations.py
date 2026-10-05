"""Glue between projects (DB) and the pure rules engine."""

from __future__ import annotations

from typing import Any

from app.cad import faro
from app.models import EngineeringDecision, Part, Project
from app.rules.data import load_rules
from app.rules.engine import Context, recommend
from app.services.cad import current_parameters
from app.services.templates import load_template


def context_for(project: Project) -> Context:
    req = project.requirements or {}
    params: dict[str, Any] = {}
    joints: list[dict[str, Any]] = []
    if project.template:
        params = current_parameters(project)
        joints = load_template(project.template).get("joints", [])
    return Context(
        power_type=req.get("power_type", "undecided"),
        production_volume=req.get("production_volume"),
        cad_parameters=params,
        joints=joints,
    )


def part_input(part: Part, ctx: Context, template: str | None) -> dict[str, Any]:
    derived: list[str] = []
    if template == "faro" and part.cad_key and ctx.cad_parameters:
        derived = faro.derived_traits(part.cad_key, ctx.cad_parameters)
    return {
        "id": part.id,
        "cad_key": part.cad_key,
        "name": part.name,
        "material_category": part.material_category,
        "finish": part.finish,
        "traits": list(part.traits or []),
        "derived_traits": derived,
        "open_questions": list(part.open_questions or []),
    }


def latest_decisions(project: Project) -> dict[int, EngineeringDecision]:
    out: dict[int, EngineeringDecision] = {}
    for d in sorted(project.decisions, key=lambda d: (d.updated_at, d.id)):
        if d.part_id is not None and d.topic == "material_process":
            out[d.part_id] = d
    return out


def project_recommendations(project: Project) -> list[dict[str, Any]]:
    rules = load_rules()
    ctx = context_for(project)
    decisions = latest_decisions(project)
    recs = []
    for part in project.parts:
        rec = recommend(rules, part_input(part, ctx, project.template), ctx)
        d = decisions.get(part.id)
        rec["decision"] = (
            {"id": d.id, "status": d.status, "chosen": d.chosen, "note": d.note, "updated_at": d.updated_at.isoformat()}
            if d else None
        )
        recs.append(rec)
    return recs


def open_project_decisions(project: Project) -> list[dict[str, Any]]:
    """Project-level open decisions from the template (e.g. power type) with current status."""
    if not project.template:
        return []
    out = []
    for od in load_template(project.template).get("open_decisions", []):
        value = (project.requirements or {}).get(od["topic"])
        out.append({**od, "current": value, "open": value in (None, "undecided")})
    return out
