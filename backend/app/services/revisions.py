"""Immutable revision snapshots of a project."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Project, Revision
from app.schemas import CadModelOut, DecisionOut, ImageOut, PartOut
from app.services.cad import current_parameters, latest_model
from app.services.recommendations import project_recommendations

SNAPSHOT_SCHEMA = 1


def build_snapshot(project: Project) -> dict[str, Any]:
    latest = latest_model(project)
    return {
        "schema": SNAPSHOT_SCHEMA,
        "project": {"name": project.name, "description": project.description, "template": project.template},
        "requirements": project.requirements,
        "assumed_fields": project.assumed_fields,
        "cad_parameters": current_parameters(project) if project.template else None,
        "cad_model": CadModelOut.model_validate(latest).model_dump(mode="json") if latest else None,
        "parts": [PartOut.model_validate(p).model_dump(mode="json") for p in project.parts],
        "decisions": [DecisionOut.model_validate(d).model_dump(mode="json") for d in sorted(project.decisions, key=lambda d: d.id)],
        "recommendations": project_recommendations(project),
        "images": [ImageOut.model_validate(i).model_dump(mode="json") for i in project.images],
    }


def create_revision(session: Session, project: Project, note: str) -> Revision:
    number = (project.revisions[-1].number + 1) if project.revisions else 1
    rev = Revision(project_id=project.id, number=number, note=note, snapshot=build_snapshot(project))
    session.add(rev)
    session.commit()
    session.refresh(project)
    return rev
