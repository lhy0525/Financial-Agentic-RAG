from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from src.agentic.types import Evidence, EvidencePackage
from src.financial_sql.entity_resolver import EntityResolver
from src.financial_sql.formula_registry import FormulaDefinition, FormulaRegistry
from src.financial_sql.schema_registry import FinancialSchemaRegistry
from src.financial_sql.sql_executor import SQLiteQueryExecutor, SQLExecutionResult
from src.financial_sql.sql_safety import SQLSafetyChecker


class SQLCompileError(ValueError):
    def __init__(
        self,
        message: str,
        error_type: str = "compile",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.metadata = metadata or {}


class TextToSQLEvidenceTool:
    def __init__(
        self,
        db_path: str | Path,
        row_limit: int = 100,
        log_db_path: str | Path | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.registry = FinancialSchemaRegistry()
        self.formulas = FormulaRegistry()
        self.resolver = EntityResolver(self.db_path)
        self.safety = SQLSafetyChecker(default_limit=row_limit)
        self.executor = SQLiteQueryExecutor(self.db_path, row_cap=row_limit, log_db_path=log_db_path)

    def query(self, plan: Any, question: str) -> EvidencePackage:
        compile_result = self._compile_with_repair(plan)
        if compile_result["status"] == "failed":
            return self._failed_package(
                question=question,
                error=compile_result["error"],
                error_type=compile_result["error_type"],
                metadata=compile_result,
            )
        sql = compile_result["sql"]
        query_metadata = compile_result["metadata"]
        repair_attempts = compile_result["repair_attempts"]
        repair_errors = compile_result["repair_errors"]

        safety = self.safety.check(sql)
        if not safety.allowed:
            return EvidencePackage(
                path="text_to_sql",
                question=question,
                evidences=[],
                metadata={
                    "status": "failed",
                    "error": f"SQL rejected by safety checker: {safety.reason}",
                    "sql": sql,
                    "db_path": str(self.db_path),
                    "safety": safety.to_dict(),
                    "repair_attempts": repair_attempts,
                    "repair_errors": repair_errors,
                    **query_metadata,
                },
            )

        result = self.executor.execute(safety.sql, question=question)
        metadata = {
            "status": result.status,
            "sql": safety.sql,
            "db_path": str(self.db_path),
            "tables": query_metadata.get("tables", []),
            "columns": result.columns,
            "row_count": result.row_count,
            "rows": result.rows,
            "formula": self._formula_metadata(query_metadata.get("formula")),
            "time_scope": query_metadata.get("time_scope", {}),
            "entity_resolution": query_metadata.get("entity_resolution", []),
            "elapsed_ms": result.elapsed_ms,
            "safety": safety.to_dict(),
            "repair_attempts": repair_attempts,
            "repair_errors": repair_errors,
        }
        result_value_column = query_metadata.get("result_value_column")
        if result_value_column and result.rows:
            first_row = result.rows[0]
            if isinstance(first_row, dict) and result_value_column in first_row:
                metadata["result_value"] = first_row[result_value_column]
        for key in (
            "join_scope",
            "selection_rules",
            "unit_assumptions",
            "price_field_semantics",
            "conversion_rules",
        ):
            if key in query_metadata:
                metadata[key] = query_metadata[key]
        if result.status == "failed":
            return EvidencePackage(
                path="text_to_sql",
                question=question,
                evidences=[],
                metadata={**metadata, "error": result.error},
            )
        if result.status == "empty":
            return EvidencePackage(path="text_to_sql", question=question, evidences=[], metadata=metadata)

        evidence = Evidence(
            evidence_id="sql-1",
            evidence_type="sql_result",
            source_type="db",
            content=json.dumps(result.rows, ensure_ascii=False, default=str),
            source=str(self.db_path),
            metadata=metadata,
        )
        return EvidencePackage(
            path="text_to_sql",
            question=question,
            evidences=[evidence],
            metadata={**metadata, "status": "success"},
        )

    def _compile_with_repair(self, plan: Any) -> dict[str, Any]:
        repair_errors: list[str] = []
        current_plan = plan
        for attempt in range(3):
            try:
                sql, metadata = self._compile(current_plan)
                return {
                    "status": "success",
                    "sql": sql,
                    "metadata": metadata,
                    "repair_attempts": attempt,
                    "repair_errors": repair_errors,
                }
            except SQLCompileError as exc:
                if exc.error_type == "entity_resolution":
                    return {
                        "status": "failed",
                        "error": str(exc),
                        "error_type": exc.error_type,
                        "repair_attempts": 0,
                        "repair_errors": repair_errors,
                        **exc.metadata,
                    }
                if attempt >= 2:
                    return {
                        "status": "failed",
                        "error": str(exc),
                        "error_type": exc.error_type,
                        "repair_attempts": attempt,
                        "repair_errors": repair_errors,
                        **exc.metadata,
                    }
                repair_errors.append(str(exc))
                current_plan = self._repair_plan(current_plan, exc, attempt + 1)
            except Exception as exc:
                if attempt >= 2:
                    return {
                        "status": "failed",
                        "error": str(exc),
                        "error_type": "compile",
                        "repair_attempts": attempt,
                        "repair_errors": repair_errors,
                    }
                repair_errors.append(str(exc))
                current_plan = self._repair_plan(current_plan, exc, attempt + 1)
        raise AssertionError("unreachable")

    def _repair_plan(self, plan: Any, exc: Exception, attempt: int) -> Any:
        return plan

    def _compile(self, plan: Any) -> tuple[str, dict[str, Any]]:
        task_type = self._get(plan, "task_type")
        entities = self._get(plan, "entities", {}) or {}
        time_scope = self._get(plan, "time_scope", {}) or {}
        formula_id = self._get(plan, "formula")
        if task_type == "raw_sql":
            return str(entities["sql"]), {"tables": [], "time_scope": time_scope, "entity_resolution": []}
        if task_type in {"latest_industry_classification", "latest_record_lookup"}:
            return self._compile_latest_industry(entities, time_scope)
        if task_type == "stock_code_lookup":
            return self._compile_stock_code_lookup(entities, time_scope)
        if task_type == "point_lookup":
            return self._compile_stock_point_lookup(entities, time_scope)
        if task_type in {"daily_percent_change", "quote_formula"}:
            return self._compile_quote_formula(entities, time_scope, formula_id, self._get(plan, "formula_params", {}) or {})
        if task_type in {"report_period_holding_ranking", "ranking", "aggregate_statistics", "report_period_query"}:
            return self._compile_holding_ranking(entities, time_scope)
        if task_type == "fund_share_movement":
            return self._compile_fund_share_movement(entities, time_scope)
        if task_type == "bond_holding_ranking":
            return self._compile_bond_holding_ranking(entities, time_scope)
        if task_type == "convertible_bond_industry_aggregation":
            return self._compile_convertible_bond_industry_aggregation(entities, time_scope)
        raise SQLCompileError(f"unsupported task_type: {task_type}")

    def _compile_date_from_scope(self, time_scope: Any, preferred_key: str) -> str | None:
        explicit = self._scope_get(time_scope, preferred_key)
        if explicit:
            return str(explicit)
        value = self._scope_get(time_scope, "value")
        if value and re.fullmatch(r"20\d{6}", str(value)):
            return str(value)
        end = self._scope_get(time_scope, "end")
        return str(end) if end else None

    def _compile_latest_industry(self, entities: dict[str, Any], time_scope: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        stock_code, resolution = self._resolve_stock_entity(entities)
        standard = self.registry.normalize_industry_standard(
            entities.get("industry_standard") or entities.get("industry_standards") or "申万行业分类"
        )
        code = resolution.code or stock_code
        sql = f"""
            SELECT "股票代码", "交易日期", "行业划分标准", "一级行业名称", "二级行业名称"
            FROM "A股公司行业划分表"
            WHERE "股票代码" = '{self._escape(code)}'
              AND "行业划分标准" = '{self._escape(standard)}'
              AND "交易日期" = (
                  SELECT MAX("交易日期")
                  FROM "A股公司行业划分表"
                  WHERE "股票代码" = '{self._escape(code)}'
                    AND "行业划分标准" = '{self._escape(standard)}'
              )
            ORDER BY "交易日期" DESC
        """
        return self._squash(sql), {
            "tables": ["A股公司行业划分表"],
            "time_scope": self._scope_to_dict(time_scope),
            "entity_resolution": [resolution.to_dict()],
        }

    def _compile_stock_code_lookup(self, entities: dict[str, Any], time_scope: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        stock_code, resolution = self._resolve_stock_entity(entities)
        code = resolution.code or stock_code
        sql = f"""
            SELECT DISTINCT "股票代码", "股票名称"
            FROM "基金股票持仓明细"
            WHERE "股票代码" = '{self._escape(code)}'
            ORDER BY "股票名称" ASC
            LIMIT 1
        """
        return self._squash(sql), {
            "tables": ["基金股票持仓明细"],
            "time_scope": self._scope_to_dict(time_scope),
            "entity_resolution": [resolution.to_dict()],
            "result_value_column": "股票代码",
        }

    def _compile_stock_point_lookup(self, entities: dict[str, Any], time_scope: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        stock_code, resolution = self._resolve_stock_entity(entities)
        trading_date = self._compile_date_from_scope(time_scope, "trading_date")
        if not trading_date:
            raise SQLCompileError("trading date is required")
        requested_columns = entities.get("columns") or ["股票代码", "交易日", "收盘价(元)"]
        if isinstance(requested_columns, str):
            requested_columns = [requested_columns]
        allowed = {
            "股票代码",
            "交易日",
            "昨收盘(元)",
            "今开盘(元)",
            "最高价(元)",
            "最低价(元)",
            "收盘价(元)",
            "成交量(股)",
            "成交金额(元)",
        }
        columns = ["股票代码", "交易日"]
        for column in requested_columns:
            normalized = self._normalize_quote_column(str(column))
            if normalized in allowed and normalized not in columns:
                columns.append(normalized)
        selected = ", ".join(f'"{column}"' for column in columns)
        code = resolution.code or stock_code
        sql = f"""
            SELECT {selected}
            FROM "A股票日行情表"
            WHERE "股票代码" = '{self._escape(code)}'
              AND "交易日" = '{self._escape(str(trading_date))}'
        """
        return self._squash(sql), {
            "tables": ["A股票日行情表"],
            "time_scope": self._scope_to_dict(time_scope),
            "entity_resolution": [resolution.to_dict()],
        }

    def _normalize_quote_column(self, value: str) -> str:
        aliases = {
            "鑲＄エ浠ｇ爜": "股票代码",
            "浜ゆ槗鏃?": "交易日",
            "鏄ㄦ敹鐩?鍏?": "昨收盘(元)",
            "浠婂紑鐩?鍏?": "今开盘(元)",
            "鏈€楂樹环(鍏?": "最高价(元)",
            "鏈€浣庝环(鍏?": "最低价(元)",
            "鏀剁洏浠?鍏?": "收盘价(元)",
            "鎴愪氦閲?鑲?": "成交量(股)",
            "鎴愪氦閲戦(鍏?": "成交金额(元)",
        }
        return aliases.get(value.strip(), value.strip())

    def _compile_quote_formula(
        self,
        entities: dict[str, Any],
        time_scope: dict[str, Any],
        formula_id: str | None,
        formula_params: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        if formula_id in {None, "daily_percent_change"}:
            if self._has_industry_scope(entities):
                return self._compile_industry_daily_percent_change_ranking(
                    entities,
                    time_scope,
                    formula_id or "daily_percent_change",
                )
            return self._compile_daily_percent_change(entities, time_scope, formula_id)
        if formula_id == "price_range":
            return self._compile_price_range(entities, time_scope)
        if formula_id in {"open_above_previous_close_days", "low_volume_days", "limit_up_days"}:
            return self._compile_count_formula(entities, time_scope, formula_id, formula_params)
        if formula_id == "annualized_return":
            return self._compile_annualized_return(entities, time_scope)
        raise SQLCompileError(f"registered formula is required: {formula_id}")

    def _compile_industry_daily_percent_change_ranking_legacy(
        self,
        entities: dict[str, Any],
        time_scope: dict[str, Any],
        formula_id: str,
    ) -> tuple[str, dict[str, Any]]:
        trading_date = self._scope_get(time_scope, "value") or self._scope_get(time_scope, "trading_date")
        if not trading_date:
            raise SQLCompileError("trading date is required")
        formula = self.formulas.get(formula_id)
        if formula is None:
            raise SQLCompileError("registered formula is required")
        standard = self.registry.normalize_industry_standard(
            entities.get("industry_standard") or entities.get("industry_standards") or "鐢充竾琛屼笟鍒嗙被"
        )
        level1 = entities.get("level1_industry")
        level2 = entities.get("level2_industry")
        industry_filter = ""
        if level1:
            industry_filter = f'AND industry."涓€绾ц涓氬悕绉?" = \'{self._escape(str(level1))}\''
        elif level2:
            industry_filter = f'AND industry."浜岀骇琛屼笟鍚嶇О" = \'{self._escape(str(level2))}\''
        top_n = self._top_n_from_entities(entities)
        sql = f"""
            SELECT
                quote."鑲＄エ浠ｇ爜",
                quote."浜ゆ槗鏃?",
                industry."琛屼笟鍒掑垎鏍囧噯",
                industry."涓€绾ц涓氬悕绉?",
                industry."浜岀骇琛屴笟鍚嶇О",
                quote."鏄ㄦ敹鐩?鍏?",
                quote."鏀剁洏浠?鍏?",
                ROUND((quote."鏀剁洏浠?鍏?" / quote."鏄ㄦ敹鐩?鍏?" - 1) * 100, 6) AS "{formula.identifier}"
            FROM "A鑲＄エ鏃ヨ鎯呰〃" AS quote
            JOIN "A鑲″叕鍙歌涓氬垝鍒嗚〃" AS industry
              ON quote."鑲＄エ浠ｇ爜" = industry."鑲＄エ浠ｇ爜"
             AND quote."浜ゆ槗鏃?" = industry."浜ゆ槗鏃ユ湡"
            WHERE quote."浜ゆ槗鏃?" = '{self._escape(str(trading_date))}'
              AND industry."琛屴笟鍒掑垎鏍囧噯" = '{self._escape(standard)}'
              {industry_filter}
            ORDER BY "{formula.identifier}" DESC
            LIMIT {top_n}
        """
        return self._squash(sql), {
            "tables": ["A鑲＄エ鏃ヨ鎯呰〃", "A鑲″叕鍙歌涓氬垝鍒嗚〃"],
            "time_scope": self._scope_to_dict(time_scope),
            "formula": formula,
            "entity_resolution": [],
        }

    def _has_industry_scope(self, entities: dict[str, Any]) -> bool:
        return any(
            entities.get(key)
            for key in (
                "industry_standard",
                "industry_standards",
                "level1_industry",
                "level2_industry",
            )
        )

    def _top_n_from_entities(self, entities: dict[str, Any]) -> int:
        raw = entities.get("top_n") or entities.get("limit") or 1
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return 1

    def _compile_industry_daily_percent_change_ranking(
        self,
        entities: dict[str, Any],
        time_scope: dict[str, Any],
        formula_id: str,
    ) -> tuple[str, dict[str, Any]]:
        trading_date = self._scope_get(time_scope, "value") or self._scope_get(time_scope, "trading_date")
        if not trading_date:
            raise SQLCompileError("trading date is required")
        formula = self.formulas.get(formula_id)
        if formula is None:
            raise SQLCompileError("registered formula is required")
        standard = self._normalize_sql_industry_standard(
            entities.get("industry_standard") or entities.get("industry_standards") or "申万行业分类"
        )
        industry_filter = ""
        if entities.get("level1_industry"):
            industry = self._normalize_sql_industry_name(str(entities["level1_industry"]))
            industry_filter = f'AND industry."一级行业名称" = \'{self._escape(industry)}\''
        elif entities.get("level2_industry"):
            industry = self._normalize_sql_industry_name(str(entities["level2_industry"]))
            industry_filter = f'AND industry."二级行业名称" = \'{self._escape(industry)}\''
        top_n = self._top_n_from_entities(entities)
        sql = f"""
            SELECT
                quote."股票代码",
                quote."交易日",
                industry."行业划分标准",
                industry."一级行业名称",
                industry."二级行业名称",
                quote."昨收盘(元)",
                quote."收盘价(元)",
                ROUND((quote."收盘价(元)" / NULLIF(quote."昨收盘(元)", 0) - 1) * 100, 6) AS "{formula.identifier}"
            FROM "A股票日行情表" AS quote
            JOIN "A股公司行业划分表" AS industry
              ON quote."股票代码" = industry."股票代码"
             AND quote."交易日" = industry."交易日期"
            WHERE quote."交易日" = '{self._escape(str(trading_date))}'
              AND industry."行业划分标准" = '{self._escape(standard)}'
              {industry_filter}
            ORDER BY "{formula.identifier}" DESC, quote."股票代码" ASC
            LIMIT {top_n}
        """
        return self._squash(sql), {
            "tables": ["A股票日行情表", "A股公司行业划分表"],
            "time_scope": self._scope_to_dict(time_scope),
            "formula": formula,
            "entity_resolution": [],
            "selection_rules": {
                "tie_breakers": [f"{formula.identifier} DESC", "股票代码 ASC"],
            },
            "price_field_semantics": {
                "daily_percent_change": "收盘价(元) / 昨收盘(元) - 1",
            },
        }

    def _normalize_sql_industry_standard(self, value: str | None) -> str:
        normalized = self.registry.normalize_industry_standard(value) if value is not None else None
        raw = (normalized or value or "").strip()
        if raw in {"申万", "申万行业", "申万行业分类", "鐢充竾", "閻㈠厖绔?"}:
            return "申万行业分类"
        if raw in {"中信", "中信行业", "中信行业分类", "涓俊"}:
            return "中信行业分类"
        return raw

    def _normalize_sql_industry_name(self, value: str) -> str:
        aliases = {
            "鍖栧伐": "化工",
            "閸栨牕浼?": "化工",
            "鐭虫补鐭冲寲": "石油石化",
            "鐭虫补鍖栧伐": "石油化工",
        }
        return aliases.get(value.strip(), value.strip())

    def _compile_daily_percent_change(
        self,
        entities: dict[str, Any],
        time_scope: dict[str, Any],
        formula_id: str | None,
    ) -> tuple[str, dict[str, Any]]:
        stock_code, resolution = self._resolve_stock_entity(entities)
        trading_date = self._scope_get(time_scope, "value") or self._scope_get(time_scope, "trading_date")
        if not trading_date:
            raise SQLCompileError("trading date is required")
        formula = self.formulas.get(formula_id or "daily_percent_change")
        if formula is None:
            raise SQLCompileError("registered formula is required")
        code = resolution.code or stock_code
        sql = f"""
            SELECT
                "股票代码",
                "交易日",
                "昨收盘(元)",
                "收盘价(元)",
                ROUND((("收盘价(元)" / NULLIF("昨收盘(元)", 0)) - 1) * 100, 6) AS "{formula.identifier}"
            FROM "A股票日行情表"
            WHERE "股票代码" = '{self._escape(code)}'
              AND "交易日" = '{self._escape(str(trading_date))}'
        """
        return self._squash(sql), {
            "tables": ["A股票日行情表"],
            "time_scope": self._scope_to_dict(time_scope),
            "formula": formula,
            "entity_resolution": [resolution.to_dict()],
        }

    def _compile_price_range(self, entities: dict[str, Any], time_scope: Any) -> tuple[str, dict[str, Any]]:
        stock_code, resolution = self._resolve_stock_entity(entities)
        trading_date = self._scope_get(time_scope, "value") or self._scope_get(time_scope, "trading_date")
        if not trading_date:
            raise SQLCompileError("trading date is required")
        formula = self.formulas.get("price_range")
        sql = f"""
            SELECT "股票代码", "交易日", "最高价(元)", "最低价(元)",
                   ROUND({formula.sql_expression}, 6) AS "price_range"
            FROM "A股票日行情表"
            WHERE "股票代码" = '{self._escape(stock_code)}'
              AND "交易日" = '{self._escape(str(trading_date))}'
        """
        return self._squash(sql), {
            "tables": ["A股票日行情表"],
            "time_scope": self._scope_to_dict(time_scope),
            "formula": formula,
            "entity_resolution": [resolution.to_dict()],
        }

    def _compile_count_formula(
        self,
        entities: dict[str, Any],
        time_scope: Any,
        formula_id: str,
        formula_params: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        stock_code, resolution = self._resolve_stock_entity(entities)
        start, end = self._date_range(time_scope)
        formula = self.formulas.get(formula_id)
        if formula_id == "open_above_previous_close_days":
            condition = '"今开盘(元)" > "昨收盘(元)"'
        elif formula_id == "limit_up_days":
            threshold = formula_params.get("threshold", formula.default_threshold or 0.098)
            condition = f'(("收盘价(元)" / "昨收盘(元)") - 1) >= {float(threshold)}'
        elif formula_id == "low_volume_days":
            condition = f"""
                "成交量(股)" < (
                    SELECT AVG("成交量(股)")
                    FROM "A股票日行情表"
                    WHERE "股票代码" = '{self._escape(stock_code)}'
                      AND "交易日" BETWEEN '{self._escape(start)}' AND '{self._escape(end)}'
                )
            """
        else:
            raise SQLCompileError(f"unsupported count formula: {formula_id}")
        sql = f"""
            SELECT COUNT(*) AS "{formula_id}"
            FROM "A股票日行情表"
            WHERE "股票代码" = '{self._escape(stock_code)}'
              AND "交易日" BETWEEN '{self._escape(start)}' AND '{self._escape(end)}'
              AND {condition}
        """
        return self._squash(sql), {
            "tables": ["A股票日行情表"],
            "time_scope": self._scope_to_dict(time_scope),
            "formula": formula,
            "entity_resolution": [resolution.to_dict()],
        }

    def _compile_annualized_return(self, entities: dict[str, Any], time_scope: Any) -> tuple[str, dict[str, Any]]:
        stock_code, resolution = self._resolve_stock_entity(entities)
        start, end = self._date_range(time_scope)
        formula = self.formulas.get("annualized_return")
        code = self._escape(stock_code)
        sql = f"""
            SELECT
                '{code}' AS "股票代码",
                ROUND((
                    (
                        SELECT "收盘价(元)" FROM "A股票日行情表"
                        WHERE "股票代码" = '{code}' AND "交易日" BETWEEN '{self._escape(start)}' AND '{self._escape(end)}'
                        ORDER BY "交易日" DESC LIMIT 1
                    ) / NULLIF((
                        SELECT "今开盘(元)" FROM "A股票日行情表"
                        WHERE "股票代码" = '{code}' AND "交易日" BETWEEN '{self._escape(start)}' AND '{self._escape(end)}'
                        ORDER BY "交易日" ASC LIMIT 1
                    ), 0) - 1
                ) * 100, 6) AS "annualized_return"
        """
        return self._squash(sql), {
            "tables": ["A股票日行情表"],
            "time_scope": self._scope_to_dict(time_scope),
            "formula": formula,
            "entity_resolution": [resolution.to_dict()],
        }

    def _compile_holding_ranking(self, entities: dict[str, Any], time_scope: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if self._scope_get(time_scope, "per_entity_latest") and len(self._as_list(entities.get("fund_codes"))) > 1:
            return self._compile_multi_fund_latest_holding_ranking(entities, time_scope)
        fund_code, resolution = self._resolve_fund_entity(entities)
        holding_date = self._compile_date_from_scope(time_scope, "holding_date")
        if holding_date and not str(holding_date).isdigit():
            holding_date = self._scope_get(time_scope, "end")
        report_types = self._scope_get(time_scope, "report_types") or []
        top_n = int(entities.get("top_n", 10))
        code = resolution.code or fund_code
        report_filter = self._report_type_filter(report_types)
        date_filter = f'AND "持仓日期" = \'{self._escape(str(holding_date))}\''
        per_entity_latest = bool(self._scope_get(time_scope, "per_entity_latest"))
        if per_entity_latest:
            start = self._scope_get(time_scope, "start") or ""
            end = self._scope_get(time_scope, "end") or "99999999"
            date_filter = f"""
                AND "持仓日期" = (
                    SELECT MAX("持仓日期")
                    FROM "基金股票持仓明细"
                    WHERE "基金代码" = '{self._escape(code)}'
                      AND "持仓日期" BETWEEN '{self._escape(str(start))}' AND '{self._escape(str(end))}'
                      {report_filter}
                )
            """
        elif not holding_date:
            raise SQLCompileError("holding date is required")
        sql = f"""
            SELECT "基金代码", "基金简称", "持仓日期", "股票代码", "股票名称",
                   "市值", "市值占基金资产净值比", "第N大重仓股", "报告类型"
            FROM "基金股票持仓明细"
            WHERE "基金代码" = '{self._escape(code)}'
              {date_filter}
              {report_filter}
            ORDER BY "第N大重仓股" ASC, "股票代码" ASC
            LIMIT {top_n}
        """
        return self._squash(sql), {
            "tables": ["基金股票持仓明细"],
            "time_scope": self._scope_to_dict(time_scope),
            "entity_resolution": [resolution.to_dict()],
            "selection_rules": {
                "per_entity_latest": per_entity_latest,
                "tie_breakers": ["第N大重仓股", "股票代码"],
                "report_type_filter": self._expanded_report_types(report_types),
            },
        }

    def _compile_multi_fund_latest_holding_ranking(
        self, entities: dict[str, Any], time_scope: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        fund_codes, resolutions = self._resolve_fund_entities(entities)
        if not fund_codes:
            raise SQLCompileError("fund code is required")
        start = self._scope_get(time_scope, "start") or ""
        end = self._scope_get(time_scope, "end") or "99999999"
        report_types = self._scope_get(time_scope, "report_types") or []
        report_filter = self._report_type_filter(report_types, alias="h")
        latest_report_filter = self._report_type_filter(report_types)
        quoted_codes = ", ".join(f"'{self._escape(code)}'" for code in fund_codes)
        top_n = int(entities.get("top_n", 10))
        sql = f"""
            SELECT
                h."基金代码",
                h."基金简称",
                h."持仓日期",
                h."股票代码",
                h."股票名称",
                h."市值",
                h."市值占基金资产净值比",
                h."第N大重仓股",
                h."报告类型"
            FROM "基金股票持仓明细" AS h
            WHERE h."基金代码" IN ({quoted_codes})
              AND h."持仓日期" = (
                  SELECT MAX("持仓日期")
                  FROM "基金股票持仓明细"
                  WHERE "基金代码" = h."基金代码"
                    AND "持仓日期" BETWEEN '{self._escape(str(start))}' AND '{self._escape(str(end))}'
                    {latest_report_filter}
              )
              {report_filter}
            ORDER BY h."基金代码" ASC, h."第N大重仓股" ASC, h."股票代码" ASC
            LIMIT {top_n * len(fund_codes)}
        """
        return self._squash(sql), {
            "tables": ["基金股票持仓明细"],
            "time_scope": self._scope_to_dict(time_scope),
            "entity_resolution": [resolution.to_dict() for resolution in resolutions],
            "selection_rules": {
                "per_entity_latest": True,
                "tie_breakers": ["基金代码", "第N大重仓股", "股票代码"],
                "report_type_filter": self._expanded_report_types(report_types),
            },
        }

    def _compile_fund_share_movement(self, entities: dict[str, Any], time_scope: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        fund_code, resolution = self._resolve_fund_entity(entities)
        start, end = self._date_range(time_scope)
        code = resolution.code or fund_code
        report_filter = self._report_type_filter(self._scope_get(time_scope, "report_types") or [])
        sql = f"""
            SELECT
                "基金代码",
                "基金简称",
                "截止日期",
                "报告期期初基金总份额",
                "报告期基金总申购份额",
                "报告期基金总赎回份额",
                "报告期期末基金总份额",
                ("报告期基金总申购份额" - "报告期基金总赎回份额") AS "net_share_change",
                "报告类型"
            FROM "基金规模变动表"
            WHERE "基金代码" = '{self._escape(code)}'
              AND "截止日期" BETWEEN '{self._escape(start)}' AND '{self._escape(end)}'
              {report_filter}
            ORDER BY "截止日期" DESC
            LIMIT 1
        """
        return self._squash(sql), {
            "tables": ["基金规模变动表"],
            "time_scope": self._scope_to_dict(time_scope),
            "entity_resolution": [resolution.to_dict()],
            "unit_assumptions": {"share_fields": "份"},
            "selection_rules": {"record_selection": "latest 截止日期 within requested report period"},
        }

    def _compile_bond_holding_ranking(self, entities: dict[str, Any], time_scope: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        fund_code, resolution = self._resolve_fund_entity(entities)
        holding_date = self._compile_date_from_scope(time_scope, "holding_date")
        if not holding_date:
            raise SQLCompileError("holding date is required")
        code = resolution.code or fund_code
        report_filter = self._report_type_filter(self._scope_get(time_scope, "report_types") or [])
        top_n = int(entities.get("top_n", 10))
        sql = f"""
            SELECT
                "基金代码",
                "基金简称",
                "持仓日期",
                "债券类型",
                "债券名称",
                "持债数量",
                "持债市值",
                "持债市值占基金资产净值比",
                "第N大重仓股",
                "报告类型"
            FROM "基金债券持仓明细"
            WHERE "基金代码" = '{self._escape(code)}'
              AND "持仓日期" = '{self._escape(str(holding_date))}'
              {report_filter}
            ORDER BY "第N大重仓股" ASC, "债券名称" ASC
            LIMIT {top_n}
        """
        return self._squash(sql), {
            "tables": ["基金债券持仓明细"],
            "time_scope": self._scope_to_dict(time_scope),
            "entity_resolution": [resolution.to_dict()],
            "selection_rules": {"tie_breakers": ["第N大重仓股", "债券名称"]},
            "unit_assumptions": {"market_value": "元"},
        }

    def _compile_convertible_bond_industry_aggregation(self, entities: dict[str, Any], time_scope: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        fund_code, resolution = self._resolve_fund_entity(entities)
        holding_date = self._compile_date_from_scope(time_scope, "holding_date")
        if not holding_date:
            raise SQLCompileError("holding date is required")
        code = resolution.code or fund_code
        standard = self._normalize_sql_industry_standard(
            entities.get("industry_standard") or entities.get("industry_standards") or "申万行业分类"
        )
        report_filter = self._report_type_filter(self._scope_get(time_scope, "report_types") or [], alias="cb")
        self._validate_convertible_industry_join_scope(code, str(holding_date), standard, report_filter)
        sql = f"""
            SELECT
                industry."一级行业名称",
                SUM(cb."市值") AS "convertible_bond_market_value",
                COUNT(*) AS "holding_count"
            FROM "基金可转债持仓明细" AS cb
            JOIN "A股公司行业划分表" AS industry
              ON cb."对应股票代码" = industry."股票代码"
             AND cb."持仓日期" = industry."交易日期"
            WHERE cb."基金代码" = '{self._escape(code)}'
              AND cb."持仓日期" = '{self._escape(str(holding_date))}'
              AND industry."行业划分标准" = '{self._escape(standard)}'
              {report_filter}
            GROUP BY industry."一级行业名称"
            ORDER BY "convertible_bond_market_value" DESC, industry."一级行业名称" ASC
        """
        return self._squash(sql), {
            "tables": ["基金可转债持仓明细", "A股公司行业划分表"],
            "time_scope": self._scope_to_dict(time_scope),
            "entity_resolution": [resolution.to_dict()],
            "join_scope": {
                "join": "convertible_industry",
                "keys": ["对应股票代码=股票代码", "持仓日期=交易日期"],
            },
            "unit_assumptions": {"market_value": "元"},
        }

    def _validate_convertible_industry_join_scope(
        self,
        fund_code: str,
        holding_date: str,
        industry_standard: str,
        report_filter: str,
    ) -> None:
        sql = f"""
            SELECT cb.rowid, cb."对应股票代码", COUNT(industry.rowid) AS industry_matches
            FROM "基金可转债持仓明细" AS cb
            LEFT JOIN "A股公司行业划分表" AS industry
              ON cb."对应股票代码" = industry."股票代码"
             AND cb."持仓日期" = industry."交易日期"
             AND industry."行业划分标准" = ?
            WHERE cb."基金代码" = ?
              AND cb."持仓日期" = ?
              {report_filter}
            GROUP BY cb.rowid, cb."对应股票代码"
        """
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute(sql, (industry_standard, fund_code, holding_date)).fetchall()
        ambiguous = [row[1] for row in rows if row[2] > 1]
        lossy = [row[1] for row in rows if row[2] == 0]
        if ambiguous:
            raise SQLCompileError(
                f"ambiguous convertible_industry join for stock codes: {', '.join(ambiguous)}",
                error_type="join_scope",
                metadata={
                    "join_scope": {
                        "join": "convertible_industry",
                        "status": "ambiguous",
                        "stock_codes": ambiguous,
                    }
                },
            )
        if lossy:
            raise SQLCompileError(
                f"lossy convertible_industry join for stock codes: {', '.join(lossy)}",
                error_type="join_scope",
                metadata={
                    "join_scope": {
                        "join": "convertible_industry",
                        "status": "lossy",
                        "stock_codes": lossy,
                    }
                },
            )

    def _resolve_stock_entity(self, entities: dict[str, Any]):
        stock_code = self._first(entities.get("stock_codes") or entities.get("stock_code"))
        if stock_code:
            resolution = self.resolver.resolve_stock(str(stock_code))
            return resolution.code or str(stock_code), resolution
        stock_name = self._first(entities.get("stock_names") or entities.get("stock_name"))
        if stock_name and entities.get("stock_names_require_lookup"):
            resolution = self.resolver.resolve_stock(str(stock_name))
            if resolution.status != "matched" or not resolution.code:
                raise SQLCompileError(
                    f"stock entity resolution failed: {resolution.status}",
                    error_type="entity_resolution",
                    metadata={"entity_resolution": [resolution.to_dict()]},
                )
            return resolution.code, resolution
        raise SQLCompileError("stock code is required")

    def _resolve_fund_entity(self, entities: dict[str, Any]):
        fund_code = self._first(entities.get("fund_codes") or entities.get("fund_code"))
        if fund_code:
            resolution = self.resolver.resolve_fund(str(fund_code))
            return resolution.code or str(fund_code), resolution
        fund_name = self._first(entities.get("fund_names") or entities.get("fund_name"))
        if fund_name and entities.get("fund_names_require_lookup"):
            resolution = self.resolver.resolve_fund(str(fund_name))
            if resolution.status != "matched" or not resolution.code:
                raise SQLCompileError(
                    f"fund entity resolution failed: {resolution.status}",
                    error_type="entity_resolution",
                    metadata={"entity_resolution": [resolution.to_dict()]},
                )
            return resolution.code, resolution
        raise SQLCompileError("fund code is required")

    def _resolve_fund_entities(self, entities: dict[str, Any]) -> tuple[list[str], list[Any]]:
        codes = [str(item) for item in self._as_list(entities.get("fund_codes") or entities.get("fund_code"))]
        if codes:
            resolutions = [self.resolver.resolve_fund(code) for code in codes]
            return [resolution.code or code for code, resolution in zip(codes, resolutions)], resolutions
        fund_names = self._as_list(entities.get("fund_names") or entities.get("fund_name"))
        if fund_names and entities.get("fund_names_require_lookup"):
            resolved_codes: list[str] = []
            resolutions = []
            for fund_name in fund_names:
                resolution = self.resolver.resolve_fund(str(fund_name))
                resolutions.append(resolution)
                if resolution.status != "matched" or not resolution.code:
                    raise SQLCompileError(
                        f"fund entity resolution failed: {resolution.status}",
                        error_type="entity_resolution",
                        metadata={"entity_resolution": [item.to_dict() for item in resolutions]},
                    )
                resolved_codes.append(resolution.code)
            return resolved_codes, resolutions
        return [], []

    def _report_type_filter(self, report_types: list[Any], alias: str | None = None) -> str:
        expanded = self._expanded_report_types(report_types)
        if not expanded:
            return ""
        quoted_types = ", ".join(f"'{self._escape(item)}'" for item in expanded)
        column = f'{alias}."报告类型"' if alias else '"报告类型"'
        return f"AND {column} IN ({quoted_types})"

    def _expanded_report_types(self, report_types: list[Any]) -> list[str]:
        expanded: list[str] = []
        for item in report_types:
            text = str(item)
            if text == "定期报告":
                expanded.extend(["年报", "半年度报告", "季报"])
            elif text == "年度含半年度":
                expanded.extend(["年报", "半年度报告"])
            else:
                expanded.append(text)
        return expanded

    def _date_range(self, time_scope: Any) -> tuple[str, str]:
        start = self._scope_get(time_scope, "start")
        end = self._scope_get(time_scope, "end")
        year = self._scope_get(time_scope, "value")
        if not start and year:
            start = f"{year}0101"
        if not end and year:
            end = f"{year}1231"
        if not start or not end:
            raise SQLCompileError("date range is required")
        return str(start), str(end)

    def _failed_package(
        self,
        question: str,
        error: str,
        error_type: str = "compile",
        metadata: dict[str, Any] | None = None,
    ) -> EvidencePackage:
        payload = {
            "status": "failed",
            "error": error,
            "error_type": error_type,
            "db_path": str(self.db_path),
            "repair_attempts": 0,
            "repair_errors": [],
        }
        if metadata:
            payload.update(metadata)
        return EvidencePackage(
            path="text_to_sql",
            question=question,
            evidences=[],
            metadata=payload,
        )

    def _formula_metadata(self, formula: FormulaDefinition | None) -> dict[str, Any] | None:
        if formula is None:
            return None
        return asdict(formula)

    def _get(self, plan: Any, key: str, default: Any = None) -> Any:
        if isinstance(plan, dict):
            return plan.get(key, default)
        return getattr(plan, key, default)

    def _scope_get(self, time_scope: Any, key: str, default: Any = None) -> Any:
        if isinstance(time_scope, dict):
            return time_scope.get(key, default)
        return getattr(time_scope, key, default)

    def _scope_to_dict(self, time_scope: Any) -> dict[str, Any]:
        if isinstance(time_scope, dict):
            return dict(time_scope)
        if hasattr(time_scope, "to_dict"):
            return time_scope.to_dict()
        return dict(time_scope or {})

    def _first(self, value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            return value[0] if value else None
        return value

    def _as_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value]

    def _escape(self, value: str) -> str:
        return value.replace("'", "''")

    def _squash(self, sql: str) -> str:
        return " ".join(sql.split())
