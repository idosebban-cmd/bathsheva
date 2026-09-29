"""
Illustrations for the Atelier prototype build manual, rendered from the CAD
model. Same style as faro/manual/illustrate.py (which this reuses via
manual_common/scene.py): clean studio renders on the manual's warm off-white
paper colour, fine dark outlines, serif labels with thin gold leader lines.
Parts show the stage they're at: matt white resin (inspection, preparation),
grey primer (priming), painted colours (from painting on). In the assembly
steps the parts already in place fade well back towards the paper colour,
and the new part is drawn at full strength with a thin dark outline (a red
one, as Faro uses, doesn't read against Atelier's own oxblood body).

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


def bbox(m):
    b = m.bounds
    return np.array([b[0], b[2], b[4]]), np.array([b[1], b[3], b[5]])


def draw_label(d, text, at, anchor, align="left", size=17, sub=None):
    """Label at `at` (image px) with a thin gold leader to `anchor`, ending in a dot.
    Identical to faro/manual/illustrate.py's helper of the same name."""
    f = font(size)
    x, y = at
    tw = d.textlength(text, font=f)
    tx = x - tw if align == "right" else (x - tw / 2 if align == "center" else x)
    halo = tuple(int(c * 255) for c in hexrgb(PAPER))
    d.text((tx, y - f.size * 0.62), text, font=f, fill=INK, stroke_width=int(2.5 * S), stroke_fill=halo)
    if sub:
        fs = font(size * 0.78, "italic")
        sw = d.textlength(sub, font=fs)
        sx = x - sw if align == "right" else (x - sw / 2 if align == "center" else x)
        d.text((sx, y + f.size * 0.45), sub, font=fs, fill=(110, 95, 82), stroke_width=int(2 * S),
               stroke_fill=tuple(int(c * 255) for c in hexrgb(PAPER)))
    if anchor is not None:
        lx = x + 10 * S if align == "right" else x - 10 * S
        if align == "center":
            lx, ly = x, y - f.size * 0.75
        else:
            ly = y
        d.line([(lx, ly), anchor], fill=GOLD_RULE, width=int(1.2 * S))
        r = 2.6 * S
        d.ellipse([anchor[0] - r, anchor[1] - r, anchor[0] + r, anchor[1] + r], fill=GOLD_RULE)


def badge(d, center, n, size=15, fill=(248, 244, 236), ring=GOLD_RULE, ink=INK):
    r = size * S
    x, y = center
    d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=ring, width=int(1.6 * S))
    f = font(size * 1.15, "medium")
    t = str(n)
    tw = d.textlength(t, font=f)
    d.text((x - tw / 2, y - f.size * 0.62), t, font=f, fill=ink)


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



# ---- plotter ------------------------------------------------------------------
# The plotter mechanics (add/part/shadow/camera/fit/project/image) live in
# manual_common/scene.py, shared with faro/manual/illustrate.py. Only
# Atelier's own part staging (style, below) is here.
class Scene(common_scene.Scene):
    def __init__(self, size=(1400, 1000), lights=1.0):
        # A red highlight outline doesn't read against the oxblood body, so
        # Atelier's "new part" outline uses the same dark outline colour as
        # every other edge, just thicker -- and the "done" parts fade back
        # much further than Faro's, so the new part still stands out at a
        # glance without relying on the outline colour to do it.
        super().__init__(atelier, mesh, p, size=size, lights=lights, scale=S,
                          paper=PAPER, outline=OUTLINE, accent=OUTLINE)

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
                          roughness=max(p.GOLD_ROUGHNESS, 0.65))          # matte enough that the grille's
                coat = False                              # clear coat dulls metallic paint    # deep honeycomb
                                                            # pockets don't self-shadow into reading as copper
        st = dict(st)
        if soft:                                          # parts already fitted: faded well back, so the new
            if "color" in st and st.get("lighting", True) is not False:  # part (full strength, dark outline)
                c = np.array(st["color"]) ** (1 / 2.2)                    # reads at a glance
                paper = np.array(lin(PAPER)) ** (1 / 2.2)
                st["color"] = tuple((c * 0.45 + paper * 0.55) ** 2.2)
            coat = False
        return st, coat


def trim_to_content(img, pad=30):
    """Crop away blank paper-colour margin around the real content (a render
    letterboxed by an odd content aspect, e.g. a tall stack beside a synthetic
    label-margin box, otherwise leaves a lot of dead space top and bottom when
    placed in a page column at a fixed width). `pad` is in the image's own
    (working-scale) pixels."""
    arr = np.asarray(img.convert("RGB")).astype(np.int16)
    paper = np.array([int(c * 255) for c in hexrgb(PAPER)])
    diff = np.abs(arr - paper).sum(axis=2)
    mask = diff > 12
    if not mask.any():
        return img
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    top, bottom = max(rows[0] - pad, 0), min(rows[-1] + pad, img.size[1])
    left, right = max(cols[0] - pad, 0), min(cols[-1] + pad, img.size[0])
    return img.crop((left, top, right, bottom))


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


def zoom_bounds(z_lo, z_hi, r=60, x=0.0, y=0.0):
    """A synthetic single-box bounds list to pass as `fit_to` (Scene.fit
    expects a list of [xmin,xmax,ymin,ymax,zmin,zmax] boxes), so a step's
    render frames just the relevant band of the body (e.g. the front face,
    or the base) instead of the whole 280 mm rocket with empty space above
    and below it."""
    return [(x - r, x + r, y - r, y + r, z_lo, z_hi)]


def img_step(name, done, new, view=(0.62, -1.0, 0.35), size=(1000, 800), fit_to=None, margin=1.1, extra=None):
    """done: parts already in place (real colours, a little lighter); new: the
    part(s) added in this step (full colour, red outline). extra: optional
    list of (mesh, style_dict) pairs added without silhouette outline (e.g.
    steel shot)."""
    sc = Scene(size)
    for n in done:
        st, coat = sc.style(n, "paint", soft=True)
        sc.add(mesh(n), st, coat)
    for n in new:
        sc.part(n, "paint", highlight=True)
    for m, st in (extra or []):
        sc.add(m, st, outline=False)
    lo_all = np.min([[b[0], b[2], b[4]] for b in sc.bounds], axis=0)
    hi_all = np.max([[b[1], b[3], b[5]] for b in sc.bounds], axis=0)
    sc.shadow((lo_all[0] + hi_all[0]) / 2, (lo_all[1] + hi_all[1]) / 2,
              min(max(hi_all[0] - lo_all[0], hi_all[1] - lo_all[1]) / 2, I["fin_tip_reach"] / 2), 0.3)
    sc.fit(view, margin=margin, bounds=fit_to)
    return finish(sc.image(), name)


def steel_shot(n=22, seed=3):
    """A loose cluster of ~6 mm steel shot resting low in the body, glued
    through the open bottom before the collar goes on."""
    rng = np.random.default_rng(seed)
    out = None
    for _ in range(n):
        a = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(0, 15)
        x, y = r * np.cos(a), r * np.sin(a)
        z = I["z0"] + 4 + rng.uniform(0, 5)
        s = pv.Sphere(radius=3.1, center=(x, y, z), theta_resolution=16, phi_resolution=16)
        out = s if out is None else out.merge(s)
    return out


def assembly_step_1_of_2():
    """Step 06, assembly, page 1 of 2: grille, bezel, knob, fins."""
    front = zoom_bounds(I["z0"] + 60, I["z_tip"] * 0.78, r=55, y=0)
    img_step("06_01_grille", done=["body", "grille_paint"], new=["grille"], fit_to=front)
    img_step("06_02_bezel", done=["body", "grille_paint", "grille"], new=["bezel"], fit_to=front)
    img_step("06_03_knob", done=["body", "grille_paint", "grille", "bezel"], new=["knob"],
              view=(0.5, -1.0, 0.0), fit_to=front)
    base = zoom_bounds(I["z0"] - 5, I["z0"] + 110, r=95)
    img_step("06_04_fins", done=["body", "grille_paint", "grille", "bezel", "knob"],
              new=["fin_1", "fin_2", "fin_3"], view=(0.55, -0.95, 0.15), fit_to=base, margin=1.15)


def assembly_step_2_of_2():
    """Step 06, assembly, page 2 of 2: dry-fit tip test, weight, collar, foot,
    nose cone. The collar and foot are test-fitted here (highlighted, as with
    any newly-placed part) for the unweighted tip test, then come off again
    before the steel shot goes in and they're glued on for good below."""
    done4 = ["body", "grille_paint", "grille", "bezel", "knob", "fin_1", "fin_2", "fin_3"]
    base = zoom_bounds(I["z0"] - 5, I["z0"] + 60, r=70)
    img_step("06_04b_dryfit_tip", done=done4, new=["collar", "foot"], view=(0.5, -0.9, 0.1), fit_to=base,
              margin=1.2)
    shot_style = dict(color=lin("#8C8F94"), pbr=True, metallic=0.9, roughness=0.4)
    img_step("06_05_weight", done=done4, new=[], view=(0.4, -0.7, -0.5), fit_to=base, margin=1.3,
              extra=[(steel_shot(), shot_style)])
    img_step("06_06_collar", done=done4, new=["collar"], view=(0.5, -0.95, 0.05), fit_to=base)
    foot_base = zoom_bounds(0, I["z0"] + 30, r=40)
    img_step("06_07_foot", done=done4 + ["collar"], new=["foot"], view=(0.5, -0.9, 0.1), fit_to=foot_base,
              margin=1.5)
    top = zoom_bounds(I["z_joint"] - 40, I["z_tip"], r=60)
    img_step("06_08_nose_cone", done=done4 + ["collar", "foot"], new=["nose_cone"], fit_to=top, margin=1.15)


# ---- Step 01: exploded, labelled, white resin --------------------------------
def img_exploded():
    """foot/collar/body/nose_cone are already modelled nested in their real
    assembled positions (the spigots interlock), so 'exploding' them means
    pulling each one further up than it naturally sits, by a fixed gap above
    wherever the part below it now ends -- not a guessed absolute height.
    grille/bezel/knob are pulled out along -Y (the model's front direction,
    see model.py's own note: "front (grille) faces -Y") off the body face."""
    sc = Scene((950, 1650))
    anchors = {}
    dz_of = {}
    z_top = None
    gap = 22.0
    for n in ("foot", "collar", "body", "nose_cone"):
        m = mesh(n)
        lo, hi = bbox(m)
        dz = 0.0 if z_top is None else (z_top + gap) - lo[2]
        dz_of[n] = dz
        m.translate((0, 0, dz), inplace=True)
        st, coat = sc.style(n, "resin")
        sc.add(m, st, coat)
        # body's own label anchors low on its flank, clear of the grille/bezel/knob
        # cluster (pulled toward the camera off its front face, below); everything
        # else anchors at its own vertical centre.
        z_lbl = lo[2] + (hi[2] - lo[2]) * (0.12 if n == "body" else 0.5)
        anchors[n] = np.array([lo[0] - 2, 0, z_lbl + dz])
        z_top = hi[2] + dz
    body_dz = dz_of["body"]
    for n, out_y, z_frac in (("grille", -34, 0.85), ("bezel", -48, 0.08), ("knob", -20, 0.5)):
        m = mesh(n)
        m.translate((0, out_y, body_dz), inplace=True)
        st, coat = sc.style(n, "resin")
        sc.add(m, st, coat)
        lo, hi = bbox(m)
        anchors[n] = np.array([lo[0] - 2, (lo[1] + hi[1]) / 2, lo[2] + (hi[2] - lo[2]) * z_frac])
    # the three fins, laid out to the side (identical parts, printed x3)
    fm = mesh("fin_1")
    lo, hi = bbox(fm)
    fin_w = hi[0] - lo[0]
    fx0 = I["fin_tip_reach"] * 0.55 + 34
    fin_z = anchors["foot"][2] + 40
    for k in range(3):
        m = fm.copy()
        m.translate((fx0 + k * (fin_w + 16) - (lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2,
                     fin_z - (lo[2] + hi[2]) / 2), inplace=True)
        st, coat = sc.style("fin_1", "resin")
        sc.add(m, st, coat)
    # the leader points at the middle fin's own top edge, not empty space above the cluster
    anchors["fin_x3"] = np.array([fx0 + (fin_w + 16), 0, fin_z + (hi[2] - lo[2]) / 2 - 4])
    # A synthetic box, well clear of any real part, extends the fitted bounds
    # further left than the body cluster actually reaches -- reserving a
    # blank label column on the left of the frame (Faro's own exploded view
    # gets this for free from its wider part spread; Atelier's front-pulled
    # cluster sits close to the body, so it needs deliberate margin instead).
    lo_all = np.min([[b[0], b[2], b[4]] for b in sc.bounds], axis=0)
    hi_all = np.max([[b[1], b[3], b[5]] for b in sc.bounds], axis=0)
    margin_box = (lo_all[0] - 85, hi_all[0], lo_all[1], hi_all[1], lo_all[2], hi_all[2])
    sc.fit((0.55, -1.0, 0.22), margin=1.02, bounds=sc.bounds + [margin_box])
    stack_keys = ["foot", "collar", "body", "nose_cone"]           # the vertical spine: one shared left column
    front_keys = ["grille", "bezel", "knob"]                       # pulled toward the camera, off the body face
    pts = dict(zip(stack_keys + front_keys + ["fin_x3"],
                    sc.project([anchors[k] for k in stack_keys + front_keys] + [anchors["fin_x3"]])))
    img = sc.image()
    d = ImageDraw.Draw(img)
    Wpx, Hpx = img.size
    ref = {"foot": "Foot", "collar": "Collar", "body": "Body", "grille": "Grille", "bezel": "Bezel",
           "knob": "Knob", "fin_x3": "Fins x3", "nose_cone": "Nose cone"}
    # every spine and front-cluster label sits in one column outside (to the
    # left of) the whole stack, each with its own long gold leader back to
    # its part -- Faro's exploded-view style, rather than a short leader
    # hugging the part's edge.
    lx = min(pts[k][0] for k in stack_keys + front_keys) - 30 * S
    for k in stack_keys + front_keys:
        x, y = pts[k]
        draw_label(d, ref[k], (lx, y), (x, y), align="right", size=25)
    fx, fy = pts["fin_x3"]
    draw_label(d, ref["fin_x3"], (min(fx + 60 * S, Wpx - 20 * S), fy - 90 * S), (fx, fy), size=25)
    img = trim_to_content(img, pad=36 * S)
    return finish(img, "01_exploded_resin")


# ---- Step 02: parts as arrived, white resin -----------------------------------
def img_parts_as_arrived():
    sys.path.insert(0, str(ROOT))
    import build as abuild
    sc = Scene((1500, 1100))
    layout = [["body"], ["nose_cone", "collar", "foot"], ["grille", "bezel", "knob", "fin_1"]]
    labels_map = {"fin_1": "fin x3", "nose_cone": "nose cone"}
    boxes = []
    gap = 30
    rows = []
    for row in reversed(layout):
        meshes = []
        for n in row:
            posed, _ = abuild._print_pose(n, M.parts[n], I)
            meshes.append((n, atelier._to_mesh(posed, 0.03)))
        rows.append(meshes)
    y_row = 0.0
    for r, row_meshes in enumerate(rows):
        widths = [bbox(m)[1][0] - bbox(m)[0][0] for _, m in row_meshes]
        depth = max(bbox(m)[1][1] - bbox(m)[0][1] for _, m in row_meshes)
        if r:
            y_row += depth / 2 + 55
        x = -(sum(widths) + gap * (len(widths) - 1)) / 2
        for (n, m), w in zip(row_meshes, widths):
            lo, hi = bbox(m)
            m.translate((x - lo[0], y_row - (lo[1] + hi[1]) / 2, 0), inplace=True)
            st, coat = sc.style(n, "resin")
            sc.add(m, st, coat)
            sc.shadow(x - lo[0] + (lo[0] + hi[0]) / 2, y_row, max(hi[0] - lo[0], hi[1] - lo[1]) / 2, 0.25)
            lo2, hi2 = lo + (x - lo[0], y_row - (lo[1] + hi[1]) / 2, 0), hi + (x - lo[0], y_row - (lo[1] + hi[1]) / 2, 0)
            boxes.append((n, lo2, hi2))
            x += w + gap
        y_row += depth / 2
    sc.fit((0, -0.62, 1.0), margin=1.12)
    # Label each part below its own true screen-space footprint (all 8 world
    # bbox corners projected, then the lowest point on screen taken), not a
    # single world-space anchor -- a ring lying flat (the bezel) or a part
    # whose 3D "front" edge doesn't match its onscreen silhouette otherwise
    # gets its label placed on top of the part instead of below it. Projected
    # before sc.image(), which closes the plotter that project() needs.
    label_pos = []
    for n, lo2, hi2 in boxes:
        corners = [(x_, y_, z_) for x_ in (lo2[0], hi2[0]) for y_ in (lo2[1], hi2[1]) for z_ in (lo2[2], hi2[2])]
        pxs = sc.project(corners)
        cx = sum(p[0] for p in pxs) / len(pxs)
        by = max(p[1] for p in pxs)
        label_pos.append((n, cx, by))
    img = sc.image()
    d = ImageDraw.Draw(img)
    for n, cx, by in label_pos:
        draw_label(d, labels_map.get(n, n), (cx, by + 26 * S), None, align="center", size=25)
    return finish(img, "02_printed_parts")


# ---- Step 03: mounted for priming, grey ---------------------------------------
def img_priming():
    sc = Scene((1500, 950))
    names = ["body", "nose_cone", "collar", "foot", "grille", "bezel", "knob", "fin_1"]
    labels_map = {"fin_1": "fin x3", "nose_cone": "nose cone"}
    gap = 30
    x = 0.0
    labels = []
    heights = []
    for n in names:
        m = mesh(n)
        lo, hi = bbox(m)
        h = hi[2] - lo[2]
        heights.append(h)
    base_y = 0.0
    stick_top = max(heights) * 0.55
    for n, h in zip(names, heights):
        m = mesh(n)
        lo, hi = bbox(m)
        w = hi[0] - lo[0]
        cx = x + w / 2
        m.translate((cx - (lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, stick_top - lo[2]), inplace=True)
        st, coat = sc.style(n, "primer")
        sc.add(m, st, coat)
        stick = pv.Cylinder(center=(cx, 0, stick_top / 2), direction=(0, 0, 1), radius=3.2, height=stick_top,
                            resolution=24)
        sc.add(stick, dict(color=lin("#C9A56A"), pbr=True, metallic=0.0, roughness=0.6), outline=False)
        labels.append((n, np.array([cx, 0, stick_top + (hi[2] - lo[2]) + 6])))
        x += w + gap
    board = pv.Cube(center=(x / 2 - gap / 2, 0, -6), x_length=x, y_length=80, z_length=6)
    sc.add(board, dict(color=lin("#C9A56A"), pbr=True, metallic=0.0, roughness=0.7), outline=False)
    sc.fit((0.05, -1.0, 0.18), margin=1.1)
    pts = sc.project([a for _, a in labels])
    img = sc.image()
    d = ImageDraw.Draw(img)
    for (n, _), (px, py) in zip(labels, pts):
        draw_label(d, labels_map.get(n, n), (px, py), None, align="center", size=25)
    return finish(img, "03_priming")


# ---- Step 04: paint groups ------------------------------------------------------
def img_paint_groups():
    sc = Scene((1500, 720))
    groups = [("Oxblood gloss", ["body"]), ("Metallic gold", ["nose_cone", "fin_1", "grille", "bezel", "knob",
              "collar", "foot"]), ("Matt black", ["grille_paint"])]
    x = 0.0
    gap = 60
    labels = []
    for title, names in groups:
        sub_x = x
        for n in names:
            m = mesh(n)
            lo, hi = bbox(m)
            w = hi[0] - lo[0]
            m.translate((sub_x - lo[0], -(lo[1] + hi[1]) / 2, -lo[2]), inplace=True)
            st, coat = sc.style(n, "paint")
            sc.add(m, st, coat)
            sub_x += w + 16
        labels.append((title, np.array([(x + sub_x - 16) / 2, 0, -14])))
        x = sub_x + gap
    sc.fit((0, -1.0, 0.35), margin=1.1)
    pts = sc.project([a for _, a in labels])
    img = sc.image()
    d = ImageDraw.Draw(img)
    for (title, _), (px, py) in zip(labels, pts):
        draw_label(d, title, (px, py), None, align="center", size=24)
    return finish(img, "04_paint_groups")


# ---- Before you begin: the front, finished --------------------------------------
def img_front_finished():
    """Page 2 (Before you begin): a finished close-up of the front -- grille,
    LED and knob on the lacquered oxblood body -- so the reader sees the
    target result before starting, in place of the earlier dry-fit shot."""
    sc = Scene((1000, 1100))
    for n in ("body", "grille_paint", "grille", "bezel", "knob"):
        add_painted(sc, n, lit=True)
    led = M.envelopes.get("led")
    if led is not None:
        col = hexrgb(p.LED_HEX)
        sc.add(atelier._to_mesh(led, 0.02), dict(color=col, lighting=False), outline=False)
        z = I["z_led"]
        y = -M._r_out(z) - 0.25
        halo = pv.Disc(center=(0, y, z), inner=0, outer=p.LED_DIA * 1.6, normal=(0, -1, 0), r_res=24, c_res=48)
        r = np.linalg.norm(halo.points[:, [0, 2]] - np.array([0, z]), axis=1)
        glow = np.exp(-(r / (p.LED_DIA * 0.55)) ** 2) * 0.85
        rgba = np.column_stack([np.tile(np.array(col) * 255, (len(r), 1)), glow * 255])
        halo["rgba"] = rgba.astype(np.uint8)
        sc.pl.add_mesh(halo, scalars="rgba", rgba=True, lighting=False, show_scalar_bar=False)
    base = zoom_bounds(I["z_knob"] - 18, I["z_grille"] + 42, r=48, y=0)
    sc.fit((0.4, -1.0, 0.15), margin=1.1, bounds=base)
    return finish(sc.image(), "front_finished")


# ---- Step 04: colour reference views -------------------------------------------
def img_views():
    """Colour reference, one per side: framed tight (not the wide margin a
    full hero shot uses) so the prototype fills the column it's printed at."""
    for name, direction in (("front", (0, -1, 0.12)), ("side", (1, 0, 0.12)), ("rear", (0, 1, 0.12)),
                             ("three_quarter", (0.62, -0.78, 0.2))):
        sc = Scene((700, 1000))
        for n in ORDER:
            add_painted(sc, n, lit=True)
        sc.shadow(0, 0, I["fin_tip_reach"], 0.4)
        sc.fit(direction, margin=1.02)
        finish(sc.image(), f"04_view_{name}")


# ---- Step 07: stability check -- a straight underside view for the record ------
# (The tip test itself is physical: rest the real prototype on the fins and nudge
# it. The unweighted comparison happens back in Step 06, before the collar seals
# the shot in; this step repeats it weighted, as built. There's no simulated
# "tips at N deg" render here: that would be faking a measurement the model can't
# make for a hand-glued, hand-weighted resin part -- only the real prototype's
# own mass and glue lines can.)
def img_underside():
    sc = Scene((900, 900))
    for n in ORDER:
        add_painted(sc, n, lit=True)
    sc.fit((0, 0.05, -1.0), up=(0, 1, 0), margin=1.15)
    return finish(sc.image(), "07_underside")


# ---- Troubleshooting: a fin's root, flush against the body ----------------------
def img_fin_root():
    """What a good fit looks like for 'Fin sits proud, or rocks': two fin
    roots flush against the body, in finished colours (this is a reference
    photo of correct results, not an assembly step, so nothing is faded or
    highlighted), framed wide enough that both are fully in shot."""
    sc = Scene((1000, 800))
    for n in ("body", "grille_paint", "grille", "bezel", "knob", "fin_1", "fin_2", "fin_3"):
        add_painted(sc, n, lit=True)
    base = zoom_bounds(I["z0"] - 5, I["z_fin_root_top"] + 20, r=95)
    sc.fit((0.55, -0.95, 0.15), margin=1.15, bounds=base)
    return finish(sc.image(), "TS_fin_root")


REGISTRY = {
    "hero": img_hero,
    "front_finished": img_front_finished,
    "step1": assembly_step_1_of_2,
    "step2": assembly_step_2_of_2,
    "exploded": img_exploded,
    "parts_as_arrived": img_parts_as_arrived,
    "priming": img_priming,
    "paint_groups": img_paint_groups,
    "views": img_views,
    "underside": img_underside,
    "fin_root": img_fin_root,
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
