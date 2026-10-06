"""Bring a project created from an older version of its template up to date.

Faro's design changed (Oct 2026: the approved prototype became the source of
truth), so projects created before then carry the old parts. The upgrade:

* removes parts the template no longer has (with their quotes and decisions),
* adds the template's new parts,
* updates requirements the template now fixes (dimensions, power, runtime),
* records the template's accepted decisions (also offered when only the decisions changed,
  e.g. Oct 2026: near-net turning, the spun gallery),
* resets the cost line items to the template defaults,
* and leaves CAD history alone (the CAD tab starts from the new defaults).

`plan()` describes what would change without touching anything.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, object_session

from app.models import ExternalQuote, Project
from app.services.templates import load_template

# Requirements the template now fixes; other requirements (prices, markets...) are the user's.
UPDATED_REQUIREMENTS = ["approx_dimensions", "power_type", "battery_runtime_h", "preferred_materials",
                        "preferred_finishes", "functional_requirements"]


def plan(project: Project) -> dict[str, Any]:
    if not project.template:
        return {"needed": False, "remove": [], "add": [], "requirements": [], "decisions": []}
    tpl = load_template(project.template)
    tpl_keys = [p["cad_key"] for p in tpl["parts"]]
    have = {p.cad_key: p for p in project.parts if p.cad_key}
    session = object_session(project)

    def quotes(part_id: int) -> int:
        if session is None:
            return 0
        return session.scalar(select(func.count()).select_from(ExternalQuote).where(ExternalQuote.part_id == part_id)) or 0

    remove = [{"cad_key": k, "name": p.name, "quotes": quotes(p.id)} for k, p in have.items() if k not in tpl_keys]
    add = [{"cad_key": p["cad_key"], "name": p["name"]} for p in tpl["parts"] if p["cad_key"] not in have]
    req = project.requirements or {}
    changed = [k for k in UPDATED_REQUIREMENTS if req.get(k) != tpl["requirements"].get(k)]
    from app.services.decisions import missing_template_decisions

    names = {p["cad_key"]: p["name"] for p in tpl["parts"]}
    decisions = [f"{names.get(d['part'], d['part'])}: {d['process'].replace('_', ' ')} ({d['material'].replace('_', ' ')})"
                 if "part" in d else d["topic"].replace("_", " ") for d in missing_template_decisions(project)]
    return {"needed": bool(remove or add or decisions), "remove": remove, "add": add, "requirements": changed,
            "decisions": decisions}


def upgrade(session: Session, project: Project) -> dict[str, Any]:
    from app.services.costing import reset_items
    from app.services.decisions import apply_template_decisions
    from app.services.projects import template_part

    p = plan(project)
    if not project.template:
        return p
    tpl = load_template(project.template)
    removed = {r["cad_key"] for r in p["remove"]}
    for part in list(project.parts):
        if part.cad_key in removed:
            session.delete(part)
    have = {pt.cad_key for pt in project.parts if pt.cad_key and pt.cad_key not in removed}
    order = {spec["cad_key"]: i for i, spec in enumerate(tpl["parts"])}
    for spec in tpl["parts"]:
        if spec["cad_key"] not in have:
            project.parts.append(template_part(spec, order[spec["cad_key"]]))
    for part in project.parts:
        if part.cad_key in order:
            part.sort_order = order[part.cad_key]
    req = dict(project.requirements or {})
    for k in UPDATED_REQUIREMENTS:
        if k in tpl["requirements"]:
            req[k] = tpl["requirements"][k]
    project.requirements = req
    tpl_assumed = set(tpl.get("assumed_fields", []))
    project.assumed_fields = [f for f in (project.assumed_fields or []) if f not in UPDATED_REQUIREMENTS or f in tpl_assumed]
    session.commit()
    session.expire_all()  # decisions and quotes of removed parts went with them (ON DELETE CASCADE)
    session.refresh(project)
    apply_template_decisions(session, project)
    reset_items(session, project)
    session.refresh(project)
    return {**p, "done": True}
