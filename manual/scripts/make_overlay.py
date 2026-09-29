"""
Overlays a rendered line-art drawing on the reference photo, and builds a
side-by-side comparison, so the drawings can be checked against the photo
by eye every time the assembly changes -- not just trusted on the numbers.

Calibration: the reference photo's own pixel<->world_z mapping was derived
in manual/scripts/photo_fit.py (nose/body seam and body-equator landmarks,
cross-checked against the verified body CAD). The drawing is rendered at
page_scale=1.0 (1 SVG unit = 1mm exactly), so its own pixel<->world mapping
is exact, not measured. Combining the two gives the placement below.

Run: python3 scripts/make_overlay.py
Output: figures/check/overlay_front.png, figures/check/side_by_side.png
"""

import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FIGURES_FINAL = ROOT / "figures" / "final"
CHECK_DIR = ROOT / "figures" / "check"
PHOTO = ROOT / "reference" / "atelier_reference_photo.png"

# photo calibration (see scripts/photo_fit.py)
SEAM_PX_Y, SEAM_WORLD_Z = 288, 209.1
EQUATOR_PX_Y, EQUATOR_WORLD_Z = 972, 91.6
SCALE_MM_PER_PX = (EQUATOR_WORLD_Z - SEAM_WORLD_Z) / (EQUATOR_PX_Y - SEAM_PX_Y)
PHOTO_PX_PER_MM = abs(1 / SCALE_MM_PER_PX)
PHOTO_CENTERLINE_X = 424.5


def world_to_photo_px(x, z):
    px = PHOTO_CENTERLINE_X + x * PHOTO_PX_PER_MM
    py = SEAM_PX_Y + (z - SEAM_WORLD_Z) / SCALE_MM_PER_PX
    return px, py


def drawing_svg_bounds(svg_path):
    """(width_mm, height_mm) from the SVG's own header -- page_scale=1.0 so
    these are also the content's real-world mm span (plus the fixed 10mm
    margin write_svg() always adds around the content)."""
    header = svg_path.read_text().splitlines()[0]
    import re
    m = re.search(r'width="([\d.]+)mm" height="([\d.]+)mm"', header)
    return float(m.group(1)), float(m.group(2))


def main():
    CHECK_DIR.mkdir(parents=True, exist_ok=True)
    svg_path = FIGURES_FINAL / "hero_front.svg"
    w_mm, h_mm = drawing_svg_bounds(svg_path)

    # write_svg's content bounds: nose tip (topmost, world_z=258.3) sits at
    # the top margin (svg_y=10), foot tip (bottommost, world_z=-29.8) at the
    # bottom margin (svg_y=h_mm-10) -- see the module docstring. Centreline
    # (world_x=0) sits at svg_x=w_mm/2 by left-right symmetry.
    margin = 10.0
    svg_x0 = w_mm / 2  # world_x=0
    svg_y_nose = margin  # world_z=258.3
    # svg_y = Y_OFFSET - world_z  =>  Y_OFFSET = svg_y_nose + 258.3
    y_offset = svg_y_nose + 258.3

    def world_to_svg_mm(x, z):
        return x + svg_x0, y_offset - z

    # render the drawing at the photo's own px/mm scale, background stripped
    px_per_mm = PHOTO_PX_PER_MM
    drawing_png = CHECK_DIR / "hero_front_transparent.png"
    subprocess.run(
        ["node", str(ROOT / "scripts" / "render_transparent.js"), str(svg_path), str(drawing_png), str(px_per_mm)],
        check=True,
    )

    photo = Image.open(PHOTO).convert("RGBA")
    drawing = Image.open(drawing_png).convert("RGBA")

    # where does the drawing's own (0,0) SVG-mm point land in photo pixels?
    world_x0, world_z0 = -svg_x0, y_offset  # inverse of world_to_svg_mm at svg (0,0)
    paste_x, paste_y = world_to_photo_px(world_x0, world_z0)

    # 50% opacity on the drawing layer
    r, g, b, a = drawing.split()
    a = a.point(lambda v: int(v * 0.5))
    drawing_half = Image.merge("RGBA", (r, g, b, a))

    overlay = photo.copy()
    overlay.alpha_composite(drawing_half, dest=(round(paste_x), round(paste_y)))
    overlay_path = CHECK_DIR / "overlay_front.png"
    overlay.convert("RGB").save(overlay_path)
    print("wrote", overlay_path)

    # side-by-side: photo | drawing on white, same height
    target_h = photo.height
    dscale = target_h / drawing.height
    drawing_resized = drawing.resize((round(drawing.width * dscale), target_h))
    drawing_on_white = Image.new("RGBA", drawing_resized.size, (247, 243, 236, 255))
    drawing_on_white.alpha_composite(drawing_resized)
    side_by_side = Image.new("RGB", (photo.width + drawing_on_white.width + 20, target_h), (255, 255, 255))
    side_by_side.paste(photo.convert("RGB"), (0, 0))
    side_by_side.paste(drawing_on_white.convert("RGB"), (photo.width + 20, 0))
    side_by_side_path = CHECK_DIR / "side_by_side.png"
    side_by_side.save(side_by_side_path)
    print("wrote", side_by_side_path)


if __name__ == "__main__":
    main()
