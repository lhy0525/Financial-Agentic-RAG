from __future__ import annotations

import sqlite3

from src.local_platform.config import resolve_platform_config


def test_database_path_prefers_environment_over_settings(tmp_path, monkeypatch):
    env_db = tmp_path / "env.db"
    settings_db = tmp_path / "settings.db"
    sqlite3.connect(env_db).close()
    sqlite3.connect(settings_db).close()
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(
        "financial_platform:\n"
        f"  sql_db_path: {settings_db.as_posix()}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FINANCIAL_DEMO_DB_PATH", str(env_db))

    config = resolve_platform_config(settings_path=settings_file)

    assert config.sql_db_path == env_db
    assert config.sql_db_path_source == "FINANCIAL_DEMO_DB_PATH"
    assert config.ready is True


def test_database_path_uses_financial_platform_settings_when_env_missing(tmp_path, monkeypatch):
    settings_db = tmp_path / "settings.db"
    sqlite3.connect(settings_db).close()
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(
        "financial_platform:\n"
        f"  sql_db_path: {settings_db.name}\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("FINANCIAL_DEMO_DB_PATH", raising=False)

    config = resolve_platform_config(settings_path=settings_file)

    assert config.sql_db_path == settings_db
    assert config.sql_db_path_source == "config/settings.yaml:financial_platform.sql_db_path"
    assert config.ready is True


def test_missing_database_path_reports_readiness_failure(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text("financial_platform: {}\n", encoding="utf-8")
    monkeypatch.delenv("FINANCIAL_DEMO_DB_PATH", raising=False)

    config = resolve_platform_config(settings_path=settings_file)

    assert config.sql_db_path is None
    assert config.ready is False
    assert config.diagnostics["missing"] == ["sql_db_path"]


def test_invalid_database_path_reports_readiness_failure(tmp_path, monkeypatch):
    missing_db = tmp_path / "missing.db"
    monkeypatch.setenv("FINANCIAL_DEMO_DB_PATH", str(missing_db))

    config = resolve_platform_config(settings_path=tmp_path / "absent.yaml")

    assert config.sql_db_path == missing_db
    assert config.ready is False
    assert config.diagnostics["invalid"] == [str(missing_db)]


def test_platform_config_has_local_host_and_dev_cors_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("FINANCIAL_DEMO_DB_PATH", raising=False)

    config = resolve_platform_config(settings_path=tmp_path / "absent.yaml")

    assert config.host == "127.0.0.1"
    assert config.port == 8010
    assert config.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_platform_config_has_repo_local_upload_dir_default(tmp_path, monkeypatch):
    monkeypatch.delenv("FINANCIAL_DEMO_DB_PATH", raising=False)

    config = resolve_platform_config(settings_path=tmp_path / "absent.yaml")

    assert config.upload_dir.name == "local_platform_uploads"
    assert config.upload_dir.parent.name == "data"


def test_platform_config_has_prospectus_indexing_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("FINANCIAL_DEMO_DB_PATH", raising=False)

    config = resolve_platform_config(settings_path=tmp_path / "absent.yaml")

    assert config.prospectus_collection == "prospectus_uploads"
    assert config.prospectus_indexing_enabled is True


def test_platform_config_reads_prospectus_collection_and_indexing_flag(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(
        "financial_platform:\n"
        "  prospectus_collection: local_prospectus\n"
        "  prospectus_indexing_enabled: false\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("FINANCIAL_DEMO_DB_PATH", raising=False)

    config = resolve_platform_config(settings_path=settings_file)

    assert config.prospectus_collection == "local_prospectus"
    assert config.prospectus_indexing_enabled is False
    assert config.settings_path == settings_file
