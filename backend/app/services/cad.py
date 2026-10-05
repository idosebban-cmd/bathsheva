"""CAD orchestration: current parameters, validation against rules, generation."""

from __future__ import annotations

import shutil
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.cad import export, faro
from app.config import settings
from app.models import CadModel, CadOutput, Project
from app.rules.data import load_rules
from app.rules.match import match_process
from app.services.templates import load_template

GENERATORS = {"faro": faro}


def generator_for(project: Project):
    gen = GENERATORS.get(project.template or "")
    if gen is None:
        raise HTTPException(404, "This project has no parametric CAD generator (only template projects such as Faro do)")
    return gen


def latest_model(project: Project) -> CadModel | None:
    return project.cad_models[-1] if project.cad_models else None


def current_parameters(project: Project) -> dict[str, Any]:
    latest = latest_model(project)
    if latest is not None:
        return dict(latest.parameters)
    return dict(load_template(project.template)["cad_parameters"])


def wall_limits(project: Project) -> dict[str, faro.WallLimit]:
    """Wall limits per CAD part from the process set on that part (or a general aluminium range)."""
    rules = load_rules()
    limits: dict[str, faro.WallLimit] = {}
    by_key = {p.cad_key: p for p in project.parts if p.cad_key}
    for part_key in ("main_body", "lantern"):
        part = by_key.get(part_key)
        proc_key = match_process(rules, part.process) if part else None
        if proc_key and rules.processes[proc_key].wall_mm:
            proc = rules.processes[proc_key]
            w = proc.wall_mm
            limits[part_key] = faro.WallLimit(proc.name, w.min, w.max, w.typical_min, w.typical_max, proc.verified)
        elif part_key == "main_body":
            gen = rules.planning["aluminium_wall_mm"]
            limits[part_key] = faro.WallLimit(
                "general aluminium", gen.value["min"], gen.value["max"], gen.value["min"], gen.value["max"], gen.verified
            )
    return limits


def validate(project: Project, params: dict[str, Any]) -> faro.ValidationResult:
    generator_for(project)
    rules = load_rules()
    return faro.validate(params, wall_limits(project), rules.plan("min_stability_ratio"))


def generate(session: Session, project: Project, params: dict[str, Any]) -> CadModel:
    gen = generator_for(project)
    result = validate(project, params)
    if not result.ok:
        raise HTTPException(422, {"message": "Invalid CAD parameters", **result.as_dict()})
    params = gen.normalise(params)

    version = (latest_model(project).version + 1) if project.cad_models else 1
    rel_dir = f"projects/{project.id}/cad/v{version}"
    out_dir = settings.data_dir / rel_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    try:
        parts = gen.build(params)
        files = []
        for key, shape in parts.items():
            files += export.export_part(shape, out_dir / "parts", key)
        files += export.export_assembly(gen.assembly(parts, project.slug), parts, out_dir, project.slug)
        info = export.part_info(parts)
    except Exception as e:  # geometry kernel failure
        shutil.rmtree(out_dir, ignore_errors=True)
        raise HTTPException(422, {"message": f"CAD generation failed: {e}", "errors": [], "warnings": []}) from e

    model = CadModel(
        project_id=project.id,
        version=version,
        generator=gen.GENERATOR,
        parameters=params,
        part_info=info,
        outputs=[
            CadOutput(part_key=f.part_key, format=f.format, path=f.path.relative_to(settings.data_dir).as_posix())
            for f in files
        ],
    )
    session.add(model)
    session.commit()
    session.refresh(project)
    return model
