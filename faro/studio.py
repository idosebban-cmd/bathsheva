"""
Faro renders, reusing Atelier's studio (environment map, lights, backdrop,
exact-normal meshing) from the top-level render.py. Only the materials and the
contact shadow are Faro's own.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pyvista as pv

sys.path.append(str(Path(__file__).resolve().parent.parent))
import render as atelier  # noqa: E402  (Atelier's render.py)

VIEWS = {"front": (0.0, -1.0, 0.0), "side": (1.0, 0.0, 0.0), "rear": (0.0, 1.0, 0.0),
         "three_quarter": (0.62, -0.78, 0.2)}

BRASS = ("nameplate", "knob", "gallery", "lantern_frame", "finial")
RED = ("band_red", "cap")
CREAM = ("band_cream", "tower")
GLOW = ("lantern_glass", "window_diffuser")


def _material(name, p):
    lin = atelier.hex_linear
    if name.startswith(GLOW):
        return dict(color=atelier.hex_rgb(p.GLOW_HEX), lighting=False), False
    if name in BRASS:
        return dict(color=lin(p.BRASS_HEX), pbr=True, metallic=1.0, roughness=p.BRASS_ROUGHNESS), False
    if name in RED:
        return dict(color=lin(p.RED_HEX), pbr=True, metallic=0.0, roughness=p.LACQUER_ROUGHNESS), True
    if name in CREAM:
        return dict(color=lin(p.CREAM_HEX), pbr=True, metallic=0.0, roughness=p.LACQUER_ROUGHNESS), True
    if name == "felt_pad":
        return dict(color=lin("#4A4642"), pbr=True, metallic=0.0, roughness=1.0), False
    if name == "base_plate":
        return dict(color=lin("#4A4541"), pbr=True, metallic=0.0, roughness=0.6), False
    if name == "base":
        return dict(color=lin(p.WALNUT_HEX), pbr=True, metallic=0.0, roughness=p.WALNUT_ROUGHNESS), False
    return dict(color=(0.5, 0.5, 0.5)), False


def _shadow(pl, m):
    grid = pv.Plane(center=(0, 0, 0.05), direction=(0, 0, 1), i_size=500, j_size=500,
                    i_resolution=200, j_resolution=200).triangulate()
    r = np.linalg.norm(grid.points[:, :2], axis=1)
    rb = m.info["base_dia"] / 2
    a = 0.55 * np.exp(-(np.maximum(r - rb * 0.8, 0) / 9.0) ** 2) * (r < rb * 1.6)
    rgba = np.zeros((len(r), 4))
    rgba[:, :3] = np.array([0.25, 0.20, 0.16]) * 255
    rgba[:, 3] = np.clip(a, 0, 1) * 255
    grid["rgba"] = rgba.astype(np.uint8)
    pl.add_mesh(grid, scalars="rgba", rgba=True, lighting=False, show_scalar_bar=False)


def plotter(m, p, size, shadow=True, hide=(), extra=()):
    pl = pv.Plotter(off_screen=True, window_size=list(size), lighting="none")
    pl.set_background(atelier.BACKDROP, top=atelier.BACKDROP_TOP)
    if not atelier.FAST:
        pl.enable_anti_aliasing("ssaa")
    if atelier._ENV is None:
        atelier._ENV = atelier._studio_environment()
    pl.set_environment_texture(atelier._ENV)
    pl.renderer.GetEnvMapPrefiltered().SetPrefilterMaxSamples(64 if atelier.FAST else 1024)
    pl.renderer.SetEnvironmentUp(0, 0, 1)
    pl.renderer.SetEnvironmentRight(1, 0, 0)
    for pos, k in (((-500, -700, 700), atelier.LIGHT_KEY), ((700, -350, 250), atelier.LIGHT_FILL),
                   ((150, 800, 600), atelier.LIGHT_RIM)):
        pl.add_light(pv.Light(position=pos, focal_point=(0, 0, 150), intensity=k * p.LIGHT_GAIN))
    for name, shape in m.parts.items():
        if name in hide:
            continue
        style, coat = _material(name, p)
        actor = pl.add_mesh(atelier._to_mesh(shape), smooth_shading=True, **style)
        if coat:
            prop = actor.GetProperty()
            prop.SetCoatStrength(p.LACQUER_CLEARCOAT)
            prop.SetCoatRoughness(0.05)
            prop.SetCoatColor(1.0, 1.0, 1.0)
            prop.SetCoatIOR(1.5)
    if "usb_receptacle" in m.envelopes:           # dark metal seen through the port
        pl.add_mesh(atelier._to_mesh(m.envelopes["usb_receptacle"], 0.05), color=(0.08, 0.08, 0.09),
                    pbr=True, metallic=0.8, roughness=0.4)
    finish = {"screws": ("#8E9095", 0.35), "magnets": ("#E2E2E4", 0.15)}   # steel / bright nickel
    for key in extra:                               # e.g. screws and magnets
        if m.envelopes.get(key) is not None:
            col, rough = finish.get(key, ("#9A9CA0", 0.35))
            pl.add_mesh(atelier._to_mesh(m.envelopes[key], 0.02), color=atelier.hex_linear(col),
                        pbr=True, metallic=1.0, roughness=rough)
    if shadow:
        _shadow(pl, m)
    return pl


def render_underside(m, p, path, size=(1100, 900)):
    """Two views up at the base: as sold (felt on) and with the felt lifted off
    (the plate, its 4 screws and 4 magnets)."""
    from PIL import Image, ImageDraw
    imgs = []
    for hide, extra in (((), ()), (("felt_pad",), ("screws", "magnets"))):
        pl = plotter(m, p, size, shadow=False, hide=hide, extra=extra)
        d = np.array([0.30, -0.45, -1.0])
        d /= np.linalg.norm(d)
        focal = np.array([0.0, 0.0, 12.0])
        pl.camera.position = tuple(focal + d * 330)
        pl.camera.focal_point = tuple(focal)
        pl.camera.up = (0, 1, 0)
        pl.camera.view_angle = 24
        pl.reset_camera_clipping_range()
        imgs.append(Image.fromarray(pl.screenshot(return_img=True)))
        pl.close()
    sheet = Image.new("RGB", (size[0] * 2 + 20, size[1]), (255, 255, 255))
    for i, im in enumerate(imgs):
        sheet.paste(im, (i * (size[0] + 20), 0))
    dr = ImageDraw.Draw(sheet)
    dr.text((20, 20), "underside, as sold (felt pad on)", fill=(40, 40, 40))
    dr.text((size[0] + 40, 20), ("felt pad lifted off: 4 screws (hex socket) hold the plate; 4 magnets (bright) "
                                 "hold the felt") if p.BASE_FIXING == "screwed" else
            "felt lifted off: the plain plate, glued into its rebate",
            fill=(40, 40, 40))
    sheet.save(path)
    return path


def render_views(m, p, out_dir: Path, views=("front", "side"), prefix="faro"):
    out_dir.mkdir(parents=True, exist_ok=True)
    H = m.info["H"]
    files = []
    for name in views:
        d = np.array(VIEWS[name], dtype=float)
        d /= np.linalg.norm(d)
        pl = plotter(m, p, p.RENDER_SIZE)
        focal = np.array([0, 0, H * 0.48])
        pl.camera.position = tuple(focal + d * H * 3.4)
        pl.camera.focal_point = tuple(focal)
        pl.camera.up = (0, 0, 1)
        pl.camera.view_angle = 22
        pl.reset_camera_clipping_range()
        f = out_dir / f"{prefix}_{name}.png"
        pl.screenshot(str(f))
        pl.close()
        files.append(f)
    return files
