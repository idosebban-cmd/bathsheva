"""
Compare the model's front view with the concept image.

    python compare_concept.py

Renders the model from the front with an orthographic (no perspective) camera,
scaled so 280 mm = the concept's tip-to-ground height and aligned on its centre
line, then writes to output/concept_compare/:

* side_by_side.png - concept | model at the same scale
* overlay.png      - the concept with the model's outline drawn over it
                     (cyan = model silhouette, magenta = model grille/knob/collar edges)
* deviation.md     - body width compared row by row, and where they still differ

The concept is a perspective photo, so small differences near the top and
bottom are expected even for a perfect match.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import model as geometry
import params as p
import render

sys.path.insert(0, str(Path(__file__).parent / "reference"))
import fit_concept as fc  # noqa: E402  (landmarks and the red mask)

OUT = Path(__file__).parent / "output" / "concept_compare"
SCALE = 2                                  # render at 2x the concept's resolution


def render_front_ortho(m, flat_bg=True):
    """Model front view, orthographic, pixel-aligned with the concept (at SCALE)."""
    concept = Image.open(fc.IMG)
    W, H = concept.width * SCALE, concept.height * SCALE
    mm_px = p.OVERALL_HEIGHT / (fc.Y_GROUND - fc.Y_TIP)          # mm per concept pixel
    xc = (concept.width / 2 - fc.X_AXIS) * mm_px                   # world X at image centre
    zc = (fc.Y_GROUND - concept.height / 2) * mm_px                # world Z at image centre
    pl = render._plotter(m, p, (W, H), shadow=not flat_bg)
    if flat_bg:
        pl.set_background("white")
    pl.enable_parallel_projection()
    pl.camera.position = (xc, -3000, zc)
    pl.camera.focal_point = (xc, 0, zc)
    pl.camera.up = (0, 0, 1)
    pl.camera.parallel_scale = concept.height / 2 * mm_px
    pl.reset_camera_clipping_range()
    img = Image.fromarray(pl.screenshot(return_img=True))
    pl.close()
    return img.resize(concept.size, Image.LANCZOS)


def silhouette(img):
    a = np.asarray(img.convert("RGB")).astype(int)
    mask = np.abs(a - 255).sum(-1) > 25
    return ndimage.binary_fill_holes(ndimage.binary_closing(mask, iterations=2))


def outline(mask):
    return mask & ~ndimage.binary_erosion(mask, iterations=1)


def body_widths(mask_red, rows):
    out = {}
    for y in rows:
        xs = np.where(mask_red[y])[0]
        if len(xs) > 20:
            out[y] = (xs.max() - xs.min()) / 2
    return out


def main():
    draft = "--draft" in sys.argv          # visible parts only, honeycomb off, side-by-side only
    if draft:
        p.HEX_PATTERN_ENABLED = False
    OUT.mkdir(parents=True, exist_ok=True)
    print("Building model...")
    m = geometry.build(p, visual_only=draft)
    print("Rendering orthographic front views...")
    flat = render_front_ortho(m, flat_bg=True)
    pretty = render_front_ortho(m, flat_bg=False)
    concept = Image.open(fc.IMG).convert("RGB")

    # side by side
    sbs = Image.new("RGB", (concept.width * 2 + 20, concept.height), (255, 255, 255))
    sbs.paste(concept, (0, 0))
    sbs.paste(pretty, (concept.width + 20, 0))
    d = ImageDraw.Draw(sbs)
    d.text((10, concept.height - 20), "concept", fill=(255, 255, 255))
    d.text((concept.width + 30, concept.height - 20), "model", fill=(60, 60, 60))
    for y in (fc.Y_TIP, fc.Y_JOINT, fc.Y_BODY_BOTTOM, fc.Y_GROUND):   # shared reference lines
        d.line([(0, y), (sbs.width, y)], fill=(0, 170, 255), width=1)
    sbs.save(OUT / "side_by_side.png")
    if draft:
        print(OUT / "side_by_side.png")
        return

    # overlay: model silhouette (cyan) + model's gold feature edges (magenta)
    sil = silhouette(flat)
    a = np.asarray(flat.convert("RGB")).astype(float) / 255
    red_model = fc.red_mask(a)
    gold_edges = outline(sil & ~ndimage.binary_dilation(red_model, iterations=1)) & ~outline(sil)
    ov = np.asarray(concept).copy()
    ov = (ov * 0.85).astype(np.uint8)
    ov[outline(ndimage.binary_dilation(sil, iterations=1))] = (0, 255, 255)
    ov[gold_edges] = (255, 0, 255)
    Image.fromarray(ov).resize((concept.width * 2, concept.height * 2), Image.NEAREST).save(OUT / "overlay.png")

    # body width compared row by row (above the fins, where the concept's edge is visible)
    mm_px = p.OVERALL_HEIGHT / (fc.Y_GROUND - fc.Y_TIP)
    red_concept = fc.red_mask(np.asarray(concept).astype(float) / 255)
    rows = range(int(fc.Y_JOINT) + 6, int(fc.FIN_TOP[0]) - 6, 2)
    wc, wm = body_widths(red_concept, rows), body_widths(sil, rows)
    diffs = [(y, (wm[y] - wc[y]) * mm_px) for y in rows if y in wc and y in wm]
    dd = np.array([v for _, v in diffs])
    worst = max(diffs, key=lambda t: abs(t[1]))

    # silhouette extents of the other features
    def extent(mask, y0, y1):
        ys, xs = np.where(mask[int(y0):int(y1)])
        return (xs.min(), xs.max()) if len(xs) else (0, 0)
    fin_c = (fc.FIN_OUTER[-1][1] + fc.FIN_OUTER[-2][1]) / 2
    fx0, fx1 = extent(sil, 760, 805)
    fin_m = (fx1 - fx0) / 2
    tip_rows = np.where(sil.any(1))[0]

    # fin edges against the concept landmarks (left and right fin averaged)
    def fin_outer_err():
        errs = []
        for y, d in fc.FIN_OUTER:
            xs = np.where(sil[int(y)])[0]
            if len(xs):
                errs.append(((fc.X_AXIS - xs.min()) + (xs.max() - fc.X_AXIS)) / 2 - d)
        return np.array(errs) * mm_px

    def fin_lower_err():
        errs = []
        for y, d in fc.FIN_LOWER[:-1]:
            for x in (int(fc.X_AXIS - d), int(fc.X_AXIS + d)):
                col = np.where(sil[:int(fc.Y_GROUND) - 3, x])[0]
                if len(col):
                    errs.append(col.max() - y)
        return np.array(errs) * mm_px
    fo, fl = fin_outer_err(), fin_lower_err()

    L = ["# Model vs concept (front view)", "",
         "Orthographic model render aligned to the concept at 280 mm tip-to-ground. "
         "The concept is a perspective photo, so a few mm near the top and bottom is expected.", "",
         "| Check | Difference |", "|---|---|",
         f"| Body half-width, above the fins (mean / worst) | {dd.mean():+.1f} / {worst[1]:+.1f} mm "
         f"(worst at {(fc.Y_GROUND - worst[0]) * mm_px:.0f} mm up) |",
         f"| Fin spread near the ground (half-width) | {(fin_m - fin_c) * mm_px:+.1f} mm |",
         f"| Fin outer edge, 5 heights (mean / worst) | {fo.mean():+.1f} / {fo[np.argmax(abs(fo))]:+.1f} mm |",
         f"| Fin lower edge, 3 points (mean / worst; + = model lower) | {fl.mean():+.1f} / "
         f"{fl[np.argmax(abs(fl))]:+.1f} mm |",
         f"| Nose tip height | {(fc.Y_TIP - tip_rows.min()) * mm_px:+.1f} mm |",
         "", "Positive = the model is wider/taller than the concept.", "",
         "## Known differences (by design or unmeasurable)", "",
         "* **Cone joint:** the concept's cone base is about 2 mm narrower than the body top (a small "
         "step). The model keeps the flush joint you asked for, blending to the concept's shape towards the tip.",
         "* **Lower body:** hidden behind the fins in the photo. It's fitted from the fin/body joint lines, "
         "plus an assumed rounded belly under the fins.",
         "* **Grille:** the concept's honeycomb is finer and irregular (a render artefact); the model uses the "
         "2.2 mm hexagon pattern.",
         "* **Base:** the concept's collar is taller (~10.6 mm) with the foot about 5 mm off the ground. The model "
         "keeps the 2 mm ground gap and fits the 5.5 mm vent gap, so the collar is slimmer "
         f"({m.info['z0'] - m.info['collar_bottom']:.1f} mm).",
         "* **Perspective:** the photo is taken from slightly above, so the collar and foot look lower "
         "and the top of the cone slightly smaller than in an orthographic view.",
         ""]
    (OUT / "deviation.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
