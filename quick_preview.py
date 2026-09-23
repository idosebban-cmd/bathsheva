"""
Quick look at the front view, in a few seconds:

    python quick_preview.py            # -> output/preview_front.png
    python quick_preview.py side       # or: front, side, rear, three_quarter, three_quarter_rear

Builds only the visible parts (no internals), with the honeycomb off, and renders
one view at reduced size and mesh detail. Use `python build.py` for the real outputs.
"""
import sys
import time
from pathlib import Path

import model
import params as p
import render

view = sys.argv[1] if len(sys.argv) > 1 else "front"
t0 = time.time()
p.HEX_PATTERN_ENABLED = False
p.RENDER_SIZE = (600, 800)
render.MESH_TOL = 0.15
render.FAST = True
m = model.build(p, visual_only=True)
out = Path(__file__).parent / "output"
files = render.render_views(m, p, out, views=[view], prefix="preview", section=False)
print(f"{files[0]}  ({time.time() - t0:.1f} s)")
