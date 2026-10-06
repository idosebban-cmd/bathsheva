from pathlib import Path

from app.datadir import DEFAULT_DATA_DIR, data_dir_from_env, migrate_legacy_data


def _make_legacy(root: Path) -> Path:
    legacy = root / "repo" / "data"
    (legacy / "projects" / "1").mkdir(parents=True)
    (legacy / "workbench.db").write_bytes(b"db")
    (legacy / "projects" / "1" / "image.png").write_bytes(b"png")
    return legacy


def test_default_and_override(tmp_path):
    assert data_dir_from_env({}) == (DEFAULT_DATA_DIR.resolve(), True)
    assert DEFAULT_DATA_DIR.parts[-2:] == ("Bathsheva Workbench", "data")
    custom = tmp_path / "my data"
    assert data_dir_from_env({"WORKBENCH_DATA_DIR": str(custom)}) == (custom.resolve(), False)
    assert data_dir_from_env({"WORKBENCH_DATA_DIR": "  "})[1] is True


def test_override_expands_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    path, is_default = data_dir_from_env({"WORKBENCH_DATA_DIR": "~/elsewhere"})
    assert path == (tmp_path / "elsewhere").resolve() and not is_default


def test_moves_legacy_data_into_empty_target(tmp_path):
    legacy = _make_legacy(tmp_path)
    target = tmp_path / "Bathsheva Workbench" / "data"
    msgs = migrate_legacy_data(target, [legacy])
    assert len(msgs) == 1 and "Moved" in msgs[0]
    assert not legacy.exists()
    assert (target / "workbench.db").read_bytes() == b"db"
    assert (target / "projects" / "1" / "image.png").read_bytes() == b"png"
    # Re-running is a no-op.
    assert migrate_legacy_data(target, [legacy]) == []


def test_moves_into_existing_empty_target(tmp_path):
    legacy = _make_legacy(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    migrate_legacy_data(target, [legacy])
    assert (target / "workbench.db").exists() and not legacy.exists()


def test_never_overwrites_existing_data(tmp_path):
    legacy = _make_legacy(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    (target / "workbench.db").write_bytes(b"newer")
    msgs = migrate_legacy_data(target, [legacy])
    assert len(msgs) == 1 and "nothing was moved" in msgs[0]
    assert (target / "workbench.db").read_bytes() == b"newer"
    assert (legacy / "workbench.db").read_bytes() == b"db"


def test_ignores_missing_empty_and_same_dirs(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    target = tmp_path / "target"
    assert migrate_legacy_data(target, [tmp_path / "missing", empty, target]) == []
    assert not target.exists()
