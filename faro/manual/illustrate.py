"""
Illustrations for the Faro prototype build manual, rendered from the CAD model.

    python faro/manual/illustrate.py            # all images -> faro/output/manual/images/
    python faro/manual/illustrate.py hero cap   # only images whose name contains these words

One style throughout: clean studio renders on the manual's warm off-white
paper colour (so they sit on the page without a box), fine dark outlines, serif
labels with thin gold leader lines. Parts show the stage they're at: matt white
resin (inspection, preparation), grey primer (priming), painted colours (from
painting on). In the assembly steps the parts already in place are softened and
the new part is drawn in full colour with a deep red outline.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
import vtk
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FARO = HERE.parent
sys.path.insert(0, str(FARO))
import lamp  # noqa: E402
import params as p  # noqa: E402
import studio  # noqa: E402

atelier = studio.atelier
OUT = FARO / "output" / "manual" / "images"
FONTS = HERE / "fonts"

# ---- the manual's palette ---------------------------------------------------
PAPER = "#F8F4EC"                  # page colour; images use it as their background
INK = (43, 36, 32)                 # body text
GOLD_RULE = (176, 138, 62)         # leader lines, rules, number rings
ACCENT = "#9B1B14"                 # highlight outline / arrows (the Faro red, a touch deeper)
OUTLINE = "#4A3E34"                # fine outlines
RESIN = "#EEEBE3"
PRIMER = "#A6A5A0"
FROST = "#F3F1EC"
BURNT_UMBER = "#4E3222"
BLACK_PAINT = "#1F1D1C"
COPPER = "#B8733A"
BEAD = "#FFD27A"

S = 2                               # render scale for crisp lines and text


def hexrgb(h):
    return atelier.hex_rgb(h)


def lin(h):
    return atelier.hex_linear(h)


def font(size, kind="regular"):
    f = {"regular": "EBGaramond-Regular.ttf", "medium": "EBGaramond-Medium.ttf",
         "italic": "EBGaramond-Italic.ttf", "display": "CormorantGaramond-SemiBold.ttf"}[kind]
    return ImageFont.truetype(str(FONTS / f), int(size * S))


# ---- the model and its derived pieces ----------------------------------------
M = lamp.build(p)
I = M.info
LIFT = I["felt_proud"]


def _split_nameplate():
    """The nameplate as three solids: the brass plate, the raised letters, and a
    thin black wash on the plate face round the letters (render only)."""
    from build123d import Align, Cylinder, FontStyle, Plane, Pos, RectangleRounded, Text, extrude
    rb = p.BASE_DIA / 2 * p.OVERALL_HEIGHT / p.REF_HEIGHT
    r_face = rb - p.NAMEPLATE_RECESS + p.NAMEPLATE_THICK
    ring = Cylinder(r_face + 5, 400, align=(Align.CENTER, Align.CENTER, Align.MIN)) - \
        Cylinder(r_face + 0.01, 400, align=(Align.CENTER, Align.CENTER, Align.MIN))
    np_ = M.parts["nameplate"]
    zn = p.NAMEPLATE_Z * p.OVERALL_HEIGHT / p.REF_HEIGHT + LIFT
    prism = lambda face: Pos(0, 0, zn) * extrude(Plane.XZ * face, amount=400)
    shell = Cylinder(r_face + 0.05, 400, align=(Align.CENTER, Align.CENTER, Align.MIN)) - \
        Cylinder(r_face - 0.02, 400, align=(Align.CENTER, Align.CENTER, Align.MIN))
    wash = shell & prism(RectangleRounded(p.NAMEPLATE_W - 1.8, p.NAMEPLATE_H - 1.8, 0.6))
    wash = wash - prism(Text(p.NAMEPLATE_TEXT, p.NAMEPLATE_TEXT_H, font_style=FontStyle.BOLD))
    return np_ - ring, np_ & ring, wash


PLATE, LETTERS, WASH = _split_nameplate()
MESH = {}


def mesh(name):
    """Triangulated part (cached). Extra names: nameplate_plate, nameplate_letters."""
    if name not in MESH:
        shape = {"nameplate_plate": PLATE, "nameplate_letters": LETTERS, "nameplate_wash": WASH}.get(name) \
            or M.parts[name]
        MESH[name] = atelier._to_mesh(shape, 0.03)
    return MESH[name].copy()


def bbox(m):
    b = m.bounds
    return np.array([b[0], b[2], b[4]]), np.array([b[1], b[3], b[5]])


# ---- extra props: fairy lights, battery box, coins, LED puck, dowels -----------
def tube(points, r, n=24):
    spline = pv.Spline(np.asarray(points, dtype=float), max(200, 6 * len(points)))
    return spline.tube(radius=r, n_sides=n)


def fairy_lights(coil=True, feed=True):
    """Wire (copper) + bead LEDs. The feed runs from a battery box behind the
    lamp, in through the rear port, across the base bay and up the wire hole;
    the coil winds loosely up inside the tower."""
    rb = I["base_dia"] / 2
    zc = p.USBC_Z + LIFT
    z_top_base = I["base_h"] + LIFT
    z_t0, z_t1 = I["z_red_top"], I["z_tower_top"]
    pts, beads = [], []
    if feed:
        pts += [(0, rb + 70, 1.0), (0, rb + 30, 1.0), (0, rb + 6, zc - 3), (0, rb - 1, zc),
                (0, rb - 12, zc + 2), (0, 6, zc + 6), (0, 0, z_top_base - 4), (0, 0, z_top_base + 8)]
    if coil:
        r0 = p.TOWER_BOTTOM_DIA / 2 - 12
        r1 = p.TOWER_TOP_DIA / 2 - 9
        start = z_top_base + 12
        turns = 3.2
        for k in range(1, 161):
            f = k / 160
            z = start + f * (z_t1 - 14 - start)
            r = r0 + (r1 - r0) * (z - z_t0) / (z_t1 - z_t0)
            a = 2 * math.pi * turns * f
            pts.append((r * math.sin(a), -r * math.cos(a), z))
            if k % 10 == 5:
                beads.append((r * math.sin(a), -r * math.cos(a), z))
    wire = tube(pts, 0.45)
    if feed:
        for t in np.linspace(0.08, 0.3, 3):                       # a few beads outside, near the box
            beads.append((0, rb + 70 - t * 120, 1.2))
    bead_mesh = None
    for b in beads:
        s = pv.Sphere(radius=1.5, center=b)
        bead_mesh = s if bead_mesh is None else bead_mesh.merge(s)
    return wire, bead_mesh


def fairy_lights_path():
    """Just the feed run (battery box -> rear port -> up through the base)."""
    rb = I["base_dia"] / 2
    zc = p.USBC_Z + LIFT
    z_top_base = I["base_h"] + LIFT
    return [(0, rb + 70, 1.0), (0, rb + 30, 1.0), (0, rb + 6, zc - 3), (0, rb - 1, zc),
            (0, rb - 12, zc + 2), (0, 6, zc + 6), (0, 0, z_top_base - 4), (0, 0, z_top_base + 30)]


def battery_box():
    rb = I["base_dia"] / 2
    box = pv.Box(bounds=(-14, 14, rb + 70, rb + 132, 0, 16)).triangulate()
    cells = None
    for x in (-6.5, 6.5):
        c = pv.Cylinder(center=(x, rb + 101, 7.5), direction=(0, 1, 0), radius=6.8, height=50)
        cells = c if cells is None else cells.merge(c)
    return box, cells


COIN_ANGLES = (0, 90, 270)      # spread round the bay, clear of the wire from the rear port


def coins():
    """Three short stacks of coins taped to the ceiling of the base bay, clear of
    the battery and the wire hole."""
    z_floor = p.PLATE_THICK + LIFT                  # on the plate, low in the base
    out = None
    for ang in COIN_ANGLES:
        a = math.radians(ang)
        x, y = 36 * math.sin(a), -36 * math.cos(a)
        for k in range(4):
            c = pv.Cylinder(center=(x, y, z_floor + 1.3 + 2.6 * k), direction=(0, 0, 1),
                            radius=11.7, height=2.4, resolution=64)
            out = c if out is None else out.merge(c)
    return out


def tape():
    z_top = p.PLATE_THICK + LIFT + 10.5
    out = None
    for ang in COIN_ANGLES:
        a = math.radians(ang)
        x, y = 36 * math.sin(a), -36 * math.cos(a)
        strip = pv.Box(bounds=(-4, 4, -17, 17, -0.2, 0.2)).triangulate()
        strip.rotate_z(ang, inplace=True)
        strip.translate((x, y, z_top), inplace=True)
        out = strip if out is None else out.merge(strip)
    return out


def led_puck(z=None):
    z = I["z_lantern"][0] + 2 if z is None else z
    body = pv.Cylinder(center=(0, 0, z + 8), direction=(0, 0, 1), radius=21.5, height=16, resolution=96)
    lens = pv.Cylinder(center=(0, 0, z + 16.2), direction=(0, 0, 1), radius=17, height=0.6, resolution=96)
    return body, lens


# ---- plotter ---------------------------------------------------------------
class Scene:
    """A studio plotter on the manual's paper colour, with outline helpers and
    world -> image projection for labels."""

    def __init__(self, size=(1400, 1000), lights=1.0):
        self.size = (size[0] * S, size[1] * S)
        pl = pv.Plotter(off_screen=True, window_size=list(self.size), lighting="none")
        pl.set_background(PAPER)
        pl.enable_anti_aliasing("ssaa")
        if atelier._ENV is None:
            atelier._ENV = atelier._studio_environment()
        pl.set_environment_texture(atelier._ENV)
        pl.renderer.GetEnvMapPrefiltered().SetPrefilterMaxSamples(256)
        pl.renderer.SetEnvironmentUp(0, 0, 1)
        pl.renderer.SetEnvironmentRight(1, 0, 0)
        for pos, k in (((-500, -700, 700), atelier.LIGHT_KEY), ((700, -350, 250), atelier.LIGHT_FILL),
                       ((150, 800, 600), atelier.LIGHT_RIM)):
            pl.add_light(pv.Light(position=pos, focal_point=(0, 0, 150), intensity=k * p.LIGHT_GAIN * lights))
        self.pl = pl
        self.shadows = []
        self.bounds = []

    # materials by stage ------------------------------------------------------
    def style(self, name, stage, lit=False, soft=False):
        frosted = name.startswith(("lantern_glass", "window_diffuser"))
        if stage == "resin":
            st = (dict(color=lin(FROST), opacity=0.6, pbr=True, metallic=0.0, roughness=0.35) if frosted else
                  dict(color=lin(RESIN), pbr=True, metallic=0.0, roughness=0.55))
            coat = False
        elif stage == "primer":
            st, coat = dict(color=lin(PRIMER), pbr=True, metallic=0.0, roughness=0.8), False
        else:                                                            # painted
            if frosted:
                st = (dict(color=hexrgb(p.GLOW_HEX), lighting=False) if lit else
                      dict(color=lin(FROST), opacity=0.55, pbr=True, metallic=0.0, roughness=0.3))
                coat = False
            elif name == "nameplate_wash":
                st, coat = dict(color=lin(BLACK_PAINT), pbr=True, metallic=0.0, roughness=0.6), False
            elif name in ("nameplate_plate", "nameplate_letters"):
                st, coat = studio._material("nameplate", p)
            elif name == "base":
                st, coat = dict(color=lin(BURNT_UMBER), pbr=True, metallic=0.0, roughness=0.6), False
            elif name == "base_plate":
                st, coat = dict(color=lin(BLACK_PAINT), pbr=True, metallic=0.0, roughness=0.55), False
            else:
                st, coat = studio._material(name, p)
            if name in studio.BRASS or name in ("nameplate_plate", "nameplate_letters"):
                st = dict(st, roughness=0.45)          # satin, so flat faces don't mirror a dark studio
        st = dict(st)
        if soft:                                         # parts already in place: softened
            if "color" in st and st.get("lighting", True) is not False:
                c = np.array(st["color"])
                st["color"] = tuple(c * 0.45 + np.array(lin(PAPER)) * 0.55)
                if st.get("metallic", 0) > 0.5:
                    st["metallic"] = 0.6
            coat = False
        return st, coat

    def add(self, m, style, coat=False, outline=True, highlight=False, smooth=True):
        kw = dict(style)
        self.bounds.append(m.bounds)
        a = self.pl.add_mesh(m, smooth_shading=smooth, **kw)
        if highlight or outline:
            # outlines from a vertex-merged copy, so only true silhouettes are drawn
            # (the render mesh has separate vertices per face, for crisp normals)
            clean = pv.PolyData(m.points, m.faces).clean(tolerance=1e-4)
            self.pl.add_silhouette(clean, color=ACCENT if highlight else OUTLINE,
                                   line_width=(3.0 if highlight else 1.1) * S)
        if coat:
            prop = a.GetProperty()
            prop.SetCoatStrength(p.LACQUER_CLEARCOAT)
            prop.SetCoatRoughness(0.05)
            prop.SetCoatColor(1.0, 1.0, 1.0)
            prop.SetCoatIOR(1.5)
        return a

    def part(self, name, stage="paint", offset=(0, 0, 0), lit=False, soft=False, highlight=False,
             outline=True, transform=None):
        m = mesh(name)
        if transform is not None:
            m = transform(m)
        m.translate(offset, inplace=True)
        st, coat = self.style(name, stage, lit, soft)
        self.add(m, st, coat, outline=outline, highlight=highlight)
        return m

    def shadow(self, x, y, r, strength=0.35, z=0.05):
        g = pv.Disc(center=(x, y, z), inner=0, outer=r * 1.9, normal=(0, 0, 1), r_res=40, c_res=96)
        d = np.linalg.norm(g.points[:, :2] - np.array([x, y]), axis=1)
        a = strength * np.exp(-(np.maximum(d - r * 0.75, 0) / (r * 0.28 + 3)) ** 2)
        rgba = np.zeros((len(d), 4))
        rgba[:, :3] = np.array([0.30, 0.24, 0.19]) * 255
        rgba[:, 3] = np.clip(a, 0, 1) * 255
        g["rgba"] = rgba.astype(np.uint8)
        self.pl.add_mesh(g, scalars="rgba", rgba=True, lighting=False, show_scalar_bar=False)

    def camera(self, focal, direction, dist=None, view_angle=22, parallel_scale=None, up=(0, 0, 1)):
        d = np.array(direction, dtype=float)
        d /= np.linalg.norm(d)
        c = self.pl.camera
        c.focal_point = tuple(focal)
        c.position = tuple(np.array(focal) + d * (dist or 1000))
        c.up = up
        if parallel_scale:
            self.pl.enable_parallel_projection()
            c.parallel_scale = parallel_scale
        else:
            c.view_angle = view_angle
        self.pl.reset_camera_clipping_range()

    def fit(self, direction, up=(0, 0, 1), margin=1.1, bounds=None):
        """Orthographic view along `direction`, framed to everything added (or `bounds`)."""
        bl = bounds or self.bounds
        lo = np.min([[b[0], b[2], b[4]] for b in bl], axis=0)
        hi = np.max([[b[1], b[3], b[5]] for b in bl], axis=0)
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        d = np.array(direction, float)
        d /= np.linalg.norm(d)
        right = np.cross(-d, np.array(up, float))
        right /= np.linalg.norm(right)
        tup = np.cross(right, -d)
        ctr = (lo + hi) / 2
        rel = corners - ctr
        r_ = rel @ right
        u_ = rel @ tup
        ctr = ctr + right * (r_.max() + r_.min()) / 2 + tup * (u_.max() + u_.min()) / 2
        aspect = self.size[0] / self.size[1]
        half = max((u_.max() - u_.min()) / 2, (r_.max() - r_.min()) / 2 / aspect) * margin
        self.camera(ctr, d, dist=3000, parallel_scale=half, up=tuple(tup))

    def project(self, pts):
        self.pl.render()
        co = vtk.vtkCoordinate()
        co.SetCoordinateSystemToWorld()
        out = []
        for q in pts:
            co.SetValue(*[float(v) for v in q])
            x, y = co.GetComputedDoubleDisplayValue(self.pl.renderer)
            out.append((x, self.size[1] - y))
        return out

    def image(self):
        img = Image.fromarray(self.pl.screenshot(return_img=True))
        self.pl.close()
        return img


# ---- 2D annotation (drawn on the render at S x scale) -------------------------
def draw_label(d, text, at, anchor, align="left", size=17, sub=None):
    """Label at `at` (image px) with a thin gold leader to `anchor`, ending in a dot."""
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


ARROW_INK = "#2B2420"


def arrow(d, a, b, color=ARROW_INK, width=2.2, head=11, halo=True):
    col = tuple(int(c * 255) for c in hexrgb(color)) if isinstance(color, str) else color
    if halo:                                     # a thin paper-coloured halo so it reads on any colour
        paper = tuple(int(c * 255) for c in hexrgb(PAPER))
        d.line([a, b], fill=paper, width=int((width + 3) * S))
    d.line([a, b], fill=col, width=int(width * S))
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    h = head * S
    p1 = (b[0] - h * math.cos(ang - 0.42), b[1] - h * math.sin(ang - 0.42))
    p2 = (b[0] - h * math.cos(ang + 0.42), b[1] - h * math.sin(ang + 0.42))
    d.polygon([b, p1, p2], fill=col)


def polyline_arrow(d, pts, color=ARROW_INK, width=2.4, head=13):
    col = tuple(int(c * 255) for c in hexrgb(color))
    paper = tuple(int(c * 255) for c in hexrgb(PAPER))
    d.line(pts, fill=paper, width=int((width + 3) * S), joint="curve")
    d.line(pts, fill=col, width=int(width * S), joint="curve")
    arrow(d, pts[-2], pts[-1], color=color, width=width, head=head, halo=False)


def finish(img, name):
    """Downsample from the S x working size and save."""
    OUT.mkdir(parents=True, exist_ok=True)
    w, h = img.size
    img = img.resize((w // S, h // S), Image.LANCZOS)
    path = OUT / f"{name}.png"
    img.save(path)
    print("  ", path.name, img.size)
    return path


# ---- assembled positions ---------------------------------------------------------
ORDER = ["base_plate", "base", "nameplate", "band_cream", "band_red", "knob", "tower",
         "window_diffuser_1", "window_diffuser_2", "window_diffuser_3", "window_diffuser_4",
         "window_diffuser_5", "gallery", "lantern_glass", "lantern_frame", "cap", "finial"]
PAINTED_NAMES = {"nameplate": ("nameplate_plate", "nameplate_letters", "nameplate_wash")}


def add_painted(sc, name, **kw):
    for sub in PAINTED_NAMES.get(name, (name,)):
        sc.part(sub, "paint", **kw)


def lamp_center():
    return np.array([0, 0, I["H"] * 0.5])


# =============================================================================
# 1. printed parts as they arrive (white resin, labelled)
# =============================================================================
def img_parts_as_arrived():
    import build as fbuild
    sc = Scene((1500, 1000))
    layout = [["tower", "cap", "gallery", "lantern_frame", "lantern_glass"],
              ["base", "base_plate", "band_red", "band_cream"],
              ["nameplate", "knob", "finial", "window_diffuser_1", "window_diffuser_2",
               "window_diffuser_3", "window_diffuser_4", "window_diffuser_5"]]
    names_ = {"window_diffuser_1": "1", "window_diffuser_2": "2", "window_diffuser_3": "3",
              "window_diffuser_4": "4", "window_diffuser_5": "5"}
    labels = []
    gap = 26
    placed = []
    rows = []
    for row in reversed(layout):                         # small parts in front, tall ones at the back
        meshes = []
        for n in row:
            shape = M.parts[n]
            if n.startswith("window_diffuser"):             # turn its window to the front first
                from build123d import Rot
                shape = Rot(0, 0, -I["windows"][int(n[-1]) - 1][1]) * shape
            posed, _ = fbuild._print_pose(n, shape)
            meshes.append((n, atelier._to_mesh(posed, 0.03)))
        rows.append(meshes)
    y_row = 0.0
    for r, meshes in enumerate(rows):
        widths = [bbox(m)[1][0] - bbox(m)[0][0] for _, m in meshes]
        depth = max(bbox(m)[1][1] - bbox(m)[0][1] for _, m in meshes)
        if r:
            y_row += depth / 2 + 55
        x = -(sum(widths) + gap * (len(widths) - 1)) / 2
        for (n, m), w in zip(meshes, widths):
            lo, hi = bbox(m)
            m.translate((x - lo[0], y_row - (lo[1] + hi[1]) / 2, 0), inplace=True)
            placed.append((n, m))
            x += w + gap
        y_row += depth / 2
    for n, m in placed:
        st, coat = sc.style(n, "resin")
        sc.add(m, st, coat)
        lo, hi = bbox(m)
        sc.shadow((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, max(hi[0] - lo[0], hi[1] - lo[1]) / 2, 0.25)
        labels.append((n, ((lo[0] + hi[0]) / 2, lo[1] - 4, 0)))
    sc.fit((0, -0.62, 1.0), margin=1.12)
    pts = sc.project([q for _, q in labels])
    img = sc.image()
    d = ImageDraw.Draw(img)
    for (n, _), (x, y) in zip(labels, pts):
        text = names_.get(n, n)
        if n.startswith("window_diffuser"):
            text = f"diffuser {text}"
        draw_label(d, text, (x, y + 24 * S), None, align="center", size=25)
    return finish(img, "01_printed_parts")


# =============================================================================
# 2. exploded views (resin for step 1; painted and numbered for the overview)
# =============================================================================
EXPLODE = [  # (group name, parts, extra z gap above the previous group)
    ("base_plate", ["base_plate"], 0),
    ("base", ["base", "nameplate"], 26),
    ("band_cream", ["band_cream"], 22),
    ("band_red", ["band_red", "knob"], 22),
    ("tower", ["tower"], 26),
    ("gallery", ["gallery"], 30),
    ("lantern_glass", ["lantern_glass"], 26),
    ("lantern_frame", ["lantern_frame"], 26),
    ("cap", ["cap"], 30),
    ("finial", ["finial"], 22),
]


def exploded_offsets(with_felt=False):
    offs, dz = {}, 0.0
    for g, parts, gap in EXPLODE:
        dz += gap
        for n in parts:
            offs[n] = dz
    if with_felt:
        offs = {k: v + 24 for k, v in offs.items()}
        offs["felt_pad"] = 0.0
    return offs


def img_exploded(stage):
    painted = stage == "paint"
    offs = exploded_offsets(with_felt=painted)
    sc = Scene((1100, 1500))
    anchors = {}
    if not painted:                                  # step 1: glass inside its frame, knob/plate on their bands
        offs["lantern_glass"] = offs["lantern_frame"]
    for n, dz in offs.items():
        off = [0, 0, dz]
        if painted and n == "nameplate":
            off = [0, -18, dz]
        if painted and n == "knob":
            off = [0, -22, dz]
        if painted:
            add_painted(sc, n, offset=off) if n != "felt_pad" else sc.part(n, "paint", offset=off)
        else:
            sc.part(n, "resin", offset=off)
        m = mesh(n)
        lo, hi = bbox(m)
        anchors[n] = np.array([lo[0] + 2, 0, (lo[2] + hi[2]) / 2]) + np.array(off)
    # the five diffusers, pulled out to the right of the tower
    tz = offs["tower"]
    for k in range(5):
        n = f"window_diffuser_{k + 1}"
        m = mesh(n)
        lo, hi = bbox(m)
        c = (lo + hi) / 2
        m.translate((-c[0] + 78 + (k % 3) * 20, -c[1] - 10, -c[2] + tz + 110 + (k // 3) * 32), inplace=True)
        st, coat = sc.style(n, "paint" if painted else "resin")
        sc.add(m, st, coat)
    anchors["diffusers"] = np.array([80, -10, tz + 150])
    sc.fit((0.55, -1.0, 0.32), margin=1.04)
    keys = [k for k in (["felt_pad"] if painted else []) + [e[0] for e in EXPLODE]] + ["nameplate", "knob"]
    pts = dict(zip(keys + ["diffusers"], sc.project([anchors[k] for k in keys] + [anchors["diffusers"]])))
    img = sc.image()
    d = ImageDraw.Draw(img)
    W = img.size[0]
    number = {"base_plate": 1, "base": 2, "band_cream": 3, "band_red": 4, "tower": 5, "gallery": 6,
              "lantern_glass": 7, "lantern_frame": 8, "cap": 9, "finial": 10, "felt_pad": 11, "nameplate": 12}
    subs = {"base": "wood effect, burnt umber", "base_plate": "black", "band_cream": "cream gloss",
            "band_red": "red gloss", "tower": "cream gloss", "gallery": "gold", "lantern_glass": "translucent",
            "lantern_frame": "gold", "cap": "red gloss", "finial": "gold", "felt_pad": "black self-adhesive felt",
            "nameplate": "gold, black round the letters", "knob": "gold, front of the red band"}
    ref = {"finial": "Finial", "cap": "Cap (twist-lock)", "lantern_frame": "Lantern frame over glass",
           "gallery": "Gallery", "tower": "Tower (5 windows)", "band_red": "Red band + knob",
           "band_cream": "Cream band", "base": "Base + nameplate", "base_plate": "Base plate"}
    for k in keys:
        if k in ("nameplate", "knob") or (not painted and k == "lantern_glass"):
            continue
        x, y = pts[k]
        lx = 250 * S
        text = (k if k != "felt_pad" else "felt") if painted else ref[k]
        draw_label(d, text, (lx, y), (x, y), align="right", size=17 if painted else 25,
                   sub=subs[k] if painted else None)
        if painted:
            badge(d, (lx - 175 * S, y + 4 * S), number[k], size=13)
    # nameplate and knob: labels on the right
    for k in (("nameplate", "knob") if painted else ()):
        x, y = pts[k]
        draw_label(d, k, (W - 260 * S, y + 30 * S), (x + 30 * S, y), size=17, sub=subs[k] if painted else None)
        if painted and k == "nameplate":
            badge(d, (W - 285 * S, y + 34 * S), 12, size=13)
    x, y = pts["diffusers"]
    draw_label(d, "window diffusers 1-5" if painted else "Diffusers 1 to 5", (W - 290 * S, y - 120 * S),
               (x + 60 * S, y - 40 * S), size=17 if painted else 25, sub="translucent" if painted else None)
    return finish(img, "02_exploded_painted" if painted else "02_exploded_resin")


# =============================================================================
# 3. parts on dowels for priming (grey)
# =============================================================================
def img_priming():
    sc = Scene((1500, 950))
    rows = [["base", "tower", "cap", "gallery", "lantern_frame"],
            ["base_plate", "band_red", "band_cream", "nameplate", "knob", "finial"]]
    tops = []
    y_rows = (95, -95)
    for row, y0 in zip(rows, y_rows):
        widths = [bbox(mesh(n))[1][0] - bbox(mesh(n))[0][0] for n in row]
        x = -(sum(widths) + 28 * (len(row) - 1)) / 2
        for n, w in zip(row, widths):
            m = mesh(n)
            lo, hi = bbox(m)
            h_dowel = 55 if y0 < 0 else 75
            m.translate((x + w / 2 - (lo[0] + hi[0]) / 2, y0 - (lo[1] + hi[1]) / 2, h_dowel - lo[2]), inplace=True)
            dowel = pv.Cylinder(center=(x + w / 2, y0, h_dowel / 2 + 1), direction=(0, 0, 1), radius=3,
                                height=h_dowel + 2, resolution=32)
            sc.add(dowel, dict(color=lin("#D9C29A"), pbr=True, metallic=0.0, roughness=0.7))
            st, coat = sc.style(n, "primer")
            sc.add(m, st, coat)
            lo2, hi2 = bbox(m)
            tops.append((n, ((lo2[0] + hi2[0]) / 2, (lo2[1] + hi2[1]) / 2, hi2[2] + 2)))
            x += w + 28
    xs = [b[0] for b in sc.bounds] + [b[1] for b in sc.bounds]
    board = pv.Box(bounds=(min(xs) - 25, max(xs) + 25, -125, 125, -14, 0)).triangulate()
    sc.add(board, dict(color=lin("#CDB894"), pbr=True, metallic=0.0, roughness=0.8))
    sc.fit((0.0, -1.0, 0.42), margin=1.14)
    pts = sc.project([q for _, q in tops])
    img = sc.image()
    d = ImageDraw.Draw(img)
    for (n, _), (px, py) in zip(tops, pts):
        draw_label(d, n, (px, py - 44 * S), (px, py - 6 * S), align="center", size=27)
    return finish(img, "03_priming")


# =============================================================================
# 4. the five painted colour groups
# =============================================================================
GROUPS = [
    ("Red gloss", ["band_red", "cap"]),
    ("Cream gloss", ["band_cream", "tower"]),
    ("Metallic gold", ["gallery", "lantern_frame", "knob", "finial", "nameplate_gold"]),
    ("Burnt umber acrylic", ["base"]),
    ("Black acrylic", ["base_plate", "nameplate"]),
]


def img_paint_groups():
    panels = []
    for title, names in GROUPS:
        sc = Scene((400, 430))
        rows = [names[:2], names[2:]] if len(names) > 2 else [names]
        placed = []
        y0 = 0.0
        for row in rows:
            x = 0.0
            row_h = 0.0
            for n in row:
                subs = {"nameplate": ("nameplate_plate", "nameplate_letters", "nameplate_wash"),
                        "nameplate_gold": ("nameplate_plate", "nameplate_letters")}.get(n, (n,))
                ms = [mesh(q) for q in subs]
                lo = np.min([bbox(q)[0] for q in ms], axis=0)
                hi = np.max([bbox(q)[1] for q in ms], axis=0)
                for q_name, q in zip(subs, ms):
                    q.translate((x - lo[0], -(lo[1] + hi[1]) / 2, y0 - lo[2]), inplace=True)
                    st, coat = sc.style(q_name, "paint")
                    sc.add(q, st, coat)
                placed.append((n, (x + (hi[0] - lo[0]) / 2, -(hi[1] - lo[1]) / 2 - 2, y0)))
                x += hi[0] - lo[0] + 22
                row_h = max(row_h, hi[2] - lo[2])
            y0 -= row_h + 34
        sc.fit((0.3, -1.0, 0.35), margin=1.25)
        lab = sc.project([q for _, q in placed])
        img = sc.image()
        d = ImageDraw.Draw(img)
        nice = {"nameplate_gold": "nameplate", "nameplate": "round letters", "lantern_frame": "frame",
                "band_cream": "band", "band_red": "band", "base_plate": "plate"}
        for (n, _), (lx, ly) in zip(placed, lab):
            draw_label(d, nice.get(n, n), (lx, ly + 30 * S), None, align="center", size=27)
        panels.append((title, img))
    gap = 16 * S
    w = sum(im.size[0] for _, im in panels) + gap * (len(panels) - 1)
    h = panels[0][1].size[1] + 110 * S
    sheet = Image.new("RGB", (w, h), tuple(int(c * 255) for c in hexrgb(PAPER)))
    d = ImageDraw.Draw(sheet)
    x = 0
    for title, im in panels:
        sheet.paste(im, (x, 110 * S))
        f = font(40, "display")
        tw = d.textlength(title, font=f)
        d.text((x + (im.size[0] - tw) / 2, 16 * S), title, font=f, fill=INK)
        d.line([(x + 40 * S, 92 * S), (x + im.size[0] - 40 * S, 92 * S)], fill=GOLD_RULE, width=int(2 * S))
        x += im.size[0] + gap
    return finish(sheet, "04_paint_groups")


# =============================================================================
# 5. diffuser map
# =============================================================================
def img_diffuser_map():
    panels = []
    for title, direction in (("front and right side", (0.75, -1.0, 0.18)), ("rear and left side", (-0.75, 1.0, 0.18))):
        sc = Scene((700, 1000))
        for n in ("base", "nameplate", "band_cream", "band_red", "knob", "tower", "gallery", "lantern_glass",
                  "lantern_frame", "cap", "finial"):
            add_painted(sc, n, lit=True)
        for k in range(5):
            sc.part(f"window_diffuser_{k + 1}", "paint", lit=True)
        sc.shadow(0, 0, I["base_dia"] / 2, 0.4)
        sc.camera((0, 0, I["H"] * 0.5), direction, dist=2000, view_angle=9.4)
        wins = []
        rt = lambda z: (p.TOWER_BOTTOM_DIA / 2 + (p.TOWER_TOP_DIA - p.TOWER_BOTTOM_DIA) / 2
                        * (z - I["z_red_top"] + (I["z_red_top"] - I["base_h"] - LIFT - p.CREAM_BAND_H))
                        / (I["z_tower_top"] - I["base_h"] - LIFT - p.CREAM_BAND_H))
        dvec = np.array(direction[:2]) / np.linalg.norm(direction[:2])
        for k, (zw, ang) in enumerate(I["windows"]):
            z = zw + LIFT
            a = math.radians(ang)
            nrm = np.array([math.sin(a), -math.cos(a)])
            r = rt(z) + 1
            wins.append((k + 1, (nrm[0] * r, nrm[1] * r, z), float(nrm @ dvec)))
        pts = sc.project([w[1] for w in wins])
        img = sc.image()
        d = ImageDraw.Draw(img)
        for (n, _, facing), (x, y) in zip(wins, pts):
            if facing > 0.15:
                badge(d, (x + 44 * S, y - 40 * S), n, size=30, fill=tuple(int(c * 255) for c in hexrgb(ACCENT)),
                      ring=(255, 255, 255), ink=(255, 255, 255))
        panels.append(img)
    w = sum(i.size[0] for i in panels)
    sheet = Image.new("RGB", (w, panels[0].size[1]), tuple(int(c * 255) for c in hexrgb(PAPER)))
    x = 0
    for im in panels:
        sheet.paste(im, (x, 0))
        x += im.size[0]
    return finish(sheet, "05_diffuser_map")


# =============================================================================
# 6. assembly steps (painted; parts in place softened, the new part highlighted)
# =============================================================================
def img_step(name, done, new, view=(0.62, -1.0, 0.35), hover=None, extras=(), size=(900, 800),
             lights_on=False, flip=False, see_through=(), radial=None, fit_to=None, margin=1.15):
    """done: parts already in place (softened); new: parts added in this step (full
    colour, red outline). hover: the new parts float by this offset, with arrows
    back to their place. radial: per-part offsets for parts that go in sideways.
    see_through: parts drawn translucent so what's inside shows."""
    sc = Scene(size)
    for n in done:
        for sub in PAINTED_NAMES.get(n, (n,)):
            m = mesh(sub)
            st, coat = sc.style(sub, "paint", lit=lights_on, soft=True)
            if n in see_through:
                st = dict(st, opacity=0.28)
            sc.add(m, st, coat)
    off = np.array(hover or (0, 0, 0), float)
    new_bounds = []
    for n in new:
        o = np.array(radial[n]) if radial and n in radial else off
        for sub in PAINTED_NAMES.get(n, (n,)):
            m = sc.part(sub, "paint", offset=tuple(o), highlight=True, lit=lights_on)
            new_bounds.append((m.bounds, o))
    for kind, obj, hl in extras:
        if kind == "wire":
            sc.add(obj, dict(color=lin(COPPER), pbr=True, metallic=0.8, roughness=0.35), highlight=hl, outline=False)
        elif kind == "beads":
            sc.add(obj, dict(color=hexrgb(BEAD), lighting=False), outline=False)
        elif kind == "box":
            sc.add(obj, dict(color=lin(FROST), opacity=0.55, pbr=True, metallic=0.0, roughness=0.3), highlight=hl)
        elif kind == "cells":
            sc.add(obj, dict(color=lin("#C9A54A"), pbr=True, metallic=0.8, roughness=0.35))
        elif kind == "coins":
            sc.add(obj, dict(color=lin("#C8A560"), pbr=True, metallic=1.0, roughness=0.35), highlight=hl)
        elif kind == "tape":
            sc.add(obj, dict(color=lin("#E8DCC0"), opacity=0.7, pbr=True, roughness=0.5), outline=False)
    # arrows: from each lifted part back towards where it goes
    arrows = []
    if hover is not None or radial:
        b_all = [b for b, _ in new_bounds]
        lo = np.min([[b[0], b[2], b[4]] for b in b_all], axis=0)
        hi = np.max([[b[1], b[3], b[5]] for b in b_all], axis=0)
        o = new_bounds[0][1]
        if np.linalg.norm(o) > 1e-6 and not radial:
            u = o / np.linalg.norm(o)
            ctr = (lo + hi) / 2
            if abs(u[2]) > 0.9:                           # vertical: two arrows beside the part
                for sx in (-1, 1):
                    pnt = np.array([ctr[0] + sx * ((hi[0] - lo[0]) / 2 + 10), ctr[1] - (hi[1] - lo[1]) / 2 * 0.7,
                                    ctr[2]])
                    arrows.append((pnt + u * 6, pnt - o * 0.85))
            else:
                pnt = ctr + u * ((hi - lo) @ np.abs(u) / 2 + 12)
                arrows.append((pnt + u * 18, pnt - u * 4))
        for n, o2 in (radial or {}).items():
            b = [bb for bb, oo in new_bounds if np.allclose(oo, o2)]
            if not b:
                continue
            b = b[0]
            c = np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2])
            arrows.append((c, c - np.array(o2) * 0.9))
    if not flip:
        lo_all = np.min([[b[0], b[2], b[4]] for b in sc.bounds], axis=0)
        hi_all = np.max([[b[1], b[3], b[5]] for b in sc.bounds], axis=0)
        if lo_all[2] < 3:
            sc.shadow((lo_all[0] + hi_all[0]) / 2, (lo_all[1] + hi_all[1]) / 2,
                      min(max(hi_all[0] - lo_all[0], hi_all[1] - lo_all[1]) / 2, I["base_dia"] / 2 + 5), 0.35)
    sc.fit(view, up=(0, 0, 1) if not flip else (0, 1, 0), margin=margin, bounds=fit_to)
    arr = [sc.project([a, b]) for a, b in arrows]
    img = sc.image()
    d = ImageDraw.Draw(img)
    for a, b in arr:
        arrow(d, a, b)
    return finish(img, name)


def assembly_steps():
    rb = I["base_dia"] / 2
    base_grp = ["base", "nameplate"]
    body = base_grp + ["band_cream", "band_red", "knob"]
    diffs = [f"window_diffuser_{k}" for k in range(1, 6)]
    tower_grp = body + ["tower"] + diffs
    wire_feed, beads_feed = fairy_lights(coil=False, feed=True)
    box, cells = battery_box()
    radial = {}
    for k, (zw, ang) in enumerate(I["windows"]):
        a = math.radians(ang)
        radial[f"window_diffuser_{k + 1}"] = (-12 * math.sin(a), 12 * math.cos(a), 0)   # lifted inwards
    top_region = lambda z0: [(-60, 60, -60, 60, z0, I["H"] + 45)]
    files = []
    # --- part 1: the main body ---
    files.append(img_step("06_p1_1_diffusers", ["tower"], diffs, view=(0.35, -1.0, 0.3), radial=radial,
                          see_through=("tower",)))
    files.append(img_step("06_p1_2_nameplate", ["base"], ["nameplate"], view=(0.35, -1.0, 0.5), hover=(0, -24, 0)))
    files.append(img_step("06_p1_3_knob", ["band_red"], ["knob"], view=(0.45, -1.0, 0.4), hover=(0, -24, 0)))
    files.append(img_step("06_p1_4_fairy_lights", base_grp, [], view=(0.8, 1.0, 0.8),
                          extras=[("wire", tube(fairy_lights_path(), 0.9), True), ("beads", beads_feed, False),
                                  ("box", box, False), ("cells", cells, False)]))
    files.append(img_step("06_p1_5_band_cream", base_grp, ["band_cream"], hover=(0, 0, 24),
                          extras=[("wire", wire_feed, False), ("beads", beads_feed, False)],
                          fit_to=[(-rb - 5, rb + 5, -rb - 5, rb + 30, 0, 75)]))
    files.append(img_step("06_p1_6_band_red", base_grp + ["band_cream"], ["band_red", "knob"], hover=(0, 0, 28),
                          extras=[("wire", wire_feed, False), ("beads", beads_feed, False)],
                          fit_to=[(-rb - 5, rb + 5, -rb - 25, rb + 30, 0, 110)]))
    files.append(img_step("06_p1_7_tower", body, ["tower"] + diffs, hover=(0, 0, 36),
                          extras=[("wire", wire_feed, False), ("beads", beads_feed, False)]))
    files.append(img_cutaway("06_p1_8_coil_lights", tower_grp, focus="lights"))
    # --- part 2: the lantern and the base ---
    files.append(img_step("06_p2_1_gallery", tower_grp, ["gallery"], hover=(0, 0, 32),
                          fit_to=[(-50, 50, -50, 50, 120, 262)]))
    files.append(img_step("06_p2_2_glass", tower_grp + ["gallery"], ["lantern_glass"], hover=(0, 0, 34),
                          fit_to=[(-48, 48, -48, 48, 170, 290)]))
    files.append(img_step("06_p2_3_frame", tower_grp + ["gallery", "lantern_glass"], ["lantern_frame"],
                          hover=(0, 0, 40), fit_to=[(-48, 48, -48, 48, 170, 300)]))
    files.append(img_step("06_p2_4_finial", ["cap"], ["finial"], hover=(0, 0, 20), view=(0.5, -1.0, 0.35)))
    files.append(img_cap_twist("06_p2_5_twist_cap", assembled=True))
    under = (0.35, -0.55, -1.0)
    base_region = [(-rb - 4, rb + 4, -rb - 4, rb + 4, -30, 40)]
    files.append(img_step("06_p2_6_weight", [n for n in ORDER if n != "base_plate"], [], view=under, flip=True,
                          extras=[("coins", coins(), True), ("tape", tape(), False), ("wire", wire_feed, False)],
                          fit_to=base_region, margin=1.05))
    files.append(img_step("06_p2_7_base_plate", [n for n in ORDER if n != "base_plate"], ["base_plate"],
                          view=under, hover=(0, 0, -28), flip=True, fit_to=base_region, margin=1.05))
    files.append(img_step("06_p2_8_felt", ORDER, ["felt_pad"], view=under, hover=(0, 0, -22), flip=True,
                          fit_to=base_region, margin=1.05))
    return files


# =============================================================================
# 7. cut-away: fairy lights coiled in the tower, LED puck in the empty lantern,
#    coins in the base
# =============================================================================
def img_cutaway(name="07_cutaway", parts=None, focus="all"):
    sc = Scene((900, 1300) if focus == "all" else (900, 1000))
    parts = parts or ORDER
    clip = dict(normal=(1, 0, 0), origin=(0, 0, 0), invert=True)    # keep the x < 0 half
    for n in parts:
        for sub in PAINTED_NAMES.get(n, (n,)):
            m = mesh(sub)
            if not n.startswith(("knob", "nameplate", "finial")):
                m = m.clip(**clip)
            st, coat = sc.style(sub, "paint", lit=True)
            a = sc.add(m, st, coat)
            a.GetProperty().SetBackfaceCulling(False)
    wire, beads = fairy_lights(coil=True, feed=True)
    sc.add(wire, dict(color=lin(COPPER), pbr=True, metallic=0.8, roughness=0.35), outline=False,
           highlight=(focus == "lights"))
    sc.add(beads, dict(color=hexrgb(BEAD), lighting=False), outline=False)
    if focus == "all":
        body, lens = led_puck()
        sc.add(body, dict(color=lin("#F2F0EA"), pbr=True, roughness=0.4))
        sc.add(lens, dict(color=hexrgb("#FFE3A8"), lighting=False), outline=False)
        sc.add(coins(), dict(color=lin("#C8A560"), pbr=True, metallic=1.0, roughness=0.35))
        sc.add(tape(), dict(color=lin("#E8DCC0"), opacity=0.7, pbr=True, roughness=0.5), outline=False)
    sc.shadow(0, 0, I["base_dia"] / 2, 0.35)
    if focus == "all":
        sc.fit((1.0, -0.35, 0.22), margin=1.05, bounds=[(-60, 60, -60, 60, 0, I["H"])])
        call = sc.project([(0, 0, I["z_lantern"][0] + 14), (-20, -10, 150), (-30, 0, 24)])
    else:
        sc.fit((1.0, -0.35, 0.22), margin=1.05, bounds=[(-50, 50, -50, 50, 20, I["z_tower_top"] + 5)])
        call = []
    img = sc.image()
    if False:
        pass
    return finish(img, name)


# =============================================================================
# 8. the cap twist: lugs, slots and a clockwise arrow
# =============================================================================
def img_cap_twist(name="08_cap_twist", assembled=False, stage="paint"):
    """Three panels: the cap from below (lugs), the lantern top from above
    (slots), and the cap on with a clockwise arrow."""
    z_l1 = I["z_lantern"][1]
    r_lip = p.LANTERN_DIA / 2 - 3.0
    low = ["tower", "gallery", "lantern_glass", "lantern_frame"]
    panels = []
    # 1. the cap from below
    sc = Scene((620, 620))
    sc.part("cap", stage, highlight=False)
    sc.part("finial", stage)
    sc.camera((0, 0, z_l1 + 8), (0.45, -0.65, -1.0), dist=3000, view_angle=1.75, up=(0, 0, 1))
    lugs = [(r_lip * math.sin(math.radians(k * 90 + p.LOCK_TURN_DEG)) * 1.02,
             -r_lip * math.cos(math.radians(k * 90 + p.LOCK_TURN_DEG)) * 1.02, z_l1 - p.LIP_H - 3.0)
            for k in range(4)]
    pts = sc.project(lugs)
    img = sc.image()
    d = ImageDraw.Draw(img)
    for q in pts:
        r = 24 * S
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=GOLD_RULE, width=int(4 * S))
    panels.append(("the cap from below: four lugs", img))
    # 2. the lantern top from above
    sc = Scene((620, 620))
    for n in low:
        add_painted(sc, n, soft=assembled) if stage == "paint" else sc.part(n, stage)
    sc.camera((0, 0, z_l1 - 6), (0.3, -0.45, 1.0), dist=3000, view_angle=1.75)
    slots = [(r_lip * 1.04 * math.sin(math.radians(k * 90)), -r_lip * 1.04 * math.cos(math.radians(k * 90)), z_l1)
             for k in range(4)]
    pts = sc.project(slots)
    img = sc.image()
    d = ImageDraw.Draw(img)
    for q in pts:
        r = 24 * S
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=GOLD_RULE, width=int(4 * S))
    panels.append(("the lantern top: four slots in the lip", img))
    # 3. cap on, turn clockwise (seen from above) to the stop
    sc = Scene((620, 620))
    for n in low:
        add_painted(sc, n, soft=assembled, lit=True) if stage == "paint" else sc.part(n, stage)
    sc.part("cap", stage, highlight=True)
    sc.part("finial", stage)
    sc.camera((0, 0, z_l1 + 4), (0.55, -1.0, 0.7), dist=3000, view_angle=1.9)
    r_arc = p.CAP_RIM_DIA / 2 + 14
    zarc = z_l1 + 3
    arc = [(r_arc * math.sin(math.radians(a)), -r_arc * math.cos(math.radians(a)), zarc)
           for a in np.linspace(60, -60, 40)]                  # decreasing angle = clockwise from above
    pts = sc.project(arc)
    img = sc.image()
    d = ImageDraw.Draw(img)
    polyline_arrow(d, pts)
    panels.append(("drop the lugs in, turn clockwise to the stop", img))
    w = sum(im.size[0] for _, im in panels)
    h = panels[0][1].size[1]
    sheet = Image.new("RGB", (w, h), tuple(int(c * 255) for c in hexrgb(PAPER)))
    d = ImageDraw.Draw(sheet)
    x = 0
    for cap, im in panels:
        sheet.paste(im, (x, 0))
        x += im.size[0]
    return finish(sheet, name)


# =============================================================================
# extras: hero, lantern close-up, photo-set views, puck insertion
# =============================================================================
def img_hero():
    sc = Scene((900, 1300))
    for n in ORDER:
        add_painted(sc, n, lit=True)
    sc.shadow(0, 0, I["base_dia"] / 2, 0.45)
    sc.camera((0, 0, I["H"] * 0.5), (0.62, -1.0, 0.2), dist=3000, view_angle=6.4)
    return finish(sc.image(), "00_hero")


def img_views():
    out = []
    for nm, dirn, foc, ang in (("front", (0, -1, 0.08), I["H"] * 0.5, 6.6), ("side", (1, 0, 0.08), I["H"] * 0.5, 6.6),
                               ("three_quarter", (0.62, -1.0, 0.2), I["H"] * 0.5, 6.6),
                               ("lantern", (0.62, -1.0, 0.25), I["z_lantern"][1] - 6, 2.3)):
        sc = Scene((600, 800))
        for n in ORDER:
            add_painted(sc, n, lit=True)
        sc.shadow(0, 0, I["base_dia"] / 2, 0.45)
        sc.camera((0, 0, foc), dirn, dist=3000, view_angle=ang)
        out.append(finish(sc.image(), f"09_view_{nm}"))
    return out


def img_puck_insert():
    sc = Scene((900, 900))
    for n in ["tower", "gallery", "lantern_glass", "lantern_frame"]:
        add_painted(sc, n, soft=True)
    body, lens = led_puck(z=I["z_lantern"][1] + 30)
    sc.add(body, dict(color=lin("#F2F0EA"), pbr=True, roughness=0.4), highlight=True)
    sc.add(lens, dict(color=hexrgb("#FFE3A8"), lighting=False), outline=False)
    sc.camera((0, 0, I["z_lantern"][1] + 5), (0.55, -1.0, 0.55), dist=3000, view_angle=2.6)
    a = sc.project([(0, -30, I["z_lantern"][1] + 42), (0, -30, I["z_lantern"][1] + 6)])
    img = sc.image()
    d = ImageDraw.Draw(img)
    arrow(d, a[0], a[1])
    return finish(img, "10_puck_insert")


def img_drystack():
    """Step 1: dry-stacked in white resin, knob and nameplate aligned on the front."""
    sc = Scene((1100, 700))
    for n in ("base", "nameplate", "band_cream", "band_red", "knob", "tower"):
        sc.part(n, "resin")
    sc.shadow(0, 0, I["base_dia"] / 2, 0.35)
    sc.fit((0.25, -1.0, 0.28), margin=1.04, bounds=[(-58, 58, -58, 58, 0, 105)])
    return finish(sc.image(), "11_drystack_resin")


def img_nameplate():
    """Step 4: the black wash brushed over the letters, then wiped off the raised
    surfaces so it stays round the letters and FARO reads in gold."""
    out = []
    for nm, parts in (("12_nameplate_brushed", ("nameplate_plate", "nameplate_letters", "nameplate_brush")),
                      ("12_nameplate_wiped", ("nameplate_plate", "nameplate_letters", "nameplate_wash"))):
        sc = Scene((900, 420))
        for sub in parts:
            if sub == "nameplate_brush":                  # thinned black over the whole face, letters included
                for q in ("nameplate_letters", "nameplate_wash"):
                    m = mesh(q)
                    m.translate((0, -0.03, 0), inplace=True)
                    sc.add(m, dict(color=lin("#26211E"), pbr=True, metallic=0.0, roughness=0.45, opacity=0.88))
            else:
                sc.part(sub, "paint")
        lo, hi = bbox(mesh("nameplate_plate"))
        sc.fit((0.18, -1.0, 0.22), margin=1.12, bounds=[(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])])
        out.append(finish(sc.image(), nm))
    return out


def img_underside():
    """The finished underside: felt stuck on; and with the felt lifted, showing
    the plate glued into its rebate (no screws or magnets in the prototype)."""
    panels = []
    for felt_on in (True, False):
        sc = Scene((700, 620))
        for n in ("base", "nameplate", "band_cream", "band_red", "knob", "base_plate"):
            add_painted(sc, n)
        if felt_on:
            sc.part("felt_pad", "paint")
        else:
            m = mesh("felt_pad")
            m.rotate_x(-38, point=(0, bbox(m)[1][1], bbox(m)[0][2]), inplace=True)   # peeled back from one edge
            m.translate((0, 8, -14), inplace=True)
            st, coat = sc.style("felt_pad", "paint")
            sc.add(m, st, coat)
        sc.fit((0.35, -0.55, -1.0), up=(0, 1, 0), margin=1.03, bounds=[(-60, 60, -60, 90, -40, 12)])
        panels.append(sc.image())
    w = sum(i.size[0] for i in panels) + 30 * S
    sheet = Image.new("RGB", (w, panels[0].size[1]), tuple(int(c * 255) for c in hexrgb(PAPER)))
    sheet.paste(panels[0], (0, 0))
    sheet.paste(panels[1], (panels[0].size[0] + 30 * S, 0))
    return finish(sheet, "13_underside")


def img_rear():
    sc = Scene((600, 800))
    for n in ORDER:
        add_painted(sc, n, lit=True)
    sc.shadow(0, 0, I["base_dia"] / 2, 0.45)
    sc.camera((0, 0, I["H"] * 0.5), (0, 1, 0.08), dist=3000, view_angle=6.6)
    return finish(sc.image(), "09_view_rear")


JOBS = {
    "drystack": img_drystack,
    "nameplate": img_nameplate,
    "underside": img_underside,
    "rear": img_rear,
    "cap_resin": lambda: img_cap_twist("08_cap_twist_resin", stage="resin"),
    "hero": img_hero,
    "printed_parts": img_parts_as_arrived,
    "exploded_resin": lambda: img_exploded("resin"),
    "exploded_painted": lambda: img_exploded("paint"),
    "priming": img_priming,
    "paint_groups": img_paint_groups,
    "diffuser_map": img_diffuser_map,
    "assembly": assembly_steps,
    "cutaway": img_cutaway,
    "cap_twist": img_cap_twist,
    "views": img_views,
    "puck": img_puck_insert,
}


def contact_sheet(path=None):
    files = sorted(OUT.glob("*.png"))
    thumbs = []
    for f in files:
        im = Image.open(f).convert("RGB")
        im.thumbnail((340, 300))
        thumbs.append((f.stem, im))
    cols = 6
    cw, ch = 360, 340
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * cw, rows * ch), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(str(FONTS / "EBGaramond-Regular.ttf"), 15)
    for i, (n, im) in enumerate(thumbs):
        x, y = (i % cols) * cw, (i // cols) * ch
        sheet.paste(im, (x + (cw - im.size[0]) // 2, y + 8))
        d.text((x + 10, y + ch - 28), n, font=f, fill=(40, 40, 40))
    path = path or OUT.parent / "contact_sheet.png"
    sheet.save(path)
    return path


if __name__ == "__main__":
    want = sys.argv[1:]
    for key, fn in JOBS.items():
        if want and not any(w in key for w in want):
            continue
        print(key)
        fn()
    print(contact_sheet())
