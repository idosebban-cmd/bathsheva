"""Acoustics and power for a project: the template's audio spec against the CAD box volume."""

from __future__ import annotations

from typing import Any

from app import audio
from app.models import Project
from app.products import product_for
from app.services.templates import load_template


def project_audio(project: Project) -> dict[str, Any]:
    product = product_for(project)
    spec = load_template(project.template).get("audio") if project.template else None
    if product is None or spec is None or product.box_volume_l is None:
        return {"applicable": False, "reason": "This project has no acoustic model."}
    from app.services.cad import current_parameters

    params = current_parameters(project)
    if not product.generator.validate(params).ok:
        return {"applicable": False, "reason": "The CAD parameters are invalid, so there is no box volume."}
    box = product.box_volume_l(params)
    battery = (load_template(project.template).get("electrical") or {}).get("battery")
    return {"applicable": True, **audio.evaluate(spec, box, battery),
            "driver": spec["driver"].get("name", ""), "radiator": spec["passive_radiator"].get("name", "")}
