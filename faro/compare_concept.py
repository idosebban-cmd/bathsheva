"""
Faro next to the concept's straight front view, at the same scale.

    python faro/compare_concept.py

Renders the model from the front with an orthographic camera, scaled so the
concept's ground-to-finial height is OVERALL_HEIGHT and aligned on its centre
line (as Atelier's compare_concept.py does), then writes
faro/output/concept_compare/side_by_side.png with shared reference lines.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE / "reference"))
import fit_concept as fc  # noqa: E402
import lamp  # noqa: E402
import params as p  # noqa: E402
import studio  # noqa: E402

OUT = HERE / "output" / "concept_compare"
ZOOM = 3                                   # the concept crop is small; show both at 3x


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = fc.CROP
    concept = Image.open(fc.IMG).convert("RGB").crop(fc.CROP)
    W, H = concept.width * ZOOM, concept.height * ZOOM
    concept = concept.resize((W, H), Image.LANCZOS)
    s = p.OVERALL_HEIGHT / (fc.Y_GROUND - fc.Y_TOP)                  # mm per concept pixel
    xc = ((x0 + x1) / 2 - fc.X_AXIS) * s
    zc = (fc.Y_GROUND - (y0 + y1) / 2) * s

    m = lamp.build(p)
    pl = studio.plotter(m, p, (W, H))
    pl.enable_parallel_projection()
    pl.camera.position = (xc, -3000, zc)
    pl.camera.focal_point = (xc, 0, zc)
    pl.camera.up = (0, 0, 1)
    pl.camera.parallel_scale = (y1 - y0) / 2 * s
    pl.reset_camera_clipping_range()
    model_img = Image.fromarray(pl.screenshot(return_img=True))
    pl.close()

    sbs = Image.new("RGB", (W * 2 + 20, H), (255, 255, 255))
    sbs.paste(concept, (0, 0))
    sbs.paste(model_img.resize((W, H)), (W + 20, 0))
    d = ImageDraw.Draw(sbs)
    L = fc.LANDMARKS
    for y in (fc.Y_TOP, L["cap_rim"][1], L["gallery_platform"][0], L["tower_top"][0],
              L["red_band"][0], L["cream_band"][0], fc.Y_GROUND):
        Y = (y - y0) * ZOOM
        d.line([(0, Y), (sbs.width, Y)], fill=(0, 170, 255), width=1)
    d.text((10, H - 20), "concept (front view)", fill=(60, 60, 60))
    d.text((W + 30, H - 20), "model", fill=(60, 60, 60))
    sbs.save(OUT / "side_by_side.png")
    print(OUT / "side_by_side.png")


if __name__ == "__main__":
    main()
