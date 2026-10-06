"""Where user data (database, uploads, CAD outputs) lives.

User data is kept outside the repository, so updating the code never touches it.
Default: ~/Bathsheva Workbench/data. Override with WORKBENCH_DATA_DIR.

Older checkouts kept data inside the repo (<repo>/data). `migrate_legacy_data`
moves that folder to the new location once, if the new location is still empty.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable, Mapping
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

DEFAULT_DATA_DIR = Path.home() / "Bathsheva Workbench" / "data"
LEGACY_DATA_DIRS = (REPO_DIR / "data", BACKEND_DIR / "data")


def data_dir_from_env(env: Mapping[str, str] = os.environ) -> tuple[Path, bool]:
    """The data folder and whether it is the default (no WORKBENCH_DATA_DIR set)."""
    raw = env.get("WORKBENCH_DATA_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve(), False
    return DEFAULT_DATA_DIR.resolve(), True


def _is_empty(path: Path) -> bool:
    return not path.exists() or not any(path.iterdir())


def migrate_legacy_data(target: Path, legacy_dirs: Iterable[Path] = LEGACY_DATA_DIRS) -> list[str]:
    """Move the first non-empty legacy data folder to `target` if `target` is empty.

    Never merges or overwrites: if `target` already holds data, legacy folders are
    left where they are and a warning is returned. Returns plain-English messages.
    """
    messages: list[str] = []
    target = target.resolve()
    for legacy in legacy_dirs:
        legacy = legacy.resolve()
        if legacy == target or _is_empty(legacy):
            continue
        if _is_empty(target):
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.rmdir()
            shutil.move(str(legacy), str(target))
            messages.append(f"Moved your existing data from {legacy} to {target}.")
        else:
            messages.append(
                f"Found older data in {legacy}, but {target} already has data, so nothing was moved. "
                "Move or delete one of them by hand if you need to."
            )
    return messages

