"""
Preview renders (PNG) of the assembly using PyVista/VTK.

Body parts are drawn in glossy deep red, everything else in gold.
Runs off-screen, so no window pops up.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pyvista as pv

# Camera directions: where the camera sits, looking at the model.
# Front of the product faces -Y.
VIEWS = {
    "front": (0.0, -1.0, 0.0),
    "side": (1.0, 0.0, 0.0),
    "rear": (0.0, 1.0, 0.0),
    "three_quarter": (0.62, -0.78, 0.18),
}


def _to_mesh(shape, tol=0.08):
    verts, tris = shape.tessellate(tol, math.radians(8))
    v = np.array([[p.X, p.Y, p.Z] for p in verts])
    f = np.hstack([np.full((len(tris), 1), 3), np.array(tris)]).ravel()
    mesh = pv.PolyData(v, f)
    return mesh.compute_normals(split_vertices=True, feature_angle=35, auto_orient_normals=True)


def _is_red(name):
    return name.startswith("body")


def _plotter(model, p, size, section=False):
    pl = pv.Plotter(off_screen=True, window_size=list(size), lighting="none")
    pl.set_background((0.93, 0.90, 0.85), top=(0.99, 0.97, 0.94))
    pl.enable_anti_aliasing("ssaa")
    # soft studio lighting: key, fill, rim
    pl.add_light(pv.Light(position=(-400, -600, 600), focal_point=(0, 0, 120), intensity=0.9))
    pl.add_light(pv.Light(position=(600, -300, 200), focal_point=(0, 0, 120), intensity=0.45))
    pl.add_light(pv.Light(position=(100, 700, 500), focal_point=(0, 0, 120), intensity=0.55))
    pl.add_light(pv.Light(light_type="headlight", intensity=0.25))

    red = dict(color=p.COLOUR_BODY, ambient=0.18, diffuse=0.75, specular=0.9, specular_power=70)
    gold = dict(color=p.COLOUR_GOLD, ambient=0.22, diffuse=0.7, specular=1.0,
                specular_power=28)
    clip = dict(normal=(1, 0, 0), origin=(0, 0, 0), invert=True) if section else None
    for name, shape in model.parts.items():
        mesh = _to_mesh(shape)
        if section:
            mesh = mesh.clip(**clip)
        pl.add_mesh(mesh, smooth_shading=True, **(red if _is_red(name) else gold))
    if section:
        colours = {"driver": (0.15, 0.15, 0.17), "battery": (0.2, 0.45, 0.75)}
        for name, env in model.envelopes.items():
            if name in colours:
                pl.add_mesh(_to_mesh(env, 0.3).clip(**clip), color=colours[name], opacity=0.9)

    # ground plane
    ground = pv.Disc(center=(0, 0, -0.2), inner=0, outer=4000, normal=(0, 0, 1), c_res=180)
    pl.add_mesh(ground, color=(0.86, 0.83, 0.78), ambient=0.4, diffuse=0.6, specular=0.1)
    return pl


def render_views(model, p, out_dir: Path, views=None, prefix="render"):
    out_dir.mkdir(parents=True, exist_ok=True)
    H = model.info["H"]
    focal = (0, 0, H * 0.47)
    dist = H * 3.2
    written = []
    for name in views or VIEWS:
        d = np.array(VIEWS[name])
        d = d / np.linalg.norm(d)
        pl = _plotter(model, p, p.RENDER_SIZE)
        pl.camera.position = tuple(np.array(focal) + d * dist + np.array([0, 0, H * 0.12]))
        pl.camera.focal_point = focal
        pl.camera.up = (0, 0, 1)
        pl.camera.view_angle = 24
        pl.reset_camera_clipping_range()
        path = out_dir / f"{prefix}_{name}.png"
        pl.screenshot(str(path))
        pl.close()
        written.append(path)

    # cut-away through the middle, seen from the side, to show internals
    pl = _plotter(model, p, p.RENDER_SIZE, section=True)
    pl.camera.position = (dist, 0, focal[2] + H * 0.05)
    pl.camera.focal_point = focal
    pl.camera.up = (0, 0, 1)
    pl.camera.view_angle = 24
    pl.reset_camera_clipping_range()
    path = out_dir / f"{prefix}_section.png"
    pl.screenshot(str(path))
    pl.close()
    written.append(path)

    # one overview image with all views side by side
    from PIL import Image
    ims = [Image.open(f) for f in written]
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * len(ims) // 2, h // 2))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((w // 2, h // 2)), (i * w // 2, 0))
    path = out_dir / f"{prefix}_overview.png"
    sheet.save(path)
    written.append(path)
    return written
