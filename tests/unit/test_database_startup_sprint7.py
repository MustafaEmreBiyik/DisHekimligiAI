"""Sprint 7 startup/schema governance regression tests."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from db import database as database_module


def test_sqlite_db_file_path_resolves_runtime_database_url(monkeypatch):
    db_file = (
        database_module.PROJECT_ROOT
        / ".pytest_runtime_artifacts"
        / "db_path_resolution"
        / "dentai_app.db"
    )
    monkeypatch.setattr(
        database_module,
        "DATABASE_URL",
        f"sqlite:///{db_file.as_posix()}",
    )

    resolved = database_module._sqlite_db_file_path()

    assert resolved == os.path.normpath(str(db_file))


def test_init_db_creates_parent_dir_and_never_calls_create_all(monkeypatch):
    runtime_root = database_module.PROJECT_ROOT / ".pytest_runtime_artifacts" / f"startup_{uuid4().hex}"
    db_file = runtime_root / "db" / "runtime" / "dentai_app.db"
    parent_dir = db_file.parent
    shutil.rmtree(runtime_root, ignore_errors=True)

    monkeypatch.setattr(
        database_module,
        "DATABASE_URL",
        f"sqlite:///{db_file.as_posix()}",
    )

    schema_checked = {"value": False}

    def _mark_schema_checked() -> None:
        schema_checked["value"] = True

    def _forbid_create_all(*_args, **_kwargs):
        raise AssertionError("init_db() must not call Base.metadata.create_all")

    monkeypatch.setattr(database_module, "_ensure_schema_is_current", _mark_schema_checked)
    monkeypatch.setattr(database_module.Base.metadata, "create_all", _forbid_create_all)

    try:
        database_module.init_db()
        assert parent_dir.exists()
        assert schema_checked["value"] is True
    finally:
        shutil.rmtree(runtime_root, ignore_errors=True)


def test_ensure_schema_is_current_fails_fast_with_upgrade_guidance(monkeypatch):
    class _DummyConnection:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _DummyEngine:
        def connect(self):
            return _DummyConnection()

    monkeypatch.setattr(database_module, "_get_alembic_config", lambda: object())
    monkeypatch.setattr(
        database_module.ScriptDirectory,
        "from_config",
        lambda _config: SimpleNamespace(get_heads=lambda: ("c2f9b7e4a1d3",)),
    )
    monkeypatch.setattr(
        database_module.MigrationContext,
        "configure",
        lambda _connection: SimpleNamespace(get_current_heads=lambda: tuple()),
    )
    monkeypatch.setattr(database_module, "engine", _DummyEngine())

    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        database_module._ensure_schema_is_current()


def test_normalize_database_url_encodes_postgres_password_and_adds_supabase_sslmode():
    normalized = database_module._normalize_database_url(
        "postgresql://postgres:NMVn*A%gCnq59Z3@db.example.supabase.co:5432/postgres"
    )

    assert normalized.startswith("postgresql+psycopg://")
    assert "NMVn%2AA%25gCnq59Z3" in normalized
    assert normalized.endswith("/postgres?sslmode=require")


def test_normalize_database_url_leaves_sqlite_url_unchanged():
    sqlite_url = "sqlite:///db/runtime/dentai_app.db"

    assert database_module._normalize_database_url(sqlite_url) == sqlite_url


def test_connection_guidance_message_flags_supabase_ipv6_direct_connection_issue(monkeypatch):
    monkeypatch.setattr(
        database_module,
        "DATABASE_URL",
        "postgresql+psycopg://postgres:secret@db.example.supabase.co:5432/postgres",
    )

    guidance = database_module._connection_guidance_message(
        RuntimeError("connection to server failed: Network is unreachable")
    )

    assert guidance is not None
    assert "Session pooler" in guidance
    assert "IPv4 add-on" in guidance
