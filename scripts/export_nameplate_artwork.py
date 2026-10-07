"""Export the FARO nameplate lettering (Cormorant Garamond SemiBold, bundled) and the knob logo to
backend/seed/artwork/: the outline loops (JSON, used by the CAD model and the drawings) and the SVG and
DXF for the etcher / engraver. Also writes the logo master to brand/logo/ (loops, SVG, PDF, DXF,
transparent PNG), built from the traced curves (brand/logo/faro_logo_curves.json, scripts/trace_logo.py).

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

from app.cad import faro  # noqa: E402
from app.factory import logo  # noqa: E402
from app.services.templates import load_template  # noqa: E402

for kind, path in logo.export_master().items():
    print(f"Wrote {path.relative_to(ROOT)}")
path = logo.export_loops(logo.ARTWORK_DIR)
print(f"Wrote {path.relative_to(ROOT)}")
logo._unit_grooves.cache_clear()
radius = logo.logo_radius(float(load_template("faro")["cad_parameters"]["knob_diameter"]))
for kind, path in logo.export(logo.ARTWORK_DIR, radius).items():
    print(f"Wrote {path.relative_to(ROOT)}")
