"""Projects page: deleting a project (records and files) and its created / updated timestamps."""

import io
import time
from datetime import datetime, timezone

from sqlalchemy import inspect, text

from app.config import settings
from app.db import new_session


def _faro(client, name="Faro"):
    r = client.post("/api/projects", json={"name": name, "template": "faro"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _fill(client, pid):
    """Give a project records in every area plus files in its data folder."""
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    assert client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params}).status_code == 201
    png = io.BytesIO(b"\\x89PNG\\r\\n\\x1a\\n" + b"0" * 64)
    assert client.post(f"/api/projects/{pid}/images", files={"file": ("concept.png", png, "image/png")},
                       data={"kind": "concept"}).status_code == 201
    base = next(p for p in client.get(f"/api/projects/{pid}/parts").json() if p["cad_key"] == "base")
    assert client.post(f"/api/projects/{pid}/parts/{base['id']}/quotes", data={
        "source": "Spinner", "quote_date": "2026-10-01", "quantity": "100", "unit_price": "12"},
        files={"attachment": ("quote.pdf", io.BytesIO(b"%PDF-1.4 quote"), "application/pdf")}).status_code == 201
    assert client.post(f"/api/projects/{pid}/revisions", json={"note": "Before delete"}).status_code == 201
    client.put(f"/api/projects/{pid}/factory-pack/contact", json={"company_name": "Bathsheva London"})


def _rows_for(pid: int) -> dict[str, int]:
    """Rows still pointing at the project in every table that has a project_id column."""
    session = new_session()
    try:
        insp = inspect(session.get_bind())
        out = {}
        for table in insp.get_table_names():
            if "project_id" in {c["name"] for c in insp.get_columns(table)}:
                n = session.execute(text(f"SELECT COUNT(*) FROM {table} WHERE project_id = :p"), {"p": pid}).scalar()
                if n:
                    out[table] = n
        n = session.execute(text("SELECT COUNT(*) FROM projects WHERE id = :p"), {"p": pid}).scalar()
        if n:
            out["projects"] = n
        return out
    finally:
        session.close()


def test_delete_removes_records_and_files_and_keeps_other_projects(client):
    keep, gone = _faro(client, "Faro keep"), _faro(client, "Faro delete")
    _fill(client, keep)
    _fill(client, gone)
    gone_dir, keep_dir = settings.data_dir / "projects" / str(gone), settings.data_dir / "projects" / str(keep)
    assert any(gone_dir.rglob("*.step")) and any(gone_dir.rglob("*.png")) and any(gone_dir.rglob("*.pdf"))
    before = _rows_for(gone)
    assert {"parts", "cad_models", "external_quotes", "cost_items", "revisions", "reference_images",
            "engineering_decisions"} <= set(before), before

    r = client.delete(f"/api/projects/{gone}")
    assert r.status_code == 204
    assert client.get(f"/api/projects/{gone}").status_code == 404
    assert _rows_for(gone) == {}  # nothing left in any table
    assert not gone_dir.exists()  # uploads, quote attachments and generated CAD are gone
    assert gone not in [p["id"] for p in client.get("/api/projects").json()]

    # The other project, its records and its files are untouched.
    assert client.get(f"/api/projects/{keep}").status_code == 200
    assert set(_rows_for(keep)) == set(before)
    assert any(keep_dir.rglob("*.step")) and any(keep_dir.rglob("*.png"))
    assert client.get(f"/api/projects/{keep}/factory-pack/contact").json()["values"]["company_name"] == "Bathsheva London"


def test_delete_unknown_project_is_404_and_project_without_files_deletes(client):
    assert client.delete("/api/projects/9999").status_code == 404
    pid = client.post("/api/projects", json={"name": "Aztec"}).json()["id"]
    assert not (settings.data_dir / "projects" / str(pid)).exists()  # a blank project has no files yet
    assert client.delete(f"/api/projects/{pid}").status_code == 204
    assert client.delete(f"/api/projects/{pid}").status_code == 404


def test_new_project_never_inherits_a_stale_folder(client):
    """SQLite can reuse the last deleted id: leftover files are moved aside, not inherited or lost."""
    pid = client.post("/api/projects", json={"name": "First"}).json()["id"]
    stale = settings.data_dir / "projects" / str(pid + 1)
    (stale / "cad" / "v1").mkdir(parents=True, exist_ok=True)
    (stale / "cad" / "v1" / "old.step").write_text("ISO-10303-21;")
    new = client.post("/api/projects", json={"name": "Second"}).json()["id"]
    assert new == pid + 1
    assert not stale.exists()
    moved = list((settings.data_dir / "projects" / "_orphaned").glob(f"{new}-*/cad/v1/old.step"))
    assert moved and moved[0].read_text() == "ISO-10303-21;"


def test_timestamps_are_utc_and_updated_follows_any_change(client):
    pid = _faro(client)
    p = client.get(f"/api/projects/{pid}").json()
    created, updated = (datetime.fromisoformat(p[k].replace("Z", "+00:00")) for k in ("created_at", "updated_at"))
    assert created.tzinfo is not None and created.utcoffset().total_seconds() == 0  # sent as UTC, not naive
    assert abs((datetime.now(timezone.utc) - created).total_seconds()) < 60
    listed = next(x for x in client.get("/api/projects").json() if x["id"] == pid)
    assert listed["created_at"] == p["created_at"] and "updated_at" in listed

    def updated_at():
        return datetime.fromisoformat(client.get(f"/api/projects/{pid}").json()["updated_at"].replace("Z", "+00:00"))

    # Editing the project itself.
    time.sleep(0.01)
    client.patch(f"/api/projects/{pid}", json={"description": "New text"})
    u1 = updated_at()
    assert u1 > updated
    # Editing one of its records (a part) also counts as an update.
    part = client.get(f"/api/projects/{pid}/parts").json()[0]
    time.sleep(0.01)
    client.patch(f"/api/projects/{pid}/parts/{part['id']}", json={"function": "Changed"})
    u2 = updated_at()
    assert u2 > u1
    # Generating CAD too; the created time never changes.
    time.sleep(0.01)
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params})
    assert updated_at() > u2
    assert client.get(f"/api/projects/{pid}").json()["created_at"] == p["created_at"]
