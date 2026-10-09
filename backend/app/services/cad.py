"""CAD orchestration: current parameters, validation against rules, generation."""

from __future__ import annotations

import shutil
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.cad import export
from app.cad.validation import ValidationResult, WallLimit
from app.config import settings
from app.models import CadModel, CadOutput, Project
from app.products import product_for
from app.rules.data import load_rules
from app.rules.match import match_process
from app.services.templates import load_template


def generator_for(project: Project):
    product = product_for(project)
    if product is None:
        raise HTTPException(404, "This project has no parametric CAD generator (only template projects such as Faro do)")
    return product.generator


def latest_model(project: Project) -> CadModel | None:
    return project.cad_models[-1] if project.cad_models else None


def current_parameters(project: Project) -> dict[str, Any]:
    defaults = dict(load_template(project.template)["cad_parameters"])
    latest = latest_model(project)
    if latest is not None:
        product = product_for(project)
        gen = product.generator if product is not None else None
        params = dict(latest.parameters)
        return gen.upgrade(params, defaults) if gen is not None else params
    return defaults


def mass_estimate(project: Project, part_info: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Estimated product mass from CAD volumes vs the target mass parameter."""
    product = product_for(project)
    if product is None:
        return None
    from app.services.costing import part_geometry, snapshot_material_keys

    info = part_info or part_geometry(project)[0]
    if not info:
        return None
    rules = load_rules()
    mats = snapshot_material_keys(project)
    densities: dict[str, float] = {}
    for key in info:
        mk = mats.get(key)
        m = rules.materials.get(mk or "")
        if m is not None and m.density_g_cm3:
            densities[key] = m.density_g_cm3
        elif key in product.bought_in_density:
            rk, fallback = product.bought_in_density[key]
            rm = rules.materials.get(rk or "")
            densities[key] = rm.density_g_cm3 if rm is not None and rm.density_g_cm3 else fallback
        elif mk == "brass":
            densities[key] = 8.5
    est = product.generator.estimate_mass(info, densities)
    target = float(current_parameters(project).get("target_mass_kg") or 0) or None
    status = "unknown"
    if target:
        status = "low" if est["total_kg"] < target * 0.95 else ("high" if est["total_kg"] > target * 1.25 else "ok")
    return {**est, "target_kg": target, "status": status,
            "note": "Estimate from CAD volumes and typical densities; electronics, cable and finish are approximate."}


def wall_limits(project: Project) -> dict[str, WallLimit]:
    """Wall limits per CAD part from the process set on that part (or a general range from the planning rules)."""
    rules = load_rules()
    limits: dict[str, WallLimit] = {}
    product = product_for(project)
    if product is None:
        return limits
    by_key = {p.cad_key: p for p in project.parts if p.cad_key}
    for part_key, fallback in product.wall_limit_parts.items():
        part = by_key.get(part_key)
        proc_key = match_process(rules, part.process) if part else None
        if proc_key and rules.processes[proc_key].wall_mm:
            proc = rules.processes[proc_key]
            w = proc.wall_mm
            limits[part_key] = WallLimit(proc.name, w.min, w.max, w.typical_min, w.typical_max, proc.verified)
        elif fallback:
            gen = rules.planning[fallback]
            label = fallback.removesuffix("_wall_mm").replace("_", " ")
            limits[part_key] = WallLimit(
                f"general {label}", gen.value["min"], gen.value["max"], gen.value["min"], gen.value["max"], gen.verified
            )
    return limits


def validate(project: Project, params: dict[str, Any]) -> ValidationResult:
    generator_for(project)
    product = product_for(project)
    return product.validate(params, wall_limits(project), load_rules())


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
        files += export.export_assembly(gen.assembly(parts, project.slug), parts, out_dir, project.slug,
                                        colours=gen.PART_COLOURS, two_tone=gen.preview_two_tone(params),
                                        extras=gen.preview_extras(params))
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
