from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_project
from app.models import Project
from app.services.dfm import build_dfm, dfm_markdown

router = APIRouter(prefix="/api/projects/{project_id}", tags=["dfm"])


@router.get("/dfm")
def get_dfm(project: Project = Depends(get_project)):
    return build_dfm(project)


@router.get("/dfm.md")
def get_dfm_markdown(project: Project = Depends(get_project)):
    return Response(
        dfm_markdown(project),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{project.slug}_dfm.md"'},
    )
