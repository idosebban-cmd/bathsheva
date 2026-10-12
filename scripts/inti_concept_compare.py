"""Compare the INTI CAD model with its concept render: the render's front, side and rear views above, the model
seen from the same directions below, at the render's scale (overall height 250 mm = the render's 250 px).

Writes docs/inti/concept_compare.png. The proportions in app/cad/inti.py (SECTIONS, FEATURES) were measured on
docs/inti/concept.png; rerun this after changing them. It takes about a minute (the model build plus a small
z-buffer rasteriser; no extra packages).

Usage (from the repo root): backend/.venv/bin/python scripts/inti_concept_compare.py
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.cad import inti  # noqa: E402

RENDER = ROOT / inti.RENDER["file"]
OUT = ROOT / "docs" / "inti" / "concept_compare.png"
W, H_IMG = 340, 290  # each panel, in render pixels
# Each view's centre on the render (x of the base ring's centre) and its camera: (right, towards the viewer).
VIEWS = {"front": (188.5, (1, 0, 0), (0, -1, 0)), "side": (478.0, (0, 1, 0), (1, 0, 0)),
         "rear": (766.0, (-1, 0, 0), (0, 1, 0))}
HIDDEN = {"driver", "battery", "main_board"}


def triangles(params):
    m = inti.model(params)
    out = []
    for key, shape in {**m.parts, **inti._instance_copies(m.parts)}.items():
        if key in HIDDEN:
            continue
        colour = np.array(inti.PART_COLOURS[key.removesuffix("_2")][:3])
        verts, tris = shape.tessellate(0.1, 0.2)
        v = np.array([[p.X, p.Y, p.Z] for p in verts])
        out += [(v[[a, b, c]], colour) for a, b, c in tris]
    return out


def rasterise(tris, right, toward):
    right, toward, up = np.array(right, float), np.array(toward, float), np.array((0, 0, 1.0))
    zbuf = np.full((H_IMG, W), -1e9)
    rgb = np.empty((H_IMG, W, 3))
    rgb[:] = (245, 242, 236)
    light = 0.5 * toward + 0.6 * up + 0.3 * right
    light /= np.linalg.norm(light)
    for t, colour in tris:
        n = np.cross(t[1] - t[0], t[2] - t[0])
        if np.linalg.norm(n) == 0 or n @ toward <= 0:
            continue
        shade = 0.35 + 0.65 * max(0.0, n @ light / np.linalg.norm(n))
        p2 = np.array([[W / 2 + p @ right, H_IMG - 20 - p @ up] for p in t])  # ground 20 px above the bottom
        depth = t @ toward
        x0, y0 = np.maximum(np.floor(p2.min(0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(p2.max(0)).astype(int), (W - 1, H_IMG - 1))
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = p2
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
        l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
        l3 = 1 - l1 - l2
        z = l1 * depth[0] + l2 * depth[1] + l3 * depth[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        hit = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6) & (z > sub)
        sub[hit] = z[hit]
        rgb[y0:y1 + 1, x0:x1 + 1][hit] = np.minimum(255, colour * shade * 255)
    return Image.fromarray(rgb.astype(np.uint8))


def main() -> None:
    params = {"overall_height": inti.RENDER["height_px"], "wall_thickness": 5.0, "trim_thickness": 2.0,
              "driver_diameter": 76.0}
    ground = inti.RENDER["ground_y_px"]
    render = Image.open(RENDER).convert("RGB")
    tris = triangles(params)
    sheet = Image.new("RGB", (W * len(VIEWS), H_IMG * 2), "white")
    for i, (cx, right, toward) in enumerate(VIEWS.values()):
        box = (int(cx - W / 2), ground - (H_IMG - 20), int(cx + W / 2), ground + 20)
        sheet.paste(render.crop(box), (W * i, 0))
        sheet.paste(rasterise(tris, right, toward), (W * i, H_IMG))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.resize((sheet.width * 2, sheet.height * 2)).save(OUT)
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
