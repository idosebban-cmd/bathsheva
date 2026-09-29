"""
Derives fitted_by_eye placement transforms for grille, bezel, knob, LED and
fins, by matching proportions measured from the reference photo
(manual/reference/atelier_reference_photo.png) against the verified body
geometry (manual/models/body.stl, already correctly assembled).

This is a one-off derivation tool, not part of the regular build. It prints
the numbers that were hand-copied into scripts/assembly.yaml under each
part's `fitted_by_eye: true` entry. Re-run it if the reference photo or the
verified body geometry changes and the fitted parts need re-deriving.

Method
------
1. Pixel measurements from the reference photo (see comments below for how
   each was taken: colour-boundary search, the photo's own cyan/magenta
   guide-trace overlay, or a brightness search for the LED highlight).
2. A local pixel-to-world-Z scale is fit from two unambiguous landmarks that
   are ALSO known exactly from the verified CAD (the nose/body seam and the
   body's own widest point) -- this is a *local* scale for the front-face
   region of the body, not a single global scale for the whole photo, since
   the photo has mild perspective (the local scale near the fin/base region
   drifts by roughly 10% from the local scale near the top -- consistent
   with a slightly low-angle product shot, not a measurement error).
3. Grille/bezel/knob/LED sit on the body's own (verified) surface, so once
   their world Z and X are known, their Y (front-facing depth) is read
   directly off the real body mesh rather than estimated.
4. Fins are solved as a proper 3D rotation: given a root point (near the
   body surface) and a tip point (out at the photo-measured footprint
   radius), a rotation is built that maps the fin's local span axis
   (root->tip) and thickness axis (blade normal) onto their world
   equivalents at each of the 3 azimuths (180, 60, -60 degrees).
"""

import sys
from pathlib import Path

import numpy as np
import trimesh
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lineart import load_part  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# --- pixel measurements from the reference photo (860x1676 px) -----------
# Nose tip: topmost cyan trace pixel.                              y=32
# Nose/body seam: colour transition (gold->oxblood) on the         y=288
#   centerline, confirmed by the magenta trace overlay's top edge.
# Body widest point: cyan trace width plateau (557px, matches the
#   known 96.8mm body diameter exactly), midpoint of the plateau.  y=972
# Grille/bezel: magenta trace overlay's large circle component
#   (centroid 426,695; bbox 393x449px, converts to ~73x77mm,
#   matching the bezel mesh's own 70x79.8mm extents within ~5%).
GRILLE_BEZEL_PX = dict(cx=426, cy=695)
# Knob: magenta trace overlay's smaller circle (centroid 425,1072;
#   bbox 97x95px, converts to ~16.5mm vs the knob mesh's 18mm -- close).
KNOB_PX = dict(cx=425, cy=1072)
# LED: brightness search (near-white, low-saturation cluster) in the
#   band between the grille and the knob -- found at (428, 979).
LED_PX = dict(cx=428, cy=979)
# Fin footprint: cyan trace silhouette max width near the base, ~793px,
#   vs the 557px body diameter -> footprint is 793/557 = 1.424x the
#   body diameter = 137.8mm tip-to-tip, i.e. 68.9mm radius from the axis.
FIN_TIP_RADIUS_MM = 137.8 / 2

CENTERLINE_PX = 424.5
SEAM_PX = dict(y=288, world_z=209.1)  # matches the verified body's nose joint
EQUATOR_PX = dict(y=972, world_z=91.6)  # matches the verified body's widest point (file z 110-125 midpoint)

# local mm-per-pixel scale for the body's front-face region (seam to equator)
SCALE_MM_PER_PX = (EQUATOR_PX["world_z"] - SEAM_PX["world_z"]) / (EQUATOR_PX["y"] - SEAM_PX["y"])


def px_to_world_z(py):
    return SEAM_PX["world_z"] + (py - SEAM_PX["y"]) * SCALE_MM_PER_PX


def body_radius_at_z(body_mesh, z, tol=3.0, x_window=10):
    V = body_mesh.vertices
    mask = (np.abs(V[:, 2] - z) < tol) & (np.abs(V[:, 0]) < x_window) & (V[:, 1] > 0)
    if mask.sum() == 0:
        return None
    return float(V[mask, 1].max())


def fin_alignment_matrix(local_root, local_tip, local_normal, world_root, world_tip, world_normal):
    """Rotation + translation mapping local (root, tip, normal) onto their world targets."""
    ls = local_tip - local_root
    ls /= np.linalg.norm(ls)
    ln = local_normal / np.linalg.norm(local_normal)
    ln = ln - np.dot(ln, ls) * ls  # orthogonalize
    ln /= np.linalg.norm(ln)
    lb = np.cross(ln, ls)
    src = np.stack([ls, lb, ln], axis=1)  # columns

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
    z = np.array([0, 0, 1.0])
    return np.cross(z, radial_dir(theta_deg))


def main():
    cfg = yaml.safe_load((ROOT / "scripts" / "assembly.yaml").read_text())["parts"]
    body = load_part("body", cfg["body"])

    print(f"SCALE_MM_PER_PX = {SCALE_MM_PER_PX:.5f}")

    for name, px in [("grille/bezel", GRILLE_BEZEL_PX), ("knob", KNOB_PX), ("led", LED_PX)]:
        z = px_to_world_z(px["cy"])
        r = body_radius_at_z(body, z)
        print(f"{name}: world_z={z:.1f}  body_radius_here={r}")

    # --- fins ---
    fin = trimesh.load(ROOT / "models" / "fin_x3.stl")
    Vf = fin.vertices
    root_mask = Vf[:, 1] > Vf[:, 1].max() - 8
    tip_mask = Vf[:, 1] < Vf[:, 1].min() + 8
    local_root = Vf[root_mask].mean(axis=0)
    local_tip = Vf[tip_mask].mean(axis=0)
    local_normal = np.array([0, 0, 1.0])
    print(f"\nfin local_root={local_root.round(1)} local_tip={local_tip.round(1)}")

    root_z = 80.0
    root_r = body_radius_at_z(body, root_z)
    tip_z = -22.0
    tip_r = FIN_TIP_RADIUS_MM
    print(f"fin root: z={root_z} r={root_r:.1f}   fin tip: z={tip_z} r={tip_r:.1f}")

    for name, theta in [("fin_1", 180), ("fin_2", 60), ("fin_3", -60)]:
        rad = radial_dir(theta)
        tan = tangential_dir(theta)
        world_root = rad * root_r + np.array([0, 0, root_z])
        world_tip = rad * tip_r + np.array([0, 0, tip_z])
        M = fin_alignment_matrix(local_root, local_tip, local_normal, world_root, world_tip, tan)
        print(f"\n{name} (azimuth {theta} deg):")
        print("matrix4:")
        for row in M:
            print("  [" + ", ".join(f"{v:.6f}" for v in row) + "]")


if __name__ == "__main__":
    main()
