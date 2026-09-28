"""
Minimum wall thickness measured on the exact CAD solids (not on STL meshes).

    from solid_check import min_wall
    r = min_wall(solid)        # dict(min=..., p1=..., at=(x, y, z), rays=...)

From points spread over every face (at least MIN_PER_FACE per face, more on big
faces), a ray goes straight inwards along the true surface normal and is
intersected with the exact B-rep. The distance to where it leaves the material
is the local wall thickness. Only exits through a roughly opposite face count
(the exit face points back within 60 deg), so ordinary 90 deg edges and corners
aren't mistaken for thin walls; genuine knife edges still are.
"""
from __future__ import annotations

import numpy as np
from OCP.BRepGProp import BRepGProp_Face
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt, gp_Vec
from OCP.TopoDS import TopoDS

MIN_PER_FACE = 3


def _normal(face_wrapped, u, v):
    """Outward normal at (u, v), taking the face's orientation into account."""
    prop = BRepGProp_Face(face_wrapped)
    p, n = gp_Pnt(), gp_Vec()
    prop.Normal(u, v, p, n)
    m = n.Magnitude()
    return None if m < 1e-12 else np.array([n.X(), n.Y(), n.Z()]) / m


def min_wall(shape, samples=6000, seed=1, max_depth=80.0, tol=1e-4):
    rng = np.random.default_rng(seed)
    faces = shape.faces()
    areas = np.array([f.area for f in faces])
    n_per = np.maximum(MIN_PER_FACE, np.round(samples * areas / areas.sum()).astype(int))
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(shape.wrapped, tol)
    out = []
    for f, k in zip(faces, n_per):
        fw = f.wrapped
        u0, u1, v0, v1 = f._uv_bounds() if hasattr(f, "_uv_bounds") else _uv_bounds(fw)
        got, tries = 0, 0
        while got < k and tries < 20 * k:
            tries += 1
            u, v = u0 + (u1 - u0) * rng.random(), v0 + (v1 - v0) * rng.random()
            if not _inside(fw, u, v):
                continue
            n = _normal(fw, u, v)
            if n is None:
                continue
            p = BRepGProp_Face(fw)
            pt, nv = gp_Pnt(), gp_Vec()
            p.Normal(u, v, pt, nv)
            p0 = np.array([pt.X(), pt.Y(), pt.Z()])
            got += 1
            start = p0 - n * 1e-3
            inter.Perform(gp_Lin(gp_Pnt(*start), gp_Dir(*(-n))), 0.0, max_depth)
            if not inter.IsDone() or inter.NbPnt() == 0:
                continue
            hits = sorted((inter.WParameter(i), i) for i in range(1, inter.NbPnt() + 1))
            for w, i in hits:
                if w < 2e-3:
                    continue
                hf = inter.Face(i)
                hn = _normal(hf, inter.UParameter(i), inter.VParameter(i))
                if hn is not None and np.dot(hn, n) < -0.5:
                    out.append((w + 1e-3, p0))
                break
    if not out:
        return None
    d = np.array([o[0] for o in out])
    i = int(np.argmin(d))
    return dict(min=float(d[i]), p1=float(np.percentile(d, 1)), at=tuple(np.round(out[i][1], 1)), rays=len(d))


def _uv_bounds(fw):
    from OCP.BRepTools import BRepTools
    return BRepTools.UVBounds_s(fw)


def _inside(fw, u, v):
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.gp import gp_Pnt2d
    from OCP.TopAbs import TopAbs_IN
    return BRepClass_FaceClassifier(fw, gp_Pnt2d(u, v), 1e-6).State() == TopAbs_IN
