"""Export the FARO nameplate lettering (prototype font and size) to backend/seed/artwork/ as SVG and DXF.

Usage (from the repo root): backend/.venv/bin/python scripts/export_nameplate_artwork.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.factory import nameplate  # noqa: E402

for kind, path in nameplate.export(nameplate.ARTWORK_DIR).items():
    print(f"Wrote {path.relative_to(ROOT)}")
