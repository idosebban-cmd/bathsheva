"""
Preview renders (PNG) of the assembly using PyVista/VTK, with physically based
materials:

* body  - lacquer: coloured base with a glossy clear coat on top
* gold  - metal: fully metallic, medium roughness (soft, brushed reflections)
* LED   - an unlit warm white dot with a soft glow

Metals only look like metal when they have something to reflect, so the scene
is lit by a procedurally generated "photo studio" environment (soft boxes and
strip lights) plus a few direct lights. Everything runs off-screen.
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


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def hex_linear(h):
    """VTK's PBR shader takes linear colour and gamma-encodes its output, so an
    sRGB hex code must be linearised first or it renders washed out."""
    return tuple(c ** 2.2 for c in hex_rgb(h))


_MESH_CACHE = {}


def _to_mesh(shape, tol=0.03, angle_deg=4.0):
    """Triangulate a CAD solid for rendering, with exact surface normals.

    Normals come from the CAD surface itself (via OpenCascade), not averaged
    from triangles; averaged normals make curved metal look hammered.
    Cached, so each part is only triangulated once per run."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepLib import BRepLib_ToolTriangulatedShape
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_REVERSED
    from OCP.TopLoc import TopLoc_Location

    key = (id(shape), tol)
    if key in _MESH_CACHE:
        return _MESH_CACHE[key]
    BRepMesh_IncrementalMesh(shape.wrapped, tol, False, math.radians(angle_deg), True)
    pts, nrm, tris, off = [], [], [], 0
    for face in shape.faces():
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face.wrapped, loc)
        if tri is None:
            continue
        BRepLib_ToolTriangulatedShape.ComputeNormals_s(face.wrapped, tri)
        trsf = loc.Transformation()
        rev = face.wrapped.Orientation() == TopAbs_REVERSED
        n_nodes = tri.NbNodes()
        for i in range(1, n_nodes + 1):
            q = tri.Node(i).Transformed(trsf)
            pts.append((q.X(), q.Y(), q.Z()))
            d = tri.Normal(i).Transformed(trsf)
            s = -1.0 if rev else 1.0
            nrm.append((s * d.X(), s * d.Y(), s * d.Z()))
        for i in range(1, tri.NbTriangles() + 1):
            a, b, c = tri.Triangle(i).Get()
            if rev:
                b, c = c, b
            tris.append((3, a - 1 + off, b - 1 + off, c - 1 + off))
        off += n_nodes
    mesh = pv.PolyData(np.array(pts), np.array(tris).ravel())
    mesh.point_data["Normals"] = np.array(nrm)
    _MESH_CACHE[key] = mesh
    return mesh


def _studio_environment(size=(512, 1024)):
    """An equirectangular 'photo studio': warm walls, a big soft box up front-left,
    strip lights either side and a dim floor. Brightness is 0..1."""
    h, w = size
    lat = np.linspace(math.pi / 2, -math.pi / 2, h)[:, None]   # +90 (up) .. -90 (down)
    lon = np.linspace(-math.pi, math.pi, w)[None, :]
    wall = 0.15 + 0.15 * np.clip(np.sin(lat), -0.5, 1)          # dark studio, brighter overhead
    img = np.repeat(wall[..., None], 3, axis=2) * np.array([1.0, 0.95, 0.88])
    img = np.broadcast_to(img, (h, w, 3)).copy()

    def box(lat0, lat1, lon0, lon1, level, soft=0.08):
        la = np.clip(np.minimum(lat - math.radians(lat0), math.radians(lat1) - lat) / soft, 0, 1)
        dl = (lon - math.radians(lon0) + math.pi) % (2 * math.pi) - math.pi
        dl1 = (math.radians(lon1) - lon + math.pi) % (2 * math.pi) - math.pi
        lo = np.clip(np.minimum(dl, dl1) / soft, 0, 1)
        return (la * lo)[..., None] * level

    img += box(20, 65, -150, -95, 1.0)      # key soft box
    img += box(-5, 55, 20, 32, 0.9)         # right strip
    img += box(-5, 55, -35, -25, 0.6)       # left strip
    img += box(10, 50, 120, 175, 0.55)      # back fill
    img += box(70, 90, -180, 180, 0.25)     # ceiling bounce
    img[lat[:, 0] < -0.05] *= 0.55          # floor is darker
    tex = pv.Texture((np.clip(img, 0, 1) * 255).astype(np.uint8))
    tex.mipmap = True
    tex.interpolate = True
    return tex


_ENV = None
LIGHT_KEY, LIGHT_FILL, LIGHT_RIM = 1.9, 0.8, 0.9
BACKDROP = (0.90, 0.875, 0.835)      # seamless studio backdrop (no visible horizon)
BACKDROP_TOP = (0.975, 0.96, 0.935)


def _add_ground_shadow(pl, model):
    """A soft contact shadow on an invisible floor: dark under the fin tips and
    foot, fading to fully transparent, so the backdrop stays seamless."""
    grid = pv.Plane(center=(0, 0, 0.05), direction=(0, 0, 1), i_size=500, j_size=500,
                    i_resolution=250, j_resolution=250).triangulate()
    xy = grid.points[:, :2]
    r = np.linalg.norm(xy, axis=1)
    a = 0.22 * np.exp(-(r / 70.0) ** 2)                       # ambient occlusion under the body
    for tx, ty in model.info["fin_tips"]:
        d = np.linalg.norm(xy - np.array([tx, ty]), axis=1)
        a = np.maximum(a, 0.55 * np.exp(-(d / 7.0) ** 2))      # fin tip contact
    a = np.maximum(a, 0.35 * np.exp(-(r / (model.info["foot_dia"] * 0.55)) ** 2))
    rgba = np.zeros((len(r), 4))
    rgba[:, :3] = np.array([0.25, 0.20, 0.16]) * 255
    rgba[:, 3] = np.clip(a, 0, 1) * 255
    grid["rgba"] = rgba.astype(np.uint8)
    pl.add_mesh(grid, scalars="rgba", rgba=True, lighting=False, show_scalar_bar=False)


def _plotter(model, p, size, section=False):
    global _ENV
    pl = pv.Plotter(off_screen=True, window_size=list(size), lighting="none")
    pl.set_background(BACKDROP, top=BACKDROP_TOP)
    pl.enable_anti_aliasing("ssaa")
    if _ENV is None:
        _ENV = _studio_environment()
    pl.set_environment_texture(_ENV)
    pre = pl.renderer.GetEnvMapPrefiltered()   # smoother blurred reflections on rough metal
    pre.SetPrefilterMaxSamples(1024)
    pl.renderer.SetEnvironmentUp(0, 0, 1)
    pl.renderer.SetEnvironmentRight(1, 0, 0)
    # direct lights for crisp highlights: key, fill, rim
    pl.add_light(pv.Light(position=(-500, -700, 700), focal_point=(0, 0, 120), intensity=LIGHT_KEY))
    pl.add_light(pv.Light(position=(700, -350, 250), focal_point=(0, 0, 120), intensity=LIGHT_FILL))
    pl.add_light(pv.Light(position=(150, 800, 600), focal_point=(0, 0, 120), intensity=LIGHT_RIM))

    red = dict(color=hex_linear(p.RED_HEX), pbr=True, metallic=0.0, roughness=p.BODY_ROUGHNESS)
    gold = dict(color=hex_linear(p.GOLD_HEX), pbr=True, metallic=p.GOLD_METALLIC,
                roughness=p.GOLD_ROUGHNESS)
    clip = dict(normal=(1, 0, 0), origin=(0, 0, 0), invert=True) if section else None
    steel = dict(color=hex_linear("#8C8F94"), pbr=True, metallic=1.0, roughness=0.45)
    internal = getattr(model, "internal", set())
    for name, shape in model.parts.items():
        if name in internal and not section:
            continue                                   # hidden inside anyway
        mesh = _to_mesh(shape)
        if section:
            mesh = mesh.clip(**clip)
        is_red = name.startswith("body")
        style = red if is_red else steel if name in internal else gold
        actor = pl.add_mesh(mesh, smooth_shading=True, **style)
        if is_red and p.BODY_CLEARCOAT > 0:
            prop = actor.GetProperty()
            prop.SetCoatStrength(p.BODY_CLEARCOAT)
            prop.SetCoatRoughness(p.BODY_CLEARCOAT_ROUGHNESS)
            prop.SetCoatColor(1.0, 1.0, 1.0)
            prop.SetCoatIOR(1.5)

    if not section:
        _add_led(pl, model, p)
        # passive radiator diaphragm, seen through the rear opening
        pl.add_mesh(_to_mesh(model.envelopes["passive_radiator"], 0.2), color=(0.06, 0.06, 0.07),
                    pbr=True, metallic=0.0, roughness=0.6)
    else:
        colours = {"driver": (0.15, 0.15, 0.17), "battery": (0.2, 0.45, 0.75),
                   "passive_radiator": (0.35, 0.2, 0.45)}
        for name, env in model.envelopes.items():
            if name in colours:
                pl.add_mesh(_to_mesh(env, 0.3).clip(**clip), color=colours[name], opacity=0.9)

    if not section:
        _add_ground_shadow(pl, model)
    return pl


def _add_led(pl, model, p):
    """Glowing LED: an unlit lens plus a soft halo just in front of the surface."""
    led = model.envelopes.get("led")
    if led is None:
        return
    col = hex_rgb(p.LED_HEX)
    pl.add_mesh(_to_mesh(led, 0.02), color=col, lighting=False)
    z = model.info["z_led"]
    y = -model._r_out(z) - 0.25
    halo = pv.Disc(center=(0, y, z), inner=0, outer=p.LED_DIA * 1.6, normal=(0, -1, 0),
                   r_res=24, c_res=48)
    r = np.linalg.norm(halo.points[:, [0, 2]] - np.array([0, z]), axis=1)
    glow = np.exp(-(r / (p.LED_DIA * 0.55)) ** 2) * 0.85
    rgba = np.column_stack([np.tile(np.array(col) * 255, (len(r), 1)), glow * 255])
    halo["rgba"] = rgba.astype(np.uint8)
    pl.add_mesh(halo, scalars="rgba", rgba=True, lighting=False, show_scalar_bar=False)


def render_views(model, p, out_dir: Path, views=None, prefix="render", section=True):
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

    if section:
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

    written.append(contact_sheet(written, out_dir / f"{prefix}_overview.png"))
    trio = [out_dir / f"{prefix}_{v}.png" for v in ("front", "side", "three_quarter")]
    if all(t in written for t in trio):
        written.append(contact_sheet(trio, out_dir / f"{prefix}_front_side_34.png", scale=0.6))
    return written


def contact_sheet(paths, out_path, scale=0.5):
    """Place several renders side by side in one image."""
    from PIL import Image
    ims = [Image.open(f) for f in paths]
    w, h = ims[0].size
    tw, th = int(w * scale), int(h * scale)
    sheet = Image.new("RGB", (tw * len(ims), th))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (i * tw, 0))
    sheet.save(out_path)
    return out_path
