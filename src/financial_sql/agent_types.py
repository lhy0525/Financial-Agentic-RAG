from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


SQLSource = Literal["rule", "lora", "api", "repair"]
SQLFailureCode = Literal[
    "compile_failed",
    "unsafe_sql",
    "execution_error",
    "empty_result",
    "repair_exhausted",
    "source_disabled",
    "source_unavailable",
    "all_candidates_failed",
]
AcceptedResultKind = Literal["rows", "empty"]


FAILURE_CODES: frozenset[str] = frozenset(
    {
        "compile_failed",
        "unsafe_sql",
        "execution_error",
        "empty_result",
        "repair_exhausted",
        "source_disabled",
        "source_unavailable",
        "all_candidates_failed",
    }
)


@dataclass(frozen=True)
class TextToSQLAgentConfig:
    enable_lora_fallback: bool = False
    lora_endpoint: str | None = None
    enable_api_fallback: bool = False
    api_model: str | None = None
    api_endpoint: str | None = None
    api_key: str | None = None
    sql_examples_path: Path | None = None
    sql_examples_top_k: int = 3
    enable_empty_result_repair: bool = False
    max_repair_attempts: int = 2


@dataclass(frozen=True)
class SQLCandidate:
    source: SQLSource
    sql: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SQLAttempt:
    attempt_id: str
    source: SQLSource
    sql: str | None
    status: str
    failure_code: SQLFailureCode | None = None
    parent_attempt_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteOutcome:
    accepted_result_kind: AcceptedResultKind | None
    failure_code: SQLFailureCode | None
    should_fallback: bool
    fallback_eligibility_reason: str
