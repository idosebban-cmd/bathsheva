"""Revisions: create and read only (snapshots are immutable)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.db import get_session
from app.models import Project
from app.schemas import RevisionCreate, RevisionOut, RevisionSummary
from app.services.revisions import create_revision

router = APIRouter(prefix="/api/projects/{project_id}/revisions", tags=["revisions"])


@router.get("", response_model=list[RevisionSummary])
def list_revisions(project: Project = Depends(get_project)):
    return list(reversed(project.revisions))


@router.post("", response_model=RevisionOut, status_code=201)
def save_revision(body: RevisionCreate, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    return create_revision(session, project, body.note)


@router.get("/{number}", response_model=RevisionOut)
def get_revision(number: int, project: Project = Depends(get_project)):
    for rev in project.revisions:
        if rev.number == number:
            return rev
    raise HTTPException(404, "Revision not found")
