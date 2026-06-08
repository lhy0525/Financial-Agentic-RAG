from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
import sqlite3
from typing import Any


@dataclass(frozen=True)
class EntityResolutionResult:
    entity_type: str
    query: str
    status: str
    code: str | None = None
    name: str | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EntityResolver:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else None

    def resolve_stock(self, value: str) -> EntityResolutionResult:
        query = value.strip()
        if self._looks_like_stock_code(query):
            return EntityResolutionResult(
                entity_type="stock",
                query=query,
                status="matched",
                code=query,
                metadata={"resolution_strategy": "direct_code"},
            )
        candidates = self._search_stock_candidates(query)
        return self._result_from_candidates("stock", query, candidates, ["基金股票持仓明细", "A股公司行业划分表"])

    def resolve_fund(self, value: str) -> EntityResolutionResult:
        query = value.strip()
        if self._looks_like_fund_code(query):
            return EntityResolutionResult(
                entity_type="fund",
                query=query,
                status="matched",
                code=query,
                metadata={"resolution_strategy": "direct_code"},
            )
        candidates = self._search_fund_candidates(query)
        return self._result_from_candidates("fund", query, candidates, ["基金基本信息"])

    def _result_from_candidates(
        self,
        entity_type: str,
        query: str,
        candidates: list[dict[str, Any]],
        searched_tables: list[str],
    ) -> EntityResolutionResult:
        metadata = {"searched_tables": searched_tables}
        if not candidates:
            return EntityResolutionResult(entity_type, query, "no_match", metadata=metadata)
        unique_codes = {candidate["code"] for candidate in candidates}
        if len(unique_codes) == 1:
            candidate = candidates[0]
            return EntityResolutionResult(
                entity_type=entity_type,
                query=query,
                status="matched",
                code=candidate["code"],
                name=candidate.get("name"),
                candidates=candidates,
                metadata={**metadata, "resolution_strategy": "sqlite_alias"},
            )
        return EntityResolutionResult(
            entity_type=entity_type,
            query=query,
            status="ambiguous",
            candidates=candidates,
            metadata=metadata,
        )

    def _search_stock_candidates(self, query: str) -> list[dict[str, Any]]:
        if self.db_path is None or not self.db_path.exists():
            return []
        searches = [
            ("基金股票持仓明细", "股票代码", "股票名称"),
            ("基金可转债持仓明细", "对应股票代码", "债券名称"),
            ("A股公司行业划分表", "股票代码", None),
        ]
        return self._search_candidates(query, searches)

    def _search_fund_candidates(self, query: str) -> list[dict[str, Any]]:
        if self.db_path is None or not self.db_path.exists():
            return []
        return self._search_candidates(query, [("基金基本信息", "基金代码", "基金简称", "基金全称")])

    def _search_candidates(self, query: str, searches: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        with sqlite3.connect(self.db_path) as con:
            for item in searches:
                table = item[0]
                if not self._table_exists(con, table):
                    continue
                code_column = item[1]
                name_columns = [column for column in item[2:] if column]
                where_parts = [f'"{code_column}" LIKE ?']
                where_parts.extend(f'"{column}" LIKE ?' for column in name_columns)
                columns = [code_column, *name_columns]
                sql = (
                    f'SELECT DISTINCT {", ".join(self._quote(column) for column in columns)} '
                    f'FROM "{table}" WHERE {" OR ".join(where_parts)} LIMIT 20'
                )
                params = [f"%{query}%"] * len(where_parts)
                for row in con.execute(sql, params):
                    code = str(row[0])
                    name = next((str(value) for value in row[1:] if value), None)
                    candidates.setdefault(code, {"code": code, "name": name, "table": table})
                for candidate in self._contained_name_candidates(con, table, code_column, name_columns, query):
                    candidates.setdefault(candidate["code"], candidate)
        return list(candidates.values())

    def _contained_name_candidates(
        self,
        con: sqlite3.Connection,
        table: str,
        code_column: str,
        name_columns: list[str],
        query: str,
    ) -> list[dict[str, Any]]:
        if not name_columns or len(query) < 4:
            return []
        selected = ", ".join(self._quote(column) for column in [code_column, *name_columns])
        sql = f'SELECT DISTINCT {selected} FROM "{table}" LIMIT 5000'
        matches: dict[str, dict[str, Any]] = {}
        for row in con.execute(sql):
            code = str(row[0])
            for value in row[1:]:
                if not value:
                    continue
                name = str(value)
                if len(name) >= 4 and name in query:
                    matches.setdefault(code, {"code": code, "name": name, "table": table})
        return list(matches.values())

    def _table_exists(self, con: sqlite3.Connection, table: str) -> bool:
        row = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None

    def _quote(self, identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def _looks_like_stock_code(self, value: str) -> bool:
        return bool(re.fullmatch(r"\d{6}|[A-Za-z0-9]{1,6}\s*HK", value))

    def _looks_like_fund_code(self, value: str) -> bool:
        return bool(re.fullmatch(r"\d{6}", value))
