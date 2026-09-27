"""
Clean single-weight line-art generator for the Atelier manual.

Loads the source STLs, rebuilds the real assembly from manual/scripts/assembly.yaml
(the STLs are individually oriented for 3D printing, not for the product), extracts
silhouette + crease + boundary edges, removes hidden lines with true ray-cast
occlusion testing against the full assembly, and writes a black-line SVG.

No shaded renders, no AI images: every line in the output traces real geometry
from the same STL files used for printing.
"""

import math
from pathlib import Path

import numpy as np
import trimesh
import yaml

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
ASSEMBLY_YAML = ROOT / "scripts" / "assembly.yaml"

CREASE_ANGLE_DEG = 20.0  # dihedral angle above which an edge is a "feature" line
SAMPLE_SPACING = 1.5  # mm between visibility test points along an edge
OCCLUSION_EPS = 0.15  # mm, ignore self-hits closer than this
GRILLE_MIN_EDGE_LEN = 6.0  # mm, drop shorter grille edges (honeycomb texture) for a clean look


def rotation_matrix(axis, deg):
    if axis == "NONE" or deg == 0:
        return np.eye(4)
    axis_vec = {"X": [1, 0, 0], "Y": [0, 1, 0], "Z": [0, 0, 1]}[axis]
    return trimesh.transformations.rotation_matrix(math.radians(deg), axis_vec)


def translation_matrix(t):
    m = np.eye(4)
    m[:3, 3] = t
    return m


def load_part(name, cfg):
    mesh = trimesh.load(MODELS / cfg["file"])
    R = rotation_matrix(cfg["rotate"]["axis"], cfg["rotate"]["deg"])
    Tr = translation_matrix(cfg["translate"])
    if "tilt" in cfg:
        # fins: tilt (local splay) -> translate (offset from axis) -> rotate (world azimuth)
        Tilt = rotation_matrix(cfg["tilt"]["axis"], cfg["tilt"]["deg"])
        T = R @ Tr @ Tilt
    else:
        # body/nose_cone/collar/foot/grille/bezel/knob: rotate (local flip) -> translate (world position)
        T = Tr @ R
    mesh.apply_transform(T)
    mesh.metadata["part_name"] = name
    return mesh


def feature_edges(mesh, view_vector, min_len=0.0):
    """Return (Nx2x3 endpoints, part-relative edge lengths) for crease + silhouette + boundary edges."""
    edges_out = []

    # crease edges: dihedral angle between adjacent faces exceeds threshold
    angles = mesh.face_adjacency_angles
    crease_mask = angles > math.radians(CREASE_ANGLE_DEG)

    # silhouette edges: adjacent faces on opposite sides of front/back w.r.t. camera
    normals = mesh.face_normals
    facing = normals @ view_vector
    fa = mesh.face_adjacency
    sign_a = facing[fa[:, 0]] > 0
    sign_b = facing[fa[:, 1]] > 0
    silhouette_mask = sign_a != sign_b

    keep = crease_mask | silhouette_mask
    adj_edges = mesh.face_adjacency_edges[keep]
    for e in adj_edges:
        p0, p1 = mesh.vertices[e[0]], mesh.vertices[e[1]]
        if np.linalg.norm(p1 - p0) >= min_len:
            edges_out.append((p0, p1))

    # boundary edges (open, non-manifold rims e.g. spigots) always count as features
    boundary = mesh.edges[trimesh.grouping.group_rows(mesh.edges_sorted, require_count=1)]
    for e in boundary:
        p0, p1 = mesh.vertices[e[0]], mesh.vertices[e[1]]
        if np.linalg.norm(p1 - p0) >= min_len:
            edges_out.append((p0, p1))

    return edges_out


def sample_edge(p0, p1, spacing):
    length = np.linalg.norm(p1 - p0)
    n = max(2, int(math.ceil(length / spacing)) + 1)
    ts = np.linspace(0.0, 1.0, n)
    return np.array([p0 + t * (p1 - p0) for t in ts]), ts


def visible_mask(points, view_vector, occluder):
    """True where a point is NOT blocked by the occluder mesh on the way to the camera."""
    origins = points + OCCLUSION_EPS * view_vector
    directions = np.tile(view_vector, (len(points), 1))
    intersector = trimesh.ray.ray_triangle.RayMeshIntersector(occluder)
    locations, index_ray, _ = intersector.intersects_location(origins, directions, multiple_hits=True)
    occluded = np.zeros(len(points), dtype=bool)
    if len(locations):
        dist = np.linalg.norm(locations - origins[index_ray], axis=1)
        real_hit = dist > OCCLUSION_EPS
        occluded[index_ray[real_hit]] = True
    return ~occluded


def project(points, right, up):
    x = points @ right
    y = points @ up
    return np.stack([x, y], axis=1)


def render_view(parts_cfg, part_names, view_vector, up_vector, out_svg, label=""):
    view_vector = np.array(view_vector, dtype=float)
    view_vector /= np.linalg.norm(view_vector)
    up_vector = np.array(up_vector, dtype=float)
    right_vector = np.cross(up_vector, view_vector)
    right_vector /= np.linalg.norm(right_vector)

    meshes = {}
    for name in part_names:
        meshes[name] = load_part(name, parts_cfg[name])
    occluder = trimesh.util.concatenate(list(meshes.values()))

    all_segments = []
    for name, mesh in meshes.items():
        min_len = GRILLE_MIN_EDGE_LEN if name == "grille" else 0.0
        edges = feature_edges(mesh, -view_vector, min_len=min_len)
        for p0, p1 in edges:
            pts, _ = sample_edge(p0, p1, SAMPLE_SPACING)
            vis = visible_mask(pts, view_vector, occluder)
            # split into contiguous visible runs
            start = None
            for i, v in enumerate(vis):
                if v and start is None:
                    start = i
                if (not v or i == len(vis) - 1) and start is not None:
                    end = i if v else i - 1
                    if end > start:
                        all_segments.append((pts[start], pts[end]))
                    start = None

    write_svg(all_segments, right_vector, up_vector, out_svg, label)
    print(f"{out_svg.name}: {len(all_segments)} visible segments from {sum(len(feature_edges(m, -view_vector)) for m in meshes.values())} candidate edges")


def write_svg(segments, right, up, out_path, label=""):
    pts2d = [project(np.array([p0, p1]), right, up) for p0, p1 in segments]
    allpts = np.concatenate(pts2d, axis=0)
    minx, miny = allpts.min(axis=0)
    maxx, maxy = allpts.max(axis=0)
    margin = 10
    w = maxx - minx + 2 * margin
    h = maxy - miny + 2 * margin

    def flip(pt):
        # SVG y grows downward; our projected "up" should point up on the page
        return pt[0] - minx + margin, h - (pt[1] - miny + margin)

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h:.1f}" width="{w:.1f}mm" height="{h:.1f}mm">')
    lines.append(f'<rect x="0" y="0" width="{w:.1f}" height="{h:.1f}" fill="#F7F3EC"/>')
    lines.append(f'<g stroke="#0A0A0A" stroke-width="0.35" stroke-linecap="round" fill="none">')
    for p0, p1 in pts2d:
        x0, y0 = flip(p0)
        x1, y1 = flip(p1)
        lines.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}"/>')
    lines.append("</g>")
    if label:
        lines.append(f'<text x="8" y="{h-6:.1f}" font-family="monospace" font-size="4" fill="#999">{label}</text>')
    lines.append("</svg>")
    out_path.write_text("\n".join(lines))


def main():
    cfg = yaml.safe_load(ASSEMBLY_YAML.read_text())
    parts_cfg = cfg["parts"]
    out_dir = ROOT / "figures" / "_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    confident = ["body", "nose_cone", "collar", "foot"]
    render_view(
        parts_cfg, confident, cfg["camera"]["front"]["view_dir"], cfg["camera"]["front"]["up"],
        out_dir / "test_front_confident.svg",
        label="body + nose_cone + collar + foot -- verified transforms, no guessed placement",
    )

    full = confident + ["grille", "bezel", "knob", "fin_1", "fin_2", "fin_3"]
    render_view(
        parts_cfg, full, cfg["camera"]["front"]["view_dir"], cfg["camera"]["front"]["up"],
        out_dir / "test_front_full_estimate.svg",
        label="full assembly -- grille/bezel/knob/fins are ESTIMATED placement, pending review",
    )


if __name__ == "__main__":
    main()
