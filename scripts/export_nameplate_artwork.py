"""Export the FARO nameplate lettering (Cormorant Garamond SemiBold, bundled) to backend/seed/artwork/:
the outline loops (JSON, used by the CAD model and the drawing) and the SVG and DXF for the etcher.

Usage (from the repo root): backend/.venv/bin/python scripts/export_nameplate_artwork.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.factory import nameplate  # noqa: E402

path = nameplate.export_loops(nameplate.ARTWORK_DIR)  # first: the SVG and DXF below are drawn from these loops
print(f"Wrote {path.relative_to(ROOT)}")
nameplate._letters_cached.cache_clear()
for kind, path in nameplate.export(nameplate.ARTWORK_DIR).items():
    print(f"Wrote {path.relative_to(ROOT)}")
