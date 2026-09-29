"""
Finds exact attachment points for grille, bezel, knob and fins by reading
witness marks (recess opening, mounting pilot holes) already modelled into
body.stl itself, and recomputes the fitted_by_eye transforms in
scripts/assembly.yaml from them.

This supersedes most of what scripts/photo_fit.py derived from the
reference photo: photo_fit.py was written first, while scripts/lineart.py's
occlusion test had its ray direction backwards (it cast away from the
camera instead of toward it -- see lineart.py's visible_mask docstring/fix).
That bug silently hid real geometry, including these witness marks, so at
the time photo-matching looked like the only option. Once the bug was
fixed, body.stl turned out to already carry the grille/bezel opening, its 4
mounting pilot holes, the knob's mounting hole, and the fins' mounting
pilot holes -- all far more precise than anything read off a photo.

What's still photo-derived (no corresponding witness mark exists):
  - the fin TIP (how far out and how low the fin extends -- the mounting
    holes fix only the root/attachment end)
  - the LED (no matching small hole was found near it; see assembly.yaml's
    note on the led marker)

Method for each hole: front-facing (Y>20) crease/silhouette edges are
extracted the same way scripts/lineart.py does for rendering, their
midpoints are clustered with a simple union-find over a KD-tree (points
within 2mm are the same cluster -- each real hole's front rim, back rim,
and any nearby duplicate detection all merge into one cluster), and each
cluster with enough points is fit as a circle (centroid + mean radial
distance in the local X-Z plane).
"""

import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lineart import load_part, feature_edges  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def find_holes(body, y_min=20.0, cluster_radius=2.0, min_points=6):
    view_vector = np.array([0, -1, 0])
    edges = feature_edges(body, -view_vector)
    front_edges = [(p0, p1) for p0, p1, k in edges if p0[1] > y_min and p1[1] > y_min]

    pts = []
    for p0, p1 in front_edges:
        pts.append(p0)
        pts.append(p1)
    pts = np.array(pts)

    tree = cKDTree(pts)
    pairs = tree.query_pairs(r=cluster_radius)
    parent = list(range(len(pts)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in pairs:
        union(a, b)

    clusters = {}
    for i in range(len(pts)):
        clusters.setdefault(find(i), []).append(i)

    holes = []
    for idxs in clusters.values():
        if len(idxs) < min_points:
            continue
        cpts = pts[idxs]
        center = cpts.mean(axis=0)
        d = np.linalg.norm(cpts[:, [0, 2]] - center[[0, 2]], axis=1)
        holes.append(dict(center=center, radius=d.mean(), radius_std=d.std(), n=len(idxs)))

    holes.sort(key=lambda h: -h["n"])
    return holes


def fin_alignment_matrix(local_root, local_tip, local_normal, world_root, world_tip, world_normal):
    ls = local_tip - local_root
    ls /= np.linalg.norm(ls)
    ln = local_normal / np.linalg.norm(local_normal)
    ln = ln - np.dot(ln, ls) * ls
    ln /= np.linalg.norm(ln)
    lb = np.cross(ln, ls)
    src = np.stack([ls, lb, ln], axis=1)

    ws = world_tip - world_root
    ws /= np.linalg.norm(ws)
    wn = world_normal / np.linalg.norm(world_normal)
    wn = wn - np.dot(wn, ws) * ws
    wn /= np.linalg.norm(wn)
    wb = np.cross(wn, ws)
    dst = np.stack([ws, wb, wn], axis=1)

    R = dst @ src.T
    t = world_root - R @ local_root
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = t
    return M


def radial_dir(theta_deg):
    th = np.radians(theta_deg)
    return np.array([np.sin(th), np.cos(th), 0.0])


def tangential_dir(theta_deg):
    return np.cross(np.array([0, 0, 1.0]), radial_dir(theta_deg))


def main():
    import yaml

    cfg = yaml.safe_load((ROOT / "scripts" / "assembly.yaml").read_text())["parts"]
    body = load_part("body", cfg["body"])

    holes = find_holes(body)
    print(f"found {len(holes)} hole clusters with >=6 points; top 20 by point count:\n")
    for h in holes[:20]:
        c = h["center"]
        print(f"  n={h['n']:4d}  center=({c[0]:7.2f},{c[1]:7.2f},{c[2]:7.2f})  radius~{h['radius']:.2f} (std {h['radius_std']:.2f})")

    # bezel mounting holes: 4 clusters, radius ~1.3mm, off-centre (x ~ +-18.7),
    # forming a rectangle. Excludes the on-centreline LED-candidate cluster,
    # which happens to have a similar radius (~1.5mm) but sits at x~0.
    bezel_holes = [h for h in holes if 1.0 < h["radius"] < 1.6 and h["n"] > 100 and abs(h["center"][0]) > 10]
    zs = [h["center"][2] for h in bezel_holes]
    print(f"\nbezel mounting holes -> Z span {min(zs):.1f} to {max(zs):.1f}, centre {sum(zs)/len(zs):.1f}")

    # knob hole: radius ~9mm (matches knob.stl's 18mm diameter)
    knob_holes = [h for h in holes if 8 < h["radius"] < 10]
    if knob_holes:
        c = np.mean([h["center"] for h in knob_holes], axis=0)
        print(f"knob hole -> centre ({c[0]:.2f},{c[1]:.2f},{c[2]:.2f})")

    # fin mounting holes (right side): radius ~1.5-1.9mm, x>25
    fin_holes = [h for h in holes if 1.4 < h["radius"] < 2.0 and h["center"][0] > 25]
    print(f"fin mounting holes (right side): {[h['center'].round(1).tolist() for h in fin_holes]}")


if __name__ == "__main__":
    main()
