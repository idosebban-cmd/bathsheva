from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_project
from app.models import Project
from app.services.bom import bom_csv, build_bom

router = APIRouter(prefix="/api/projects/{project_id}", tags=["bom"])


@router.get("/bom")
def get_bom(project: Project = Depends(get_project)):
    return build_bom(project)


@router.get("/bom.csv")
def get_bom_csv(project: Project = Depends(get_project)):
    return Response(
        bom_csv(project),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{project.slug}_bom.csv"'},
    )
