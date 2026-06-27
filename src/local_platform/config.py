from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.core.settings import DEFAULT_SETTINGS_PATH
from src.financial_sql.agent_types import TextToSQLAgentConfig


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
    text2sql_agent: TextToSQLAgentConfig = field(default_factory=TextToSQLAgentConfig)


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
    text2sql_agent = _resolve_text2sql_agent_config(platform.get("text2sql_agent"), settings_file)

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
        text2sql_agent=text2sql_agent,
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


def _resolve_text2sql_agent_config(raw_config: Any, settings_file: Path) -> TextToSQLAgentConfig:
    if not isinstance(raw_config, dict):
        raw_config = {}
    return TextToSQLAgentConfig(
        enable_lora_fallback=_as_bool(raw_config.get("enable_lora_fallback"), default=False),
        lora_endpoint=_as_optional_str(raw_config.get("lora_endpoint")),
        enable_api_fallback=_as_bool(raw_config.get("enable_api_fallback"), default=False),
        api_model=_as_optional_str(raw_config.get("api_model")),
        api_endpoint=_as_optional_str(raw_config.get("api_endpoint")),
        api_key=_as_optional_str(raw_config.get("api_key")),
        sql_examples_path=_resolve_optional_path(raw_config.get("sql_examples_path"), settings_file),
        sql_examples_top_k=_as_int(raw_config.get("sql_examples_top_k"), default=3, minimum=0),
        enable_empty_result_repair=_as_bool(raw_config.get("enable_empty_result_repair"), default=False),
        max_repair_attempts=_as_int(raw_config.get("max_repair_attempts"), default=2, minimum=0),
    )


def _resolve_optional_path(raw_path: Any, settings_file: Path) -> Path | None:
    text = _as_optional_str(raw_path)
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    return (settings_file.parent / path).resolve()


def _as_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any, *, default: int, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed
