"""Parts (hierarchical component list)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.db import get_session
from app.config import settings
from app.models import ExternalQuote, Part, Project
from app.schemas import PartCreate, PartOut, PartUpdate

router = APIRouter(prefix="/api/projects/{project_id}/parts", tags=["parts"])


def _get_part(project: Project, part_id: int, session: Session) -> Part:
    part = session.get(Part, part_id)
    if part is None or part.project_id != project.id:
        raise HTTPException(404, "Part not found")
    return part


def _check_parent(project: Project, part_id: int | None, parent_id: int | None, session: Session) -> None:
    if parent_id is None:
        return
    seen = {part_id}
    current: int | None = parent_id
    while current is not None:
        if current in seen:
            raise HTTPException(422, "Parent would create a cycle")
        parent = _get_part(project, current, session)
        seen.add(current)
        current = parent.parent_id


@router.get("", response_model=list[PartOut])
def list_parts(project: Project = Depends(get_project)):
    return project.parts


@router.post("", response_model=PartOut, status_code=201)
def create_part(body: PartCreate, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    _check_parent(project, None, body.parent_id, session)
    data = body.model_dump()
    if not data["sort_order"]:
        data["sort_order"] = max((p.sort_order for p in project.parts), default=-1) + 1
    part = Part(project_id=project.id, **data)
    session.add(part)
    session.commit()
    return part


@router.patch("/{part_id}", response_model=PartOut)
def update_part(part_id: int, body: PartUpdate, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    part = _get_part(project, part_id, session)
    changes = body.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        _check_parent(project, part.id, changes["parent_id"], session)
    for key, value in changes.items():
        setattr(part, key, value)
    session.commit()
    return part


@router.delete("/{part_id}", status_code=204)
def delete_part(part_id: int, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    part = _get_part(project, part_id, session)
    for quote in session.query(ExternalQuote).filter(ExternalQuote.part_id == part.id):
        if quote.attachment_path:
            (settings.data_dir / quote.attachment_path).unlink(missing_ok=True)
    session.delete(part)
    session.commit()
