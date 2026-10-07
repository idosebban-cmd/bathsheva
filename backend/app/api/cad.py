"""CAD parameters, validation, generation and downloads."""

from __future__ import annotations

import io
import zipfile
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.config import settings
from app.db import get_session
from app.models import Project
from app.schemas import CadModelOut
from app.services import cad as cad_service

router = APIRouter(prefix="/api/projects/{project_id}/cad", tags=["cad"])


@router.get("")
def cad_state(project: Project = Depends(get_project)) -> dict[str, Any]:
    """Parameter definitions, current values, live validation and the latest model."""
    gen = cad_service.generator_for(project)
    params = cad_service.current_parameters(project)
    latest = cad_service.latest_model(project)
    return {
        "generator": gen.GENERATOR,
        "param_defs": [asdict(d) for d in gen.PARAMS],
        "parameters": params,
        "derived": gen.public_derived(params),
        "production_changes": gen.PRODUCTION_CHANGES,
        "validation": cad_service.validate(project, params).as_dict(),
        "wall_limits": {k: asdict(v) for k, v in cad_service.wall_limits(project).items()},
        "latest": CadModelOut.model_validate(latest).model_dump(mode="json") if latest else None,
        "mass": cad_service.mass_estimate(project),
    }


@router.post("/validate")
def validate(parameters: dict[str, Any] = Body(..., embed=True), project: Project = Depends(get_project)):
    return cad_service.validate(project, parameters).as_dict()


@router.post("/generate", response_model=CadModelOut, status_code=201)
def generate(
    parameters: dict[str, Any] = Body(..., embed=True),
    project: Project = Depends(get_project),
    session: Session = Depends(get_session),
):
    return cad_service.generate(session, project, parameters)


@router.get("/models", response_model=list[CadModelOut])
def list_models(project: Project = Depends(get_project)):
    return project.cad_models


@router.get("/models/{version}", response_model=CadModelOut)
def get_model(version: int, project: Project = Depends(get_project)):
    for m in project.cad_models:
        if m.version == version:
            return m
    raise HTTPException(404, "CAD version not found")


@router.get("/models/{version}/download.zip")
def download_zip(version: int, project: Project = Depends(get_project)):
    model = get_model(version, project)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for out in model.outputs:
            path = settings.data_dir / out.path
            arc = path.name if out.part_key is None else f"parts/{path.name}"
            zf.write(path, arc)
    buf.seek(0)
    filename = f"{project.slug}_cad_v{version}.zip"
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
