"""Alembic migrations must produce exactly the schema described by the models."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.db import Base, init_db, new_session
from app.migrate import alembic_config, upgrade_database
from app.services.projects import create_project


def _schema(engine):
    """A comparable description of every table: columns, FKs, unique constraints, indexes."""
    insp = inspect(engine)
    out = {}
    for t in sorted(insp.get_table_names()):
        if t == "alembic_version":
            continue
        out[t] = {
            "columns": [(c["name"], str(c["type"]), c["nullable"]) for c in insp.get_columns(t)],
            "pk": insp.get_pk_constraint(t)["constrained_columns"],
            "fks": sorted(
                (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]),
                 (fk.get("options") or {}).get("ondelete"))
                for fk in insp.get_foreign_keys(t)
            ),
            "unique": sorted(tuple(u["column_names"]) for u in insp.get_unique_constraints(t)),
            "indexes": sorted((tuple(i["column_names"]), bool(i["unique"])) for i in insp.get_indexes(t)),
        }
    return out


def _head():
    return ScriptDirectory.from_config(alembic_config("sqlite://")).get_current_head()


def _current(engine):
    with engine.connect() as conn:
        return conn.execute(text("select version_num from alembic_version")).scalar()


def test_single_migration_head():
    heads = ScriptDirectory.from_config(alembic_config("sqlite://")).get_heads()
    assert len(heads) == 1, f"multiple Alembic heads: {heads}"


def test_fresh_migration_matches_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    migrated = create_engine(url)
    upgrade_database(migrated, url)
    assert _current(migrated) == _head()

    # 1. Alembic's own autogenerate diff finds nothing to change.
    with migrated.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert diff == [], f"models and migrations differ: {diff}"

    # 2. The reflected schema is identical to one built straight from the models.
    from_models = create_engine(f"sqlite:///{tmp_path / 'models.db'}")
    Base.metadata.create_all(from_models)
    assert _schema(migrated) == _schema(from_models)


def test_init_db_migrates_and_app_works(tmp_path):
    engine = init_db(f"sqlite:///{tmp_path / 'app.db'}")
    assert _current(engine) == _head()
    session = new_session()
    project = create_project(session, "Faro", template="faro")
    assert len(project.parts) == 7
    session.close()
    # Re-running startup on an up-to-date database is a no-op.
    init_db(f"sqlite:///{tmp_path / 'app.db'}")
    session = new_session()
    assert session.execute(text("select count(*) from projects")).scalar() == 1
    session.close()


def test_pre_migration_database_is_adopted(tmp_path):
    """A Milestone 1 database built with create_all (no alembic_version) keeps its data."""
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    legacy = create_engine(url)
    Base.metadata.create_all(legacy)
    with legacy.begin() as conn:
        conn.execute(text(
            "insert into projects (name, slug, description, template, requirements, assumed_fields, created_at, updated_at) "
            "values ('Old', 'old', '', null, '{}', '[]', '2026-01-01', '2026-01-01')"
        ))
    legacy.dispose()

    engine = init_db(url)
    assert _current(engine) == _head()
    with engine.connect() as conn:
        # Data survives: the baseline was stamped rather than the tables re-created.
        assert conn.execute(text("select name from projects")).scalar() == "Old"


def test_downgrade_and_upgrade_round_trip(tmp_path):
    url = f"sqlite:///{tmp_path / 'rt.db'}"
    engine = create_engine(url)
    upgrade_database(engine, url)
    cfg = alembic_config(url)
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    upgrade_database(engine, url)
    assert _current(engine) == _head()
    assert "projects" in inspect(engine).get_table_names()
