"""Export generated CAD to STEP / STL / GLB files (build123d / OpenCASCADE)."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from build123d import Align, Box, Color, Compound, Pos, Shape, export_gltf, export_step, export_stl

STL_TOLERANCE = 0.05  # mm, linear deflection
STL_ANGULAR = 0.2  # radians
_MIN = (Align.CENTER, Align.CENTER, Align.MIN)


@dataclass
class ExportedFile:
    part_key: str | None  # None = assembly
    format: str
    path: Path


def export_part(shape: Shape, directory: Path, key: str) -> list[ExportedFile]:
    directory.mkdir(parents=True, exist_ok=True)
    step = directory / f"{key}.step"
    stl = directory / f"{key}.stl"
    s = copy.copy(shape)
    s.label = key
    export_step(s, str(step))
    export_stl(shape, str(stl), tolerance=STL_TOLERANCE, angular_tolerance=STL_ANGULAR)
    return [ExportedFile(key, "step", step), ExportedFile(key, "stl", stl)]


def _display_split(parts: dict[str, Shape], colours: dict[str, tuple], two_tone: dict[str, dict[str, Any]],
                   extras: dict[str, tuple[Shape, tuple]] | None = None) -> Compound:
    """Preview-only compound: two-tone parts are split at their colour line into `<key>` (upper)
    and `<key>_lower`, so the GLB shows both lacquers; `extras` adds preview-only bodies (e.g. the
    nameplate's black lettering fill). STEP keeps one body per part."""
    kids = []
    for key, shape in parts.items():
        tone = two_tone.get(key)
        pieces = [(key, shape, colours.get(key, (0.7, 0.7, 0.7, 1.0)))]
        if tone and tone.get("split_z") is not None:
            bb = shape.bounding_box()
            z = tone["split_z"]
            if bb.min.Z < z < bb.max.Z:
                big = max(bb.size.X, bb.size.Y) * 2 + 10
                below = Pos(0, 0, bb.min.Z - 1) * Box(big, big, z - bb.min.Z + 1, align=_MIN)
                lower, upper = shape & below, shape - below
                pieces = [(key, upper, tone["upper"]), (f"{key}_lower", lower, tone["lower"])]
        for name, s, col in pieces:
            s = copy.copy(s)
            s.label = name
            s.color = Color(*col)
            kids.append(s)
    for name, (shape, col) in (extras or {}).items():
        s = copy.copy(shape)
        s.label = name
        s.color = Color(*col)
        kids.append(s)
    return Compound(children=kids, label="preview")


def export_assembly(asm: Compound, parts: dict[str, Shape], directory: Path, name: str,
                    colours: dict[str, tuple] | None = None, two_tone: dict[str, dict[str, Any]] | None = None,
                    extras: dict[str, tuple[Shape, tuple]] | None = None) -> list[ExportedFile]:
    directory.mkdir(parents=True, exist_ok=True)
    step = directory / f"{name}_assembly.step"
    stl = directory / f"{name}_assembly.stl"
    glb = directory / f"{name}_assembly.glb"
    export_step(asm, str(step))
    export_stl(Compound(children=[copy.copy(s) for s in parts.values()]), str(stl), tolerance=STL_TOLERANCE,
               angular_tolerance=STL_ANGULAR)
    preview = _display_split(parts, colours or {}, two_tone or {}, extras or {}) if (two_tone or extras) else asm
    export_gltf(preview, str(glb), binary=True, linear_deflection=STL_TOLERANCE * 2, angular_deflection=STL_ANGULAR)
    return [ExportedFile(None, "step", step), ExportedFile(None, "stl", stl), ExportedFile(None, "glb", glb)]


def part_info(parts: dict[str, Shape]) -> dict[str, Any]:
    """Bounding box size and volume per part (mm, mm³)."""
    info: dict[str, Any] = {}
    for key, solid in parts.items():
        bb = solid.bounding_box()
        info[key] = {
            "size_mm": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
            "z_range_mm": [round(bb.min.Z, 2), round(bb.max.Z, 2)],
            "volume_mm3": round(solid.volume, 1),
            "valid": bool(solid.is_valid),
        }
    return info

