"""
Finds every opening on body.stl's front face (+Y) by ray-casting along the
centreline from far +Y toward -Y and recording where the front surface
opens and closes -- i.e. genuine through-holes/recesses, found directly
from the real mesh surface rather than from vertex density.

This REPLACES the grille/bezel/knob part of refit_from_mesh.py's cluster
approach, which turned out to have a false positive: it identified a noisy,
high-std cluster around file_z 101-110 as "the knob hole", when ray-casting
here shows that stretch of the front face is fully solid (baseline ~45-48mm
radius, no opening at all) -- that cluster was almost certainly boundary
artefacts from the grille recess's own edge (file_z closes at 97.5, right
next to the false positive), not a separate feature. The real knob hole is
at file_z 132.5-143.0, confirmed independently by Ido measuring body.stl
himself and cross-checked here with a full centreline sweep -- see the
usage docstring below and manual/README.md's "Knob/grille/LED derivation"
section for the comparison.

Coordinates are body.stl's own print-orientation frame (file_z=0 at the
cone-joint rim). world_z = 209.1 - file_z (the transform in assembly.yaml's
`body` entry, which is a pure 180deg flip about Y -- doesn't touch X or Y,
so front-facing (+Y) and left/right (X) are identical in both frames).

Run: python3 scripts/find_front_holes.py
"""

from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent


def front_hit(intersector, x, z):
    origin = np.array([[x, 200, z]])
    direction = np.array([[0, -1, 0]])
    locs, idx_ray, idx_tri = intersector.intersects_location(origin, direction, multiple_hits=True)
    return [float(y) for y in locs[:, 1] if y > 0] if len(locs) else []


def sweep_centreline(intersector, z0=0, z1=209, step=0.5):
    """Returns [(open_from_file_z, close_at_file_z), ...] -- every stretch
    where the front face has no material at x=0."""
    openings = []
    open_start = None
    z = z0
    while z < z1:
        is_open = len(front_hit(intersector, 0, z)) == 0
        if is_open and open_start is None:
            open_start = z
        if not is_open and open_start is not None:
            openings.append((open_start, z))
            open_start = None
        z += step
    return openings


def x_extent(intersector, z, x_max=40, step=0.5):
    """At a given z, the x-range where the front face is open."""
    xs_open = [x for x in np.arange(-x_max, x_max, step) if not front_hit(intersector, x, z)]
    if not xs_open:
        return None
    return min(xs_open), max(xs_open)


def main():
    body = trimesh.load(ROOT / "models" / "body.stl")
    intersector = trimesh.ray.ray_triangle.RayMeshIntersector(body)

    print("Centreline (x=0) opening sweep, file_z 0-209:\n")
    openings = sweep_centreline(intersector)
    for start, end in openings:
        center = (start + end) / 2
        world_center = 209.1 - center
        xr = x_extent(intersector, center)
        radius = (xr[1] - xr[0]) / 2 if xr else None
        print(f"  file_z {start:.1f} to {end:.1f}  (span {end-start:.1f})  centre file_z={center:.2f}  world_z={world_center:.2f}" +
              (f"  x-radius~{radius:.1f}mm" if radius else ""))


if __name__ == "__main__":
    main()
