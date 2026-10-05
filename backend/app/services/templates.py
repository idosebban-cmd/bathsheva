"""Product templates (seed/products/*.yaml)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from app.config import SEED_DIR


@lru_cache
def load_template(name: str) -> dict[str, Any]:
    path = SEED_DIR / "products" / f"{name}.yaml"
    if not path.exists():
        raise KeyError(f"Unknown product template: {name}")
    with path.open() as f:
        return yaml.safe_load(f)
