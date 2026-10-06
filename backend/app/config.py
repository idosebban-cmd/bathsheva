"""Runtime configuration, read from environment variables."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from app.datadir import BACKEND_DIR, data_dir_from_env, migrate_legacy_data

SEED_DIR = BACKEND_DIR / "seed"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    database_url: str
    llm_provider: str  # "anthropic" | "mock" | "none"
    anthropic_model: str


def load_settings() -> Settings:
    data_dir, is_default = data_dir_from_env()
    if is_default:
        # Older checkouts kept data in the repo; move it out once (never overwrites).
        for msg in migrate_legacy_data(data_dir):
            print(f"==> {msg}", file=sys.stderr)
    data_dir.mkdir(parents=True, exist_ok=True)
    db_url = os.environ.get("WORKBENCH_DATABASE_URL", f"sqlite:///{data_dir / 'workbench.db'}")

    provider = os.environ.get("WORKBENCH_LLM_PROVIDER", "").strip().lower()
    if not provider:
        provider = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "none"

    return Settings(
        data_dir=data_dir,
        database_url=db_url,
        llm_provider=provider,
        anthropic_model=os.environ.get("WORKBENCH_ANTHROPIC_MODEL", "claude-opus-5-5"),
    )


settings = load_settings()
