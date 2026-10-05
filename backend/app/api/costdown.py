"""Cost-down tab: pricing targets, process routes, design-change scenarios, product summary."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.db import get_session
from app.models import CostScenario, Part, Project
from app.services import costdown

router = APIRouter(prefix="/api/projects/{project_id}", tags=["cost-down"])


class RouteSelection(BaseModel):
    process_key: str
    material_key: str
    reason: str = Field(min_length=1)


class ChangeSel(BaseModel):
    key: str
    option: int | None = None


class ScenarioEval(BaseModel):
    changes: list[ChangeSel] = []
    region: str = "uk"


class ScenarioSetIn(ScenarioEval):
    name: str = Field(min_length=1)
    notes: str = ""


class ScenarioSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    changes: list[dict[str, Any]]
    region: str
    notes: str


def _require_template(project: Project) -> None:
    if not project.template:
        raise HTTPException(404, "Cost-down analysis needs a template project (such as Faro)")


@router.get("/pricing")
def get_pricing(project: Project = Depends(get_project)):
    return costdown.pricing_report(project)


@router.put("/pricing")
def put_pricing(changes: dict[str, float], project: Project = Depends(get_project), session: Session = Depends(get_session)):
    return costdown.update_pricing(session, project, changes)


@router.get("/routes")
def get_routes(project: Project = Depends(get_project), session: Session = Depends(get_session)):
    _require_template(project)
    return costdown.part_routes(session, project)


@router.post("/parts/{part_id}/route")
def choose_route(part_id: int, body: RouteSelection, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    part = session.get(Part, part_id)
    if part is None or part.project_id != project.id:
        raise HTTPException(404, "Part not found")
    return costdown.select_route(session, project, part, body.process_key, body.material_key, body.reason)


@router.get("/scenarios")
def get_scenarios(project: Project = Depends(get_project), session: Session = Depends(get_session)):
    _require_template(project)
    return costdown.scenario_catalog(session, project)


@router.post("/scenarios/evaluate")
def evaluate(body: ScenarioEval, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    _require_template(project)
    return costdown.evaluate_selection(session, project, [c.model_dump() for c in body.changes], body.region)


@router.get("/cost-down/summary")
def summary(project: Project = Depends(get_project), session: Session = Depends(get_session)):
    _require_template(project)
    return costdown.product_summary(session, project)


@router.get("/scenario-sets", response_model=list[ScenarioSetOut])
def list_sets(project: Project = Depends(get_project), session: Session = Depends(get_session)):
    return session.query(CostScenario).filter(CostScenario.project_id == project.id).order_by(CostScenario.id).all()


@router.post("/scenario-sets", response_model=ScenarioSetOut, status_code=201)
def save_set(body: ScenarioSetIn, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    _require_template(project)
    # Validate before saving (unknown keys, conflicts, region).
    costdown.evaluate_selection(session, project, [c.model_dump() for c in body.changes], body.region)
    row = CostScenario(project_id=project.id, name=body.name, changes=[c.model_dump() for c in body.changes],
                       region=body.region, notes=body.notes)
    session.add(row)
    session.commit()
    return row


@router.delete("/scenario-sets/{set_id}", status_code=204)
def delete_set(set_id: int, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    row = session.get(CostScenario, set_id)
    if row is None or row.project_id != project.id:
        raise HTTPException(404, "Scenario set not found")
    session.delete(row)
    session.commit()
