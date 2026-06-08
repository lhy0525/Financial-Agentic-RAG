from __future__ import annotations

from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class SQLSafetyResult:
    allowed: bool
    sql: str
    reason: str | None = None
    applied_limit: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class SQLSafetyChecker:
    def __init__(self, default_limit: int = 100) -> None:
        self.default_limit = default_limit
        self._unsafe_pattern = re.compile(
            r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|vacuum|reindex)\b",
            re.IGNORECASE,
        )

    def check(self, sql: str) -> SQLSafetyResult:
        stripped = sql.strip()
        if not stripped:
            return SQLSafetyResult(False, stripped, "SQL is empty")
        if ";" in stripped:
            return SQLSafetyResult(False, stripped, "Statement separators are not allowed")
        if "--" in stripped or "/*" in stripped or "*/" in stripped:
            return SQLSafetyResult(False, stripped, "SQL comments are not allowed")
        if self._unsafe_pattern.search(stripped):
            return SQLSafetyResult(False, stripped, "Write, DDL, and administrative SQL are not allowed")
        if not re.match(r"^\s*select\b", stripped, re.IGNORECASE):
            return SQLSafetyResult(False, stripped, "Only SELECT statements are allowed")
        if self._has_limit(stripped) or self._is_aggregate_only(stripped):
            return SQLSafetyResult(True, stripped)
        limited = f"{stripped} LIMIT {self.default_limit}"
        return SQLSafetyResult(True, limited, applied_limit=self.default_limit)

    def _has_limit(self, sql: str) -> bool:
        return re.search(r"\blimit\s+\d+\s*$", sql, re.IGNORECASE) is not None

    def _is_aggregate_only(self, sql: str) -> bool:
        select_match = re.match(r"^\s*select\s+(.*?)\s+from\s+", sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return False
        select_list = select_match.group(1).strip()
        if "," in select_list:
            return False
        return re.match(r"^(count|sum|avg|min|max)\s*\(", select_list, re.IGNORECASE) is not None
