"""
Generates the actual figure set used in the manual (manual/figures/final/),
using the assembled geometry from scripts/lineart.py + scripts/assembly.yaml.

Run: python3 scripts/make_figures.py
Output: manual/figures/final/*.svg (+ .png previews via a separate step,
see manual/build.py)
"""

import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lineart as la  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "figures" / "final"

CONFIDENT = ["body", "nose_cone", "collar", "foot"]
FITTED = ["grille", "bezel", "knob", "fin_1", "fin_2", "fin_3"]
FULL = CONFIDENT + FITTED

# world-space anchor points, reused across figures for callouts. Grille/LED/
# knob match the mesh-derived positions in assembly.yaml (scripts/find_front_holes.py).
NOSE_TIP = (0, 0, 258.3)
GRILLE_CENTER = (0, 50, 136.1)
LED_POINT = (0, 49.0, 88.1)
KNOB_POINT = (0, 50, 71.35)
FIN_TIP = (59.66, 34.45, -22.0)  # fin_2, azimuth 60 deg
FOOT_TIP = (0, 0, -29.8)
USB_PORT = (-15.8, -1.4, -16.7)


def main():
    cfg = yaml.safe_load((ROOT / "scripts" / "assembly.yaml").read_text())
    parts_cfg = cfg["parts"]
    markers_cfg = cfg.get("markers", {})
    OUT.mkdir(parents=True, exist_ok=True)

    front = cfg["camera"]["front"]
    underside = cfg["camera"]["underside"]

    results = {}

    # 1. Hero front view, no callouts -- for the cover and "in the box"
    results["hero_front"] = la.render_view(
        parts_cfg, FULL, front["view_dir"], front["up"],
        OUT / "hero_front.svg", page_scale=1.0,
        markers_cfg=markers_cfg, marker_names=["led"],
    )

    # 2. Front view with numbered callouts -- "getting to know Atelier"
    callouts = [
        (NOSE_TIP, "1", "Nose cone"),
        (GRILLE_CENTER, "2", "Grille"),
        (LED_POINT, "3", "LED"),
        (KNOB_POINT, "4", "Knob"),
        (FIN_TIP, "5", "Fins"),
        (FOOT_TIP, "6", "Foot"),
    ]
    results["front_callouts"] = la.render_view(
        parts_cfg, FULL, front["view_dir"], front["up"],
        OUT / "front_callouts.svg", page_scale=1.0,
        markers_cfg=markers_cfg, marker_names=["led"],
        callouts=callouts,
    )

    # 3. Underside view -- USB-C port + foot. collar/foot only: verified, high confidence.
    under_callouts = [
        (USB_PORT, "1", "USB-C port"),
        (FOOT_TIP, "2", "Foot"),
    ]
    results["underside_callouts"] = la.render_view(
        parts_cfg, ["collar", "foot"], underside["view_dir"], underside["up"],
        OUT / "underside_callouts.svg", page_scale=1.0,
        callouts=under_callouts,
    )

    # 4. Knob close-up: cropped tight around the knob, zoomed in.
    #    Arrows for turn/press/hold are added as a schematic overlay afterwards
    #    (not derived from geometry -- they're instructional, not physical).
    #    Knob is at its real mounting-hole position (world Z 62.35-80.35,
    #    see assembly.yaml) with a genuine ~19mm clearance to the grille/
    #    bezel above it (scripts/measure_knob_gap.py), so body+knob alone
    #    frames cleanly without needing the bezel for context.
    results["knob_closeup"] = la.render_view(
        parts_cfg, ["body", "knob"], front["view_dir"], front["up"],
        OUT / "knob_closeup_base.svg", page_scale=2.2,
        crop=(-20, 20, 58, 90),
    )

    # Persist each figure's real fitted_by_eye status (not a hand-maintained
    # guess -- build.py reads this to decide the "Provisional illustration"
    # footer, since a static list went stale the moment the knob stopped
    # being fitted_by_eye but knob_closeup was still hardcoded as provisional).
    status = {name: res["fitted_by_eye"] for name, res in results.items()}
    (OUT / "fitted_status.json").write_text(json.dumps(status, indent=2) + "\n")

    for name, res in results.items():
        print(f"{name}: fitted_by_eye={res['fitted_by_eye']}")


if __name__ == "__main__":
    main()
