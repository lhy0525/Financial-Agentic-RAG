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

    def execute(self, sql: str, question: str | None = None) -> SQLExecutionResult:
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
        self._log(question=question, result=result)
        return result

    def _log(self, question: str | None, result: SQLExecutionResult) -> None:
        if self.log_db_path is None:
            return
        with sqlite3.connect(self.log_db_path) as con:
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
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            con.execute(
                """
                INSERT INTO sql_query_log
                    (question, sql, status, error, row_count, elapsed_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    question,
                    result.sql,
                    result.status,
                    result.error,
                    result.row_count,
                    result.elapsed_ms,
                ),
            )
            con.commit()
