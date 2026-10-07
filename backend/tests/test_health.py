"""/api/health: whether the running server still has the code that is on disk."""


def test_health_reports_stale_code(client, monkeypatch):
    """After an update the files on disk change but a running server keeps its old code: /api/health says so
    (the front end shows a restart banner and the macOS launcher restarts the server)."""
    from app import codeversion

    h = client.get("/api/health").json()
    assert h["stale"] is False and len(h["code"]) == 12
    monkeypatch.setattr(codeversion, "LOADED", "0" * 40)  # as if the code on disk changed since start-up
    assert client.get("/api/health").json()["stale"] is True


def test_code_fingerprint_follows_files(tmp_path, monkeypatch):
    from app import codeversion

    monkeypatch.setattr(codeversion, "WATCHED", (tmp_path,))
    monkeypatch.setattr(codeversion, "REPO_DIR", tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "__pycache__").mkdir()
    before = codeversion.fingerprint()
    (tmp_path / "__pycache__" / "a.cpython-312.pyc").write_bytes(b"\0")  # bytecode caches don't count
    assert codeversion.fingerprint() == before
    (tmp_path / "a.py").write_text("x = 22\n")  # an update rewrites the file
    assert codeversion.fingerprint() != before
