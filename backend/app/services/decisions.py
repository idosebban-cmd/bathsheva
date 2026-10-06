"""Engineering decisions a product template records on new projects (accepted by the user)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.costing.assemble import route_changes_for
from app.costing.data import load_cost_data
from app.models import EngineeringDecision, Project
from app.rules.data import load_rules
from app.services.templates import load_template


def route_decision_chosen(project: Project, part: Any, process_key: str, material_key: str,
                          previous_process: str = "", previous_material: str = "") -> dict[str, Any]:
    """The `chosen` record for a process-route decision, with the design changes the route needs."""
    rules, cost = load_rules(), load_cost_data()
    from app.cad import faro

    traits = set(part.traits or [])
    if project.template == "faro" and part.cad_key:
        from app.services.cad import current_parameters

        traits |= set(faro.derived_traits(part.cad_key, current_parameters(project)))
    changes = route_changes_for(cost, process_key, traits)
    latest = project.cad_models[-1] if project.cad_models else None
    proc, mat = rules.processes[process_key], rules.materials[material_key]
    chosen = {
        "process_key": process_key, "process": proc.name, "material_key": material_key, "material": mat.name,
        "previous_process": previous_process, "previous_material": previous_material,
        "design_changes": [" ".join(rc.design_change.split()) for rc in changes],
        "design_change_keys": [rc.key for rc in changes],
        "cad_version": latest.version if latest else None,
    }
    chosen["cad_mismatch"] = bool(unimplemented_changes(project, part.cad_key, chosen["design_change_keys"]))
    return chosen


def unimplemented_changes(project: Project, cad_key: str | None, keys: list[str]) -> list[str]:
    """Design changes the project's CAD doesn't show yet (latest generated model, or the current generator)."""
    if project.template != "faro":
        return list(keys)
    from app.cad import faro

    latest = project.cad_models[-1] if project.cad_models else None
    bodies = set(latest.part_info) if latest is not None else set(faro.PART_KEYS)
    return [k for k in keys if not faro.implements(k, cad_key, bodies)]


def missing_template_decisions(project: Project) -> list[dict[str, Any]]:
    """The template's accepted decisions that the project hasn't recorded yet."""
    if not project.template:
        return []
    tpl = load_template(project.template)
    by_key = {p.cad_key: p for p in project.parts if p.cad_key}
    existing = {(d.topic, d.part_id, (d.chosen or {}).get("process_key") or (d.chosen or {}).get("value"))
                for d in project.decisions}
    out = []
    for spec in tpl.get("decisions", []):
        if "part" in spec:
            part = by_key.get(spec["part"])
            if part is None or ("process_route", part.id, spec["process"]) in existing:
                continue
        elif (spec["topic"], None, spec["chosen"].get("value")) in existing:
            continue
        out.append(spec)
    return out


def apply_template_decisions(session: Session, project: Project) -> list[EngineeringDecision]:
    """Record the template's accepted decisions that the project doesn't have yet (idempotent)."""
    by_key = {p.cad_key: p for p in project.parts if p.cad_key}
    rules = load_rules()
    added = []
    for spec in missing_template_decisions(project):
        reason = " ".join(spec["reason"].split())
        if "part" in spec:
            part = by_key[spec["part"]]
            chosen = route_decision_chosen(project, part, spec["process"], spec["material"], part.process, part.material)
            d = EngineeringDecision(project_id=project.id, part_id=part.id, topic="process_route", status="accepted",
                                    recommendation={}, chosen=chosen, note=reason)
            part.process = rules.processes[spec["process"]].name
            part.material = rules.materials[spec["material"]].name
        else:
            d = EngineeringDecision(project_id=project.id, part_id=None, topic=spec["topic"], status="accepted",
                                    recommendation={}, chosen=dict(spec["chosen"]), note=reason)
        session.add(d)
        added.append(d)
    session.commit()
    session.refresh(project)
    return added
