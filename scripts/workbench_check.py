"""Setup checks used by scripts/setup_mac.sh. Run with the backend venv's Python.

    python scripts/workbench_check.py migrate    move old in-repo data out, back up, migrate the DB
    python scripts/workbench_check.py selftest   generate the default Faro CAD in a throwaway folder

`selftest` never touches your real data: it uses a temporary data folder.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def migrate() -> int:
    from app.datadir import data_dir_from_env, migrate_legacy_data

    data_dir, _ = data_dir_from_env()
    for msg in migrate_legacy_data(data_dir):
        print(f"    {msg}")

    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine

    from app.config import settings
    from app.db import init_db
    from app.migrate import alembic_config

    print(f"    Your data folder: {settings.data_dir}")
    db_file = settings.data_dir / "workbench.db"
    if settings.database_url == f"sqlite:///{db_file}" and db_file.exists():
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()
        engine.dispose()
        head = ScriptDirectory.from_config(alembic_config(settings.database_url)).get_current_head()
        if current != head:
            backups = settings.data_dir / "backups"
            backups.mkdir(exist_ok=True)
            dest = backups / f"workbench-{datetime.now():%Y%m%d-%H%M%S}.db"
            shutil.copy2(db_file, dest)
            print(f"    The database needs updating. Backed it up first to {dest}")

    init_db(settings.database_url)
    print("    Database is up to date.")
    return 0


def selftest() -> int:
    tmp = tempfile.mkdtemp(prefix="workbench selftest ")  # space on purpose: real path has one
    os.environ["WORKBENCH_DATA_DIR"] = tmp
    os.environ["WORKBENCH_LLM_PROVIDER"] = "none"
    try:
        from fastapi.testclient import TestClient

        from app.main import create_app

        with TestClient(create_app()) as client:
            assert client.get("/api/health").json()["status"] == "ok", "health check failed"
            r = client.post("/api/projects", json={"name": "Self-test", "template": "faro"})
            assert r.status_code == 201, f"creating the Faro project failed: {r.text}"
            pid = r.json()["id"]
            params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
            r = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params})
            assert r.status_code == 201, f"generating the Faro CAD failed: {r.text}"
            outputs = r.json()["outputs"]
            formats = {o["format"] for o in outputs}
            assert {"step", "stl", "glb"} <= formats, f"missing CAD outputs, got {sorted(formats)}"
            for o in outputs:
                path = Path(tmp) / o["path"]
                assert path.exists() and path.stat().st_size > 0, f"empty CAD file {o['path']}"
            assert client.get(f"/files/{outputs[0]['path']}").status_code == 200, "CAD files are not served"
        print(f"    Generated the default Faro lamp: {len(outputs)} CAD files (STEP, STL, GLB).")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    commands = {"migrate": migrate, "selftest": selftest}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print(__doc__)
        sys.exit(2)
    sys.exit(commands[sys.argv[1]]())
