"""Database migrations (Alembic), run at startup.

Workflow (see CLAUDE.md): change models.py, then from backend/ run
    .venv/bin/alembic revision --autogenerate -m "what changed"
review the generated file in migrations/versions/, and commit it.
"""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.config import BACKEND_DIR

# The first migration. Its schema is exactly what Milestone 1's create_all built,
# so databases created before migrations existed are stamped at this revision.
BASELINE_REVISION = "0001"


def alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    cfg.attributes["configure_logging"] = False
    return cfg


def upgrade_database(engine: Engine, database_url: str) -> None:
    """Bring the database to the latest migration."""
    cfg = alembic_config(database_url)
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        tables = set(inspect(conn).get_table_names())
        if "alembic_version" not in tables and "projects" in tables:
            # Pre-migration database created by create_all: adopt it at the baseline.
            command.stamp(cfg, BASELINE_REVISION)
        command.upgrade(cfg, "head")
