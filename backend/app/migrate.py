"""Database migrations (Alembic), run at startup.

Workflow (see CLAUDE.md): change models.py, then from backend/ run
    .venv/bin/alembic revision --autogenerate -m "what changed"
review the generated file in migrations/versions/, and commit it.
"""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

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


def _is_memory(url: str) -> bool:
    return url in ("sqlite://", "sqlite:///:memory:") or ":memory:" in url


def upgrade_database(engine: Engine, database_url: str) -> None:
    """Bring the database to the latest migration.

    On SQLite, migrations run on their own unpooled connection with foreign keys
    off: batch-mode table rebuilds drop and recreate tables, and with foreign keys
    on, dropping a parent table cascade-deletes its children. The app's pooled
    connections keep foreign keys on.
    """
    cfg = alembic_config(database_url)
    is_sqlite = database_url.startswith("sqlite")
    mig_engine = engine if (not is_sqlite or _is_memory(database_url)) else create_engine(database_url, poolclass=NullPool)
    try:
        with mig_engine.connect() as conn:
            if is_sqlite:
                conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
                conn.commit()
            with conn.begin():
                cfg.attributes["connection"] = conn
                tables = set(inspect(conn).get_table_names())
                if "alembic_version" not in tables and "projects" in tables:
                    # Pre-migration database created by create_all: adopt it at the baseline.
                    command.stamp(cfg, BASELINE_REVISION)
                command.upgrade(cfg, "head")
            if is_sqlite and mig_engine is engine:
                conn.exec_driver_sql("PRAGMA foreign_keys=ON")
                conn.commit()
    finally:
        if mig_engine is not engine:
            mig_engine.dispose()
