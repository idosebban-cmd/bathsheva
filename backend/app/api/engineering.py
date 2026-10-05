"""Rules-based recommendations, decisions and optional LLM explanations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.provider import LLMUnavailable, get_provider
from app.api.deps import get_project
from app.config import settings
from app.db import get_session
from app.models import EngineeringDecision, Part, Project
from app.schemas import DecisionIn, DecisionOut
from app.services.recommendations import open_project_decisions, project_recommendations

router = APIRouter(prefix="/api/projects/{project_id}", tags=["engineering"])


@router.get("/recommendations")
def recommendations(project: Project = Depends(get_project)) -> dict[str, Any]:
    return {
        "recommendations": project_recommendations(project),
        "open_decisions": open_project_decisions(project),
        "llm": {"enabled": settings.llm_provider != "none", "provider": settings.llm_provider},
    }


@router.post("/recommendations/{part_id}/explain")
def explain(part_id: int, project: Project = Depends(get_project)) -> dict[str, Any]:
    provider = get_provider()
    if provider is None:
        raise HTTPException(503, "LLM is disabled. Set ANTHROPIC_API_KEY to enable explanations.")
    rec = next((r for r in project_recommendations(project) if r["part_id"] == part_id), None)
    if rec is None:
        raise HTTPException(404, "Part not found")
    try:
        explanation = provider.explain(rec)
    except LLMUnavailable as e:
        raise HTTPException(502, str(e)) from e
    return {"provider": provider.name, "explanation": explanation.model_dump()}


@router.get("/decisions", response_model=list[DecisionOut])
def list_decisions(project: Project = Depends(get_project)):
    return sorted(project.decisions, key=lambda d: d.id)


@router.post("/decisions", response_model=DecisionOut, status_code=201)
def record_decision(body: DecisionIn, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    part: Part | None = None
    if body.part_id is not None:
        part = session.get(Part, body.part_id)
        if part is None or part.project_id != project.id:
            raise HTTPException(404, "Part not found")

    chosen = dict(body.chosen)
    if body.topic == "material_process" and part is not None:
        rec = body.recommendation.get("recommendation") or {}
        if body.status == "accepted":
            if not rec:
                raise HTTPException(422, "Cannot accept an empty recommendation")
            chosen = {"material": rec["material_name"], "process": rec["process_name"]}
        if body.status in ("accepted", "edited"):
            if not chosen.get("material") and not chosen.get("process"):
                raise HTTPException(422, "Edited decisions need a material or process")
            part.material = chosen.get("material", part.material)
            part.process = chosen.get("process", part.process)
            if chosen.get("finish"):
                part.finish = chosen["finish"]
    elif body.topic == "power_type":
        value = chosen.get("value")
        if value not in ("mains", "battery", "passive", "undecided"):
            raise HTTPException(422, "power_type decision needs chosen.value of mains/battery/passive/undecided")
        project.requirements = {**project.requirements, "power_type": value}

    decision = EngineeringDecision(
        project_id=project.id,
        part_id=body.part_id,
        topic=body.topic,
        status=body.status,
        recommendation=body.recommendation,
        chosen=chosen,
        note=body.note,
    )
    session.add(decision)
    session.commit()
    session.refresh(project)
    return decision
