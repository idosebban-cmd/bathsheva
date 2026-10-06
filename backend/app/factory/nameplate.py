"""FARO nameplate lettering as 1:1 vector artwork (SVG and DXF) for the etcher.

The lettering is the prototype's (faro/lamp.py and faro/params.py on the prototype
branch): build123d `Text("FARO", 6.5, font_style=BOLD)` with the default font (Arial
Bold; Liberation Sans Bold, which has Arial's metrics, where Arial isn't installed),
centred on the plate. The plate outline is the production nameplate (37 × 11.5 mm, R1.2).

The exported files are stored in seed/artwork/ (scripts/export_nameplate_artwork.py)
so the pack ships the same artwork on every machine, whatever fonts it has.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.cad import faro
from app.config import SEED_DIR

TEXT = "FARO"  # prototype NAMEPLATE_TEXT
TEXT_SIZE = 6.5  # prototype NAMEPLATE_TEXT_H (font size, mm)
CORNER_R = 1.2
ARTWORK_DIR = SEED_DIR / "artwork"
STEM = "F-05_nameplate_lettering"


def shapes():
    from build123d import FontStyle, RectangleRounded, Text

    letters = Text(TEXT, TEXT_SIZE, font_style=FontStyle.BOLD)
    plate = RectangleRounded(faro.NAMEPLATE_W, faro.NAMEPLATE_H, CORNER_R)
    return plate, letters


def export(out_dir: Path) -> dict[str, Path]:
    """Write <STEM>.svg and <STEM>.dxf (millimetres, 1:1) into out_dir."""
    from build123d import ExportDXF, ExportSVG, Unit

    plate, letters = shapes()
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path, dxf_path = out_dir / f"{STEM}.svg", out_dir / f"{STEM}.dxf"
    svg = ExportSVG(unit=Unit.MM, line_weight=0.05)
    svg.add_layer("plate_outline_reference", line_color="gray", line_weight=0.05)
    svg.add_layer("lettering_etch", fill_color="black", line_color=None, line_weight=0.0)
    svg.add_shape(plate.edges(), layer="plate_outline_reference")
    svg.add_shape(letters.faces(), layer="lettering_etch")
    svg.write(str(svg_path))
    dxf = ExportDXF(unit=Unit.MM)
    dxf.add_layer("PLATE_OUTLINE_REFERENCE")
    dxf.add_layer("LETTERING_ETCH")
    dxf.add_shape(plate.edges(), layer="PLATE_OUTLINE_REFERENCE")
    dxf.add_shape(letters.faces(), layer="LETTERING_ETCH")
    dxf.write(str(dxf_path))
    return {"svg": svg_path, "dxf": dxf_path}


def artwork_files() -> dict[str, bytes]:
    """The stored artwork (seed/artwork); exported on the fly if it is missing."""
    files = {ext: ARTWORK_DIR / f"{STEM}.{ext}" for ext in ("svg", "dxf")}
    if not all(p.is_file() for p in files.values()):
        files = export(Path(tempfile.mkdtemp(prefix="nameplate-")))
    return {f"{STEM}.{ext}": p.read_bytes() for ext, p in files.items()}
