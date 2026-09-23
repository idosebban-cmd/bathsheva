"""
Build Faro.

    python faro/build.py --draft    # front + side renders -> faro/output/draft/
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lamp  # noqa: E402
import params as p  # noqa: E402
import studio  # noqa: E402

OUT = HERE / "output"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draft", action="store_true", help="front + side renders only (default for now)")
    ap.parse_args()
    t0 = time.time()
    m = lamp.build(p)
    files = studio.render_views(m, p, OUT / "draft", views=("front", "side"))
    files.append(studio.render_underside(m, p, OUT / "draft" / "faro_underside.png"))
    print(f"Draft done in {time.time() - t0:.0f} s:", *files, sep="\n  ")


if __name__ == "__main__":
    main()
