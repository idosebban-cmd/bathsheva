"""Which code the running server loaded, and whether the files on disk have changed since.

The backend loads its Python code, seed data and artwork once, at start-up (no auto-reload). After an
update (git pull, setup) a server that was left running keeps building CAD, costs and documents with
the old code, while the web page refreshes. /api/health reports `stale` so the front end can say so and
the macOS launcher can restart the server instead of reopening it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.datadir import BACKEND_DIR, REPO_DIR

WATCHED = (BACKEND_DIR / "app", BACKEND_DIR / "seed", REPO_DIR / "brand")
SKIP_DIRS = {"__pycache__", ".pytest_cache"}


def fingerprint() -> str:
    """Hash of every watched file's path, size and modification time (a few ms)."""
    h = hashlib.sha1()
    for root in WATCHED:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or SKIP_DIRS.intersection(p.parts) or p.suffix == ".pyc":
                continue
            st = p.stat()
            h.update(f"{p.relative_to(REPO_DIR).as_posix()}\0{st.st_size}\0{st.st_mtime_ns}\n".encode())
    return h.hexdigest()


LOADED = fingerprint()


def status() -> dict[str, object]:
    return {"code": LOADED[:12], "stale": fingerprint() != LOADED}
