"""Export generated CAD to STEP / STL / GLB files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cadquery as cq

STL_TOLERANCE = 0.05  # mm, linear deflection
STL_ANGULAR = 0.2  # radians


@dataclass
class ExportedFile:
    part_key: str | None  # None = assembly
    format: str
    path: Path


def export_part(shape: cq.Workplane, directory: Path, key: str) -> list[ExportedFile]:
    directory.mkdir(parents=True, exist_ok=True)
    step = directory / f"{key}.step"
    stl = directory / f"{key}.stl"
    cq.exporters.export(shape, str(step), exportType="STEP")
    cq.exporters.export(shape, str(stl), exportType="STL", tolerance=STL_TOLERANCE, angularTolerance=STL_ANGULAR)
    return [ExportedFile(key, "step", step), ExportedFile(key, "stl", stl)]


def export_assembly(asm: cq.Assembly, parts: dict[str, cq.Workplane], directory: Path, name: str) -> list[ExportedFile]:
    directory.mkdir(parents=True, exist_ok=True)
    step = directory / f"{name}_assembly.step"
    stl = directory / f"{name}_assembly.stl"
    glb = directory / f"{name}_assembly.glb"
    asm.export(str(step), exportType="STEP")
    compound = cq.Compound.makeCompound([s.val() for s in parts.values()])
    cq.exporters.export(cq.Workplane().add(compound), str(stl), exportType="STL",
                        tolerance=STL_TOLERANCE, angularTolerance=STL_ANGULAR)
    asm.export(str(glb), exportType="GLTF", tolerance=STL_TOLERANCE * 2, angularTolerance=STL_ANGULAR)
    return [ExportedFile(None, "step", step), ExportedFile(None, "stl", stl), ExportedFile(None, "glb", glb)]


def part_info(parts: dict[str, cq.Workplane]) -> dict[str, Any]:
    """Bounding box size and volume per part (mm, mm³)."""
    info: dict[str, Any] = {}
    for key, shape in parts.items():
        solid = shape.val()
        bb = solid.BoundingBox()
        info[key] = {
            "size_mm": [round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2)],
            "z_range_mm": [round(bb.zmin, 2), round(bb.zmax, 2)],
            "volume_mm3": round(solid.Volume(), 1),
            "valid": bool(solid.isValid()),
        }
    return info
