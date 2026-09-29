"""
Derives the fin_1/2/3 matrix4 transforms in scripts/assembly.yaml from
fin_x3.stl's own pilot holes and body.stl's real fin mounting holes.

Replaces an earlier, wrong fin orientation (sticking out sideways from a
point instead of sweeping down to the floor, per Ido's review) that came
from a rough root point plus a hand-picked tilt/footprint radius. This
script uses only mesh geometry plus one physical constraint (the tip
reaches as close to the floor as the mesh allows) -- see assembly.yaml's
note above the fin_1 entry for the full method and its one open point (a
~4mm shortfall to the exact floor level).

Run: python3 scripts/find_fin_transform.py
"""

import sys
from pathlib import Path

import numpy as np
import trimesh
import yaml
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lineart import load_part, feature_edges  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# fin_x3.stl local frame (print-orientation coords), from tracing the
# planform outline (all vertices projected to XY) and finding its own
# pilot holes with the same cluster method used on body.stl.
LOCAL_HOLE_UPPER = np.array([-8.66, -22.10, 4.00])   # nearer the pointed root tip
LOCAL_HOLE_LOWER = np.array([-11.45, -14.27, 4.00])
LOCAL_TIP_ROOT = np.array([-4.70, -43.87, 4.0])       # pointed end: top attachment point
LOCAL_TIP_FLOOR = np.array([23.33, 43.87, 4.0])       # far outer corner: floor tip
LOCAL_NORMAL = np.array([0, 0, 1.0])


def find_body_holes(body, view_vector, region_filter, r_lo, r_hi, min_points=10, std_max=0.6):
    edges = feature_edges(body, -view_vector)
    sel = [(p0, p1) for p0, p1, k in edges if region_filter(p0) and region_filter(p1)]
    pts = []
    for p0, p1 in sel:
        pts.append(p0)
        pts.append(p1)
    pts = np.array(pts)
    tree = cKDTree(pts)
    pairs = tree.query_pairs(r=2.0)
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
    results = []
    for idxs in clusters.values():
        if len(idxs) < min_points:
            continue
        cpts = pts[idxs]
        center = cpts.mean(axis=0)
        d = np.linalg.norm(cpts[:, [0, 2]] - center[[0, 2]], axis=1)
        if r_lo < d.mean() < r_hi and d.std() < std_max:
            results.append((center, d.mean(), d.std(), len(idxs)))
    results.sort(key=lambda r: -r[3])
    return results


def rotation_align(a, b):
    """Rotation matrix mapping unit vector a onto unit vector b."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = np.dot(a, b)
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3) if c > 0 else -np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))


def rotation_about_axis(axis, angle):
    axis = axis / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)


def solve_fin(world_hole_upper, world_hole_lower, label, floor_z=-29.8):
    local_axis = LOCAL_HOLE_LOWER - LOCAL_HOLE_UPPER
    world_axis = world_hole_lower - world_hole_upper
    R_base = rotation_align(local_axis, world_axis)

    def transform_point(p, phi):
        R = rotation_about_axis(world_axis, phi) @ R_base
        return R @ (p - LOCAL_HOLE_UPPER) + world_hole_upper

    phis = np.linspace(0, 2 * np.pi, 7200)
    zs = np.array([transform_point(LOCAL_TIP_FLOOR, phi)[2] for phi in phis])
    i = np.argmin(zs)  # twist that brings the floor tip as low as the geometry allows
    phi = phis[i]
    R = rotation_about_axis(world_axis, phi) @ R_base
    t = world_hole_upper - R @ LOCAL_HOLE_UPPER
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = t

    root_w = R @ LOCAL_TIP_ROOT + t
    floor_w = R @ LOCAL_TIP_FLOOR + t
    print(f"--- {label} ---")
    print(f"  det(R)={np.linalg.det(R):.6f}  floor_z={floor_w[2]:.2f} (target {floor_z})  shortfall={floor_w[2]-floor_z:.2f}mm")
    print(f"  root: world={root_w.round(2)} radius={np.linalg.norm(root_w[:2]):.2f}")
    print("  matrix4:")
    for row in M:
        print("    - [" + ", ".join(f"{v:.6f}" for v in row) + "]")
    return M


def main():
    cfg = yaml.safe_load((ROOT / "scripts" / "assembly.yaml").read_text())["parts"]
    body = load_part("body", cfg["body"])

    print("Body fin mounting holes, per azimuth:\n")
    right = find_body_holes(body, np.array([0, -1, 0]), lambda p: p[0] > 20 and p[1] > 10, 1.0, 2.5)
    left = find_body_holes(body, np.array([0, -1, 0]), lambda p: p[0] < -20 and p[1] > 10, 1.0, 2.5)
    back = find_body_holes(body, np.array([0, 1, 0]), lambda p: abs(p[0]) < 10 and p[1] < -20, 1.5, 3.0)
    for label, holes in [("right", right), ("left", left), ("back", back)]:
        print(f"{label}:")
        for c, rm, rs, n in holes:
            print(f"  n={n:4d} center=({c[0]:7.2f},{c[1]:7.2f},{c[2]:7.2f}) r~{rm:.2f} std={rs:.3f}")

    print()
    solve_fin(np.array([36.0, 20.8, 40.20]), np.array([33.6, 19.4, 32.42]), "fin_2 RIGHT (azimuth 60)")
    solve_fin(np.array([-36.0, 20.8, 40.20]), np.array([-33.6, 19.4, 32.42]), "fin_3 LEFT (azimuth -60)")
    solve_fin(np.array([0, -41.6, 40.22]), np.array([0, -38.79, 32.43]), "fin_1 BACK (azimuth 180)")


if __name__ == "__main__":
    main()
