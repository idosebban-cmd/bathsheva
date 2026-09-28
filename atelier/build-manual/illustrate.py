"""
Illustrations for the Atelier prototype build manual, rendered from the CAD
model. Same style as faro/manual/illustrate.py (which this reuses via
manual_common/scene.py): clean studio renders on the manual's warm off-white
paper colour, fine dark outlines, serif labels with thin gold leader lines.
Parts show the stage they're at: matt white resin (inspection, preparation),
grey primer (priming), painted colours (from painting on). In the assembly
steps the parts already in place keep their real colours, a little lighter,
and the new part is drawn in full colour with a deep red outline.

    python atelier/build-manual/illustrate.py            # all images
    python atelier/build-manual/illustrate.py hero step  # only names containing these words

Renders need a GPU or a software GL context (e.g. `xvfb-run python3 ...`;
see manual/README's environment notes for this sandbox).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ATELIER_DIR = HERE.parent
ROOT = ATELIER_DIR.parent
sys.path.insert(0, str(ROOT))
import model  # noqa: E402
import params as p  # noqa: E402
import render as atelier  # noqa: E402  (the shared studio: env map, light rig, _to_mesh)
from manual_common import scene as common_scene  # noqa: E402

OUT = ATELIER_DIR / "build-manual" / "output" / "images"
FONTS = HERE / "fonts"

# ---- the manual's palette (identical to faro/manual/illustrate.py) ---------
PAPER = "#F8F4EC"
INK = (43, 36, 32)
GOLD_RULE = (176, 138, 62)
ACCENT = "#9B1B14"
OUTLINE = "#4A3E34"
RESIN = "#EEEBE3"
PRIMER = "#A6A5A0"
BLACK_PAINT = "#1F1D1C"

S = 2


def hexrgb(h):
    return atelier.hex_rgb(h)


def lin(h):
    return atelier.hex_linear(h)


def font(size, kind="regular"):
    f = {"regular": "EBGaramond-Regular.ttf", "medium": "EBGaramond-Medium.ttf",
         "italic": "EBGaramond-Italic.ttf", "display": "CormorantGaramond-SemiBold.ttf"}[kind]
    return ImageFont.truetype(str(FONTS / f), int(size * S))


# ---- the model --------------------------------------------------------------
M = model.build(p, visual_only=True)
I = M.info

MESH = {}


def mesh(name):
    """Triangulated part (cached). 'grille_paint' is the matt-black recess
    floor behind the grille -- a render envelope on the body, not a printed
    part (see the note on Step 04 in the manual)."""
    if name not in MESH:
        shape = M.envelopes[name] if name == "grille_paint" else M.parts[name]
        MESH[name] = atelier._to_mesh(shape, 0.03)
    return MESH[name].copy()


PART_NAMES = ["body", "grille_paint", "grille", "bezel", "knob", "fin_1", "fin_2", "fin_3", "collar", "foot",
              "nose_cone"]
GOLD_PARTS = {"nose_cone", "fin_1", "fin_2", "fin_3", "grille", "bezel", "knob", "collar", "foot"}


# ---- plotter ------------------------------------------------------------------
# The plotter mechanics (add/part/shadow/camera/fit/project/image) live in
# manual_common/scene.py, shared with faro/manual/illustrate.py. Only
# Atelier's own part staging (style, below) is here.
class Scene(common_scene.Scene):
    def __init__(self, size=(1400, 1000), lights=1.0):
        super().__init__(atelier, mesh, p, size=size, lights=lights, scale=S,
                          paper=PAPER, outline=OUTLINE, accent=ACCENT)

    # materials by stage ------------------------------------------------------
    def style(self, name, stage, lit=False, soft=False):
        if stage == "resin":
            st, coat = dict(color=lin(RESIN), pbr=True, metallic=0.0, roughness=0.55), False
        elif stage == "primer":
            st, coat = dict(color=lin(PRIMER), pbr=True, metallic=0.0, roughness=0.8), False
        else:                                                            # painted
            if name == "grille_paint":                    # matt black recess floor, masked and sprayed
                st, coat = dict(color=lin(BLACK_PAINT), pbr=True, metallic=0.0, roughness=0.85), False
            elif name.startswith("body"):
                st = dict(color=lin(p.RED_HEX), pbr=True, metallic=0.0, roughness=p.BODY_ROUGHNESS)
                coat = True
            else:                                          # gold trim: nose cone, fins, bezel, knob,
                st = dict(color=lin(p.GOLD_HEX), pbr=True, metallic=p.GOLD_METALLIC,  # collar, foot, grille
                          roughness=max(p.GOLD_ROUGHNESS, 0.45))          # satin in the studio, not mirror
                coat = False                                              # clear coat dulls metallic paint
        st = dict(st)
        if soft:                                          # parts already in place: real colour, a little lighter
            if "color" in st and st.get("lighting", True) is not False:
                c = np.array(st["color"]) ** (1 / 2.2)
                paper = np.array(lin(PAPER)) ** (1 / 2.2)
                st["color"] = tuple((c * 0.85 + paper * 0.15) ** 2.2)
            coat = False
        return st, coat


def finish(img, name):
    """Downsample from the S x working size and save."""
    OUT.mkdir(parents=True, exist_ok=True)
    w, h = img.size
    img = img.resize((w // S, h // S), Image.LANCZOS)
    path = OUT / f"{name}.png"
    img.save(path)
    print("  ", path.name, img.size)
    return path


ORDER = ["body", "grille_paint", "grille", "bezel", "knob", "fin_1", "fin_2", "fin_3", "collar", "foot", "nose_cone"]


def add_painted(sc, name, **kw):
    sc.part(name, "paint", **kw)


def img_hero():
    """Cover: the finished, painted, assembled prototype."""
    sc = Scene((900, 1300))
    for n in ORDER:
        add_painted(sc, n, lit=True)
    sc.shadow(0, 0, I["fin_tip_reach"], 0.45)
    sc.camera((0, 0, I["H"] * 0.42), (0, -1, 0.12), dist=3000, view_angle=7.2)
    return finish(sc.image(), "00_hero")


def img_step(name, done, new, view=(0.62, -1.0, 0.35), size=(1000, 800), fit_to=None, margin=1.08):
    """done: parts already in place (real colours, a little lighter); new: the
    part(s) added in this step (full colour, red outline)."""
    sc = Scene(size)
    for n in done:
        st, coat = sc.style(n, "paint", soft=True)
        sc.add(mesh(n), st, coat)
    for n in new:
        sc.part(n, "paint", highlight=True)
    lo_all = np.min([[b[0], b[2], b[4]] for b in sc.bounds], axis=0)
    hi_all = np.max([[b[1], b[3], b[5]] for b in sc.bounds], axis=0)
    sc.shadow((lo_all[0] + hi_all[0]) / 2, (lo_all[1] + hi_all[1]) / 2,
              min(max(hi_all[0] - lo_all[0], hi_all[1] - lo_all[1]) / 2, I["fin_tip_reach"] / 2), 0.3)
    sc.fit(view, margin=margin, bounds=fit_to)
    return finish(sc.image(), name)


def assembly_step_1_of_3():
    """Step 06, assembly, page 1: grille, bezel, knob."""
    img_step("06_01_grille", done=["body", "grille_paint"], new=["grille"])
    img_step("06_02_bezel", done=["body", "grille_paint", "grille"], new=["bezel"])
    img_step("06_03_knob", done=["body", "grille_paint", "grille", "bezel"], new=["knob"],
              view=(0.5, -1.0, 0.0))


REGISTRY = {
    "hero": img_hero,
    "step": assembly_step_1_of_3,
}


def contact_sheet(path=None):
    files = sorted(OUT.glob("*.png"))
    if not files:
        return
    thumbs = [Image.open(f) for f in files]
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    tw, th = 260, 200
    sheet = Image.new("RGB", (cols * tw, rows * th), (255, 255, 255))
    for i, im in enumerate(thumbs):
        im2 = im.copy()
        im2.thumbnail((tw - 10, th - 24))
        x, y = (i % cols) * tw + 5, (i // cols) * th + 5
        sheet.paste(im2, (x, y))
        d = ImageDraw.Draw(sheet)
        d.text((x, y + th - 20), files[i].stem, fill=(40, 40, 40))
    out = path or (ATELIER_DIR / "build-manual" / "output" / "contact_sheet.png")
    sheet.save(out)
    return out


def main():
    names = sys.argv[1:]
    todo = {k: v for k, v in REGISTRY.items() if not names or any(n in k for n in names)}
    if not todo:
        print("no matching images:", names)
        return
    for k, fn in todo.items():
        print(k)
        fn()
    contact_sheet()


if __name__ == "__main__":
    main()
