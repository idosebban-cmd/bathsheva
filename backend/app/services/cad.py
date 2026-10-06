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
    defaults = dict(load_template(project.template)["cad_parameters"])
    latest = latest_model(project)
    if latest is not None:
        gen = GENERATORS.get(project.template or "")
        params = dict(latest.parameters)
        return gen.upgrade(params, defaults) if gen is not None and hasattr(gen, "upgrade") else params
    return defaults


# Rough densities (g/cm³) for bought-in bodies, used only for the lamp-mass estimate.
# Electronics are placeholder envelopes, so their "density" turns the envelope into a
# typical mass (2 x 18650 cells about 95 g; the boards and LED about 10-20 g each).
BOUGHT_IN_DENSITY = {
    "weight_plate": ("steel_s275", 7.85), "base_plate": ("al_5052", 2.68), "felt_pad": (None, 0.5),
    "battery": (None, 2.1), "charge_board": (None, 1.8), "led_module": (None, 2.0),
    "tower_light": (None, 0.6), "dimmer": (None, 2.0),
}


def mass_estimate(project: Project, part_info: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Estimated lamp mass from CAD volumes vs the target mass parameter."""
    if project.template != "faro":
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
        elif key in BOUGHT_IN_DENSITY:
            rk, fallback = BOUGHT_IN_DENSITY[key]
            rm = rules.materials.get(rk or "")
            densities[key] = rm.density_g_cm3 if rm is not None and rm.density_g_cm3 else fallback
        elif mk == "brass":
            densities[key] = 8.5
    est = faro.estimate_mass(info, densities)
    target = float(current_parameters(project).get("target_mass_kg") or 0) or None
    status = "unknown"
    if target:
        status = "low" if est["total_kg"] < target * 0.95 else ("high" if est["total_kg"] > target * 1.25 else "ok")
    return {**est, "target_kg": target, "status": status,
            "note": "Estimate from CAD volumes and typical densities; electronics, cable and finish are approximate."}


def wall_limits(project: Project) -> dict[str, faro.WallLimit]:
    """Wall limits per CAD part from the process set on that part (or a general aluminium range)."""
    rules = load_rules()
    limits: dict[str, faro.WallLimit] = {}
    by_key = {p.cad_key: p for p in project.parts if p.cad_key}
    for part_key in ("tower", "lantern_glass"):
        part = by_key.get(part_key)
        proc_key = match_process(rules, part.process) if part else None
        if proc_key and rules.processes[proc_key].wall_mm:
            proc = rules.processes[proc_key]
            w = proc.wall_mm
            limits[part_key] = faro.WallLimit(proc.name, w.min, w.max, w.typical_min, w.typical_max, proc.verified)
        elif part_key == "tower":
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
        files += export.export_assembly(gen.assembly(parts, project.slug), parts, out_dir, project.slug,
                                        colours=gen.PART_COLOURS, two_tone=gen.preview_two_tone(params),
                                        extras=gen.preview_extras(params) if hasattr(gen, "preview_extras") else None)
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
