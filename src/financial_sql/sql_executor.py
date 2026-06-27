from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import sqlite3
import time
from typing import Any


@dataclass(frozen=True)
class SQLExecutionResult:
    status: str
    sql: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    row_count: int = 0
    elapsed_ms: float = 0.0
    error: str | None = None
    db_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SQLiteQueryExecutor:
    def __init__(
        self,
        db_path: str | Path,
        row_cap: int = 100,
        timeout_seconds: float = 10.0,
        log_db_path: str | Path | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.row_cap = row_cap
        self.timeout_seconds = timeout_seconds
        self.log_db_path = Path(log_db_path) if log_db_path is not None else None

    def execute(
        self,
        sql: str,
        question: str | None = None,
        attempt_context: dict[str, Any] | None = None,
    ) -> SQLExecutionResult:
        started = time.perf_counter()
        try:
            with sqlite3.connect(self.db_path, timeout=self.timeout_seconds) as con:
                con.row_factory = sqlite3.Row
                cur = con.execute(sql)
                rows = cur.fetchmany(self.row_cap)
                columns = [description[0] for description in cur.description or []]
                mapped_rows = [dict(row) for row in rows]
            elapsed_ms = (time.perf_counter() - started) * 1000
            status = "success" if mapped_rows else "empty"
            result = SQLExecutionResult(
                status=status,
                sql=sql,
                rows=mapped_rows,
                columns=columns,
                row_count=len(mapped_rows),
                elapsed_ms=elapsed_ms,
                db_path=str(self.db_path),
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            result = SQLExecutionResult(
                status="failed",
                sql=sql,
                elapsed_ms=elapsed_ms,
                error=str(exc),
                db_path=str(self.db_path),
            )
        self._log(question=question, result=result, attempt_context=attempt_context)
        return result

    def _log(
        self,
        question: str | None,
        result: SQLExecutionResult,
        attempt_context: dict[str, Any] | None = None,
    ) -> None:
        if self.log_db_path is None:
            return
        with sqlite3.connect(self.log_db_path) as con:
            self._ensure_log_schema(con)
            attempt_context = attempt_context or {}
            selected = bool(attempt_context.get("selected"))
            selected_statuses = set(attempt_context.get("selected_statuses") or [])
            if result.status in selected_statuses:
                selected = True
            con.execute(
                """
                INSERT INTO sql_query_log
                    (
                        question,
                        sql,
                        status,
                        error,
                        row_count,
                        elapsed_ms,
                        source,
                        attempt_id,
                        parent_attempt_id,
                        failure_code,
                        repair_reason,
                        safety_status,
                        execution_status,
                        selected
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question,
                    result.sql,
                    result.status,
                    result.error,
                    result.row_count,
                    result.elapsed_ms,
                    attempt_context.get("source"),
                    attempt_context.get("attempt_id"),
                    attempt_context.get("parent_attempt_id"),
                    attempt_context.get("failure_code"),
                    attempt_context.get("repair_reason"),
                    attempt_context.get("safety_status"),
                    attempt_context.get("execution_status") or result.status,
                    1 if selected else 0,
                ),
            )
            con.commit()

    def _ensure_log_schema(self, con: sqlite3.Connection) -> None:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS sql_query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                sql TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                row_count INTEGER NOT NULL,
                elapsed_ms REAL NOT NULL,
                source TEXT,
                attempt_id TEXT,
                parent_attempt_id TEXT,
                failure_code TEXT,
                repair_reason TEXT,
                safety_status TEXT,
                execution_status TEXT,
                selected INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing = {row[1] for row in con.execute("PRAGMA table_info(sql_query_log)").fetchall()}
        additions = {
            "source": "TEXT",
            "attempt_id": "TEXT",
            "parent_attempt_id": "TEXT",
            "failure_code": "TEXT",
            "repair_reason": "TEXT",
            "safety_status": "TEXT",
            "execution_status": "TEXT",
            "selected": "INTEGER NOT NULL DEFAULT 0",
        }
        for column, definition in additions.items():
            if column not in existing:
                con.execute(f"ALTER TABLE sql_query_log ADD COLUMN {column} {definition}")
