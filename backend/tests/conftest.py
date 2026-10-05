import os
import tempfile

# Configure an isolated data dir and no LLM before the app is imported.
_tmp = tempfile.mkdtemp(prefix="workbench-test-")
os.environ["WORKBENCH_DATA_DIR"] = _tmp
os.environ["WORKBENCH_LLM_PROVIDER"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import init_db, new_session  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    init_db(f"sqlite:///{tmp_path / 'test.db'}")
    session = new_session()
    yield session
    session.close()


@pytest.fixture()
def client(tmp_path):
    from app.main import create_app

    app = create_app()
    init_db(f"sqlite:///{tmp_path / 'api.db'}")
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def faro_project(client):
    r = client.post("/api/projects", json={"name": "Faro", "template": "faro"})
    assert r.status_code == 201, r.text
    return r.json()


__all__ = ["settings"]
