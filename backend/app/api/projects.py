"""Projects, requirements and reference images."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.config import settings
from app.db import get_session
from app.models import Project, ReferenceImage
from app.schemas import REQUIREMENT_FIELDS, ImageOut, ProjectCreate, ProjectOut, ProjectSummary, ProjectUpdate
from app.services.projects import create_project

router = APIRouter(prefix="/api/projects", tags=["projects"])

ALLOWED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@router.get("", response_model=list[ProjectSummary])
def list_projects(session: Session = Depends(get_session)):
    return session.scalars(select(Project).order_by(Project.created_at)).all()


@router.post("", response_model=ProjectOut, status_code=201)
def create(body: ProjectCreate, session: Session = Depends(get_session)):
    return create_project(session, body.name, body.description, body.template)


@router.get("/{project_id}", response_model=ProjectOut)
def get(project: Project = Depends(get_project)):
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update(body: ProjectUpdate, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    if body.requirements is not None:
        project.requirements = body.requirements.model_dump()
    if body.assumed_fields is not None:
        unknown = set(body.assumed_fields) - set(REQUIREMENT_FIELDS)
        if unknown:
            raise HTTPException(422, f"Unknown requirement fields: {sorted(unknown)}")
        project.assumed_fields = body.assumed_fields
    session.merge(project)
    session.commit()
    return session.get(Project, project.id)


@router.delete("/{project_id}", status_code=204)
def delete(project: Project = Depends(get_project), session: Session = Depends(get_session)):
    """Delete a project: its database records (parts, CAD versions, quotes, cost items, decisions, revisions,
    images...) cascade with it, then its folder in the data folder (uploads and generated CAD) is removed."""
    from app.services.projects import delete_project

    delete_project(session, project)


@router.post("/{project_id}/images", response_model=ImageOut, status_code=201)
def upload_image(
    file: UploadFile = File(...),
    kind: str = Form("reference"),
    caption: str = Form(""),
    project: Project = Depends(get_project),
    session: Session = Depends(get_session),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(422, f"Unsupported image type {suffix!r}")
    if kind not in {"concept", "reference"}:
        raise HTTPException(422, "kind must be 'concept' or 'reference'")
    rel = Path("projects") / str(project.id) / "images" / f"{uuid.uuid4().hex}{suffix}"
    dest = settings.data_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    image = ReferenceImage(project_id=project.id, filename=file.filename or dest.name, path=rel.as_posix(), kind=kind, caption=caption)
    session.add(image)
    session.commit()
    return image


@router.delete("/{project_id}/images/{image_id}", status_code=204)
def delete_image(image_id: int, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    image = session.get(ReferenceImage, image_id)
    if image is None or image.project_id != project.id:
        raise HTTPException(404, "Image not found")
    (settings.data_dir / image.path).unlink(missing_ok=True)
    session.delete(image)
    session.commit()


@router.get("/{project_id}/runtime")
def get_runtime(project: Project = Depends(get_project)):
    """Estimated battery runtime at full brightness vs the runtime requirement."""
    from app.services.electrical import project_runtime

    return project_runtime(project)


@router.get("/{project_id}/template-upgrade")
def get_template_upgrade(project: Project = Depends(get_project)):
    """What updating the project to its template's current parts would change (nothing is changed)."""
    from app.services.template_upgrade import plan

    return plan(project)


@router.post("/{project_id}/template-upgrade")
def post_template_upgrade(project: Project = Depends(get_project), session: Session = Depends(get_session)):
    """Update the project's parts, fixed requirements, decisions and cost items to the current template."""
    from app.services.template_upgrade import upgrade

    return upgrade(session, project)
