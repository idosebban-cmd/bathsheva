"""
Measures the real gap (or overlap) between the knob and the bezel/grille,
both at their mesh-derived positions (see assembly.yaml), using actual
transformed mesh geometry rather than assumed bounding boxes.

Run: python3 scripts/measure_knob_gap.py
"""

import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lineart import load_part  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    cfg = yaml.safe_load((ROOT / "scripts" / "assembly.yaml").read_text())["parts"]

    knob = load_part("knob", cfg["knob"])
    bezel = load_part("bezel", cfg["bezel"])
    grille = load_part("grille", cfg["grille"])

    knob_top_z = knob.bounds[1][2]
    knob_bottom_z = knob.bounds[0][2]
    bezel_bottom_z = bezel.bounds[0][2]
    bezel_top_z = bezel.bounds[1][2]
    grille_bottom_z = grille.bounds[0][2]

    print(f"knob:   Z {knob_bottom_z:.2f} to {knob_top_z:.2f}  (mesh bounds, exact mounting-hole position)")
    print(f"bezel:  Z {bezel_bottom_z:.2f} to {bezel_top_z:.2f}")
    print(f"grille: Z {grille_bottom_z:.2f} to ...")
    print()

    gap_bezel = bezel_bottom_z - knob_top_z
    gap_grille = grille_bottom_z - knob_top_z
    print(f"knob top edge to bezel bottom edge (along Z, both on the X=0 centreline): {gap_bezel:+.1f} mm")
    print(f"knob top edge to grille bottom edge:                                      {gap_grille:+.1f} mm")
    print("(negative = overlap)")
    print()

    # also compute true minimum 3D surface-to-surface distance, not just the Z-axis
    # figure, in case the closest approach isn't straight up the centreline
    from scipy.spatial import cKDTree
    knob_top_pts = knob.vertices[knob.vertices[:, 2] > knob_top_z - 3]
    bezel_bottom_pts = bezel.vertices[bezel.vertices[:, 2] < bezel_bottom_z + 3]
    tree = cKDTree(bezel_bottom_pts)
    dists, _ = tree.query(knob_top_pts)
    min_dist = dists.min()
    closest_idx = dists.argmin()
    print(f"true minimum surface-to-surface distance (knob vs bezel, 3D, near the top/bottom edges): {min_dist:.1f} mm")
    print(f"  (at knob point {knob_top_pts[closest_idx].round(1)})")
    print()
    if gap_bezel < 3:
        print("ISSUE: gap is under 3mm (or overlapping) -- flag as a model design issue, not a rendering choice.")


if __name__ == "__main__":
    main()
