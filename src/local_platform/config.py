from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.core.settings import DEFAULT_SETTINGS_PATH


@dataclass(frozen=True)
class PlatformConfig:
    sql_db_path: Path | None
    sql_db_path_source: str | None
    ready: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)
    host: str = "127.0.0.1"
    port: int = 8010
    cors_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    prospectus_enabled: bool = False
    upload_dir: Path | None = None
    prospectus_indexing_enabled: bool = True
    prospectus_collection: str = "prospectus_uploads"
    settings_path: Path | None = None


def resolve_platform_config(settings_path: str | Path | None = None) -> PlatformConfig:
    settings_file = Path(settings_path) if settings_path is not None else DEFAULT_SETTINGS_PATH
    if not settings_file.is_absolute():
        settings_file = settings_file.resolve()

    settings = _load_yaml(settings_file)
    platform = settings.get("financial_platform", {})
    if not isinstance(platform, dict):
        platform = {}

    raw_path = os.environ.get("FINANCIAL_DEMO_DB_PATH")
    source = "FINANCIAL_DEMO_DB_PATH" if raw_path else None
    if not raw_path:
        configured = platform.get("sql_db_path")
        if configured:
            raw_path = str(configured)
            source = "config/settings.yaml:financial_platform.sql_db_path"

    db_path = _resolve_db_path(raw_path, settings_file) if raw_path else None
    host = str(platform.get("host") or "127.0.0.1")
    port = int(platform.get("port") or 8010)
    cors_origins = platform.get("cors_origins") or [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    if not isinstance(cors_origins, list):
        cors_origins = [str(cors_origins)]
    upload_dir = _resolve_upload_dir(platform.get("upload_dir"), settings_file)
    prospectus_collection = str(platform.get("prospectus_collection") or "prospectus_uploads").strip()
    if not prospectus_collection:
        prospectus_collection = "prospectus_uploads"

    diagnostics: dict[str, Any] = {
        "missing": [],
        "invalid": [],
        "sql_db_path_source": source,
    }
    if db_path is None:
        diagnostics["missing"].append("sql_db_path")
    elif not db_path.exists() or not db_path.is_file():
        diagnostics["invalid"].append(str(db_path))

    return PlatformConfig(
        sql_db_path=db_path,
        sql_db_path_source=source,
        ready=not diagnostics["missing"] and not diagnostics["invalid"],
        diagnostics=diagnostics,
        host=host,
        port=port,
        cors_origins=[str(origin) for origin in cors_origins],
        prospectus_enabled=bool(platform.get("prospectus_enabled", False)),
        upload_dir=upload_dir,
        prospectus_indexing_enabled=bool(platform.get("prospectus_indexing_enabled", True)),
        prospectus_collection=prospectus_collection,
        settings_path=settings_file,
    )


def _load_yaml(settings_file: Path) -> dict[str, Any]:
    if not settings_file.exists():
        return {}
    with settings_file.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _resolve_db_path(raw_path: str | None, settings_file: Path) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (settings_file.parent / path).resolve()


def _resolve_upload_dir(raw_path: Any, settings_file: Path) -> Path:
    default_path = Path(__file__).resolve().parents[2] / "data" / "local_platform_uploads"
    if not raw_path:
        return default_path
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    return (settings_file.parent / path).resolve()
