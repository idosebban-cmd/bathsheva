"""
Shared studio-render Scene helper for the Bathsheva London prototype build
manuals (Faro, Atelier, ...). Wraps the pyvista/PBR studio (environment map,
three-point light rig) that render.py -- the top-level Atelier renderer --
builds, adding: vertex-clean silhouette outlines so only true part edges
draw (not the render mesh's per-face vertex splits); part staging (add a
mesh in a named style, with an optional clear coat and silhouette outline);
an orthographic "fit to bounds" camera; and world -> image point projection,
for the leader-line labels drawn on top of a render afterwards.

Material and build-stage styling -- which colour a part renders in at the
resin / primer / painted stage, whether it gets a clear coat -- is specific
to each manual's own part list and finishes, so it isn't baked in here:
subclass Scene and implement `style(name, stage, lit, soft)`, returning
(pyvista style kwargs, clearcoat: bool). Extracted from
faro/manual/illustrate.py, whose own Scene now subclasses this one with
Faro's `style()`; its many drawing functions (img_hero, assembly_steps,
...) are unchanged.
"""
from __future__ import annotations

import numpy as np
import pyvista as pv
import vtk
from PIL import Image


class Scene:
    """A studio plotter on the manual's paper colour, with outline helpers
    and world -> image projection for labels.

    `atelier` is the render.py module (or a re-export of it, as in
    faro/studio.py) supplying the shared environment map, light rig and mesh
    helpers. `mesh_fn(name) -> pyvista mesh` is the manual's own part
    lookup. `p` is the manual's params module, read here only for
    LIGHT_GAIN and LACQUER_CLEARCOAT.
    """

    def __init__(self, atelier, mesh_fn, p, size=(1400, 1000), lights=1.0, scale=2,
                 paper="#F8F4EC", outline="#4A3E34", accent="#9B1B14"):
        self.atelier = atelier
        self.mesh_fn = mesh_fn
        self.p = p
        self.S = scale
        self.outline = outline
        self.accent = accent
        self.size = (size[0] * scale, size[1] * scale)
        pl = pv.Plotter(off_screen=True, window_size=list(self.size), lighting="none")
        pl.set_background(paper)
        pl.enable_anti_aliasing("ssaa")
        if atelier._ENV is None:
            atelier._ENV = atelier._studio_environment()
        pl.set_environment_texture(atelier._ENV)
        pl.renderer.GetEnvMapPrefiltered().SetPrefilterMaxSamples(256)
        pl.renderer.SetEnvironmentUp(0, 0, 1)
        pl.renderer.SetEnvironmentRight(1, 0, 0)
        light_gain = getattr(p, "LIGHT_GAIN", 1.0)
        for pos, k in (((-500, -700, 700), atelier.LIGHT_KEY), ((700, -350, 250), atelier.LIGHT_FILL),
                       ((150, 800, 600), atelier.LIGHT_RIM)):
            pl.add_light(pv.Light(position=pos, focal_point=(0, 0, 150), intensity=k * light_gain * lights))
        self.pl = pl
        self.shadows = []
        self.bounds = []

    def style(self, name, stage, lit=False, soft=False):
        """Subclasses implement this for their own part list and finishes."""
        raise NotImplementedError

    def add(self, m, style, coat=False, outline=True, highlight=False, smooth=True):
        kw = dict(style)
        self.bounds.append(m.bounds)
        a = self.pl.add_mesh(m, smooth_shading=smooth, **kw)
        if highlight or outline:
            # outlines from a vertex-merged copy, so only true silhouettes are drawn
            # (the render mesh has separate vertices per face, for crisp normals)
            clean = pv.PolyData(m.points, m.faces).clean(tolerance=1e-4)
            self.pl.add_silhouette(clean, color=self.accent if highlight else self.outline,
                                   line_width=(3.0 if highlight else 1.1) * self.S)
        if coat:
            prop = a.GetProperty()
            clearcoat = getattr(self.p, "LACQUER_CLEARCOAT", getattr(self.p, "BODY_CLEARCOAT", 1.0))
            prop.SetCoatStrength(clearcoat)
            prop.SetCoatRoughness(0.05)
            prop.SetCoatColor(1.0, 1.0, 1.0)
            prop.SetCoatIOR(1.5)
        return a

    def part(self, name, stage="paint", offset=(0, 0, 0), lit=False, soft=False, highlight=False,
             outline=True, transform=None):
        m = self.mesh_fn(name)
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
