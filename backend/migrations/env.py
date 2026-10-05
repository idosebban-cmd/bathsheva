"""Alembic environment: uses the app's models and configured database URL."""

from __future__ import annotations

import logging.config

from alembic import context
from sqlalchemy import create_engine

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.db import Base

config = context.config
# Only configure logging when run from the CLI; the app configures its own.
if config.config_file_name is not None and config.attributes.get("configure_logging", True):
    logging.config.fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    from app.config import settings

    return settings.database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(_url())
    with engine.connect() as conn:
        _run(conn)
    engine.dispose()


def _run(connection) -> None:
    if connection.dialect.name == "sqlite" and not connection.in_transaction():
        # Batch rebuilds drop and recreate tables; with foreign keys on that would
        # cascade-delete child rows. (app.migrate turns them off before calling us.)
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    # render_as_batch lets ALTER-style migrations work on SQLite.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
