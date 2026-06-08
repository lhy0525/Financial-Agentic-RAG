from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.agentic.types import AnswerConstraints, Evidence, QuestionPlan, VerificationReport


class FinancialVerifier:
    """Deterministic sufficiency, source-priority, numeric, and formatting checks."""

    def verify(self, plan: QuestionPlan, evidences: list[Evidence]) -> VerificationReport:
        if not evidences:
            return VerificationReport(
                status="insufficient",
                selected_evidence_ids=[],
                conflicts=[],
                missing_evidence=self._required_missing(plan),
                notes=["No evidence returned"],
            )

        missing = self._missing_evidence(plan, evidences)
        conflicts = self._fact_conflicts(evidences)
        notes: list[str] = []
        selected = list(evidences)

        preference = self._source_preference(plan)
        if conflicts and preference:
            preferred = self._preferred_evidence(evidences, preference)
            if preferred:
                selected = preferred
                conflicts = []
                notes.append(f"Applied {preference} source priority to conflicting facts")

        formula_conflicts = self._formula_conflicts(evidences)
        conflicts.extend(formula_conflicts)
        conflicts.extend(self._metadata_consistency_conflicts(plan, evidences))

        raw_table_missing = self._raw_table_missing(plan, evidences)
        if raw_table_missing and "raw_table" not in missing:
            missing.append("raw_table")
            notes.append("Retrieved table placeholder but raw table payload is unavailable")

        if conflicts:
            status = "conflict"
        elif missing:
            status = "partial" if evidences else "insufficient"
        else:
            status = "pass"

        return VerificationReport(
            status=status,
            selected_evidence_ids=[item.evidence_id for item in selected],
            conflicts=conflicts,
            missing_evidence=missing,
            notes=notes,
        )

    def format_value(self, value: Any, constraints: AnswerConstraints) -> str:
        output_type = getattr(constraints, "output_type", "text")
        precision = getattr(constraints, "precision", None)
        unit = getattr(constraints, "unit", None) or ""

        if output_type == "percentage":
            return f"{float(value):.{precision if precision is not None else 2}f}%"
        if output_type in {"money", "monetary", "number"}:
            return f"{self._format_number(value, precision)}{unit}"
        if output_type == "identifier" and getattr(
            constraints, "preserve_identifier_zeroes", True
        ):
            return str(value)
        if output_type in {"multi_value", "multi-year", "multi_year"} and isinstance(
            value, (list, tuple)
        ):
            return "; ".join(self._format_multi_item(item, precision, unit) for item in value)
        if output_type in {"ranked", "top_n", "top-N"} and isinstance(value, (list, tuple)):
            return "; ".join(self._format_ranked_item(item, index + 1, unit) for index, item in enumerate(value))
        if precision is not None and isinstance(value, (int, float)):
            return self._format_number(value, precision)
        return str(value)

    def format_answer(
        self,
        values: Any,
        plan: QuestionPlan,
        report: VerificationReport | None = None,
    ) -> str:
        prefix = ""
        if report and report.status in {"partial", "insufficient"}:
            prefix = f"{report.status}: "
        return prefix + self.format_value(values, plan.answer_constraints)

    def _required_missing(self, plan: QuestionPlan) -> list[str]:
        missing: list[str] = []
        for need in getattr(plan, "evidence_need", []) or []:
            self._append_unique(missing, self._need_label(need))
        return missing

    def _missing_evidence(self, plan: QuestionPlan, evidences: list[Evidence]) -> list[str]:
        missing: list[str] = []
        has_sql = any(item.evidence_type == "sql_result" or item.source_type == "db" for item in evidences)
        has_doc = any(item.source_type in {"pdf", "txt"} for item in evidences)
        has_table = any(item.evidence_type == "table" for item in evidences)

        for need in getattr(plan, "evidence_need", []) or []:
            label = self._need_label(need)
            if label == "sql_result" and not has_sql:
                missing.append("sql_result")
            elif label == "prospectus_evidence" and not has_doc:
                missing.append("prospectus_evidence")
            elif label == "table" and not has_table:
                missing.append("table")

        if getattr(plan, "route", None) == "hybrid":
            if not has_sql:
                self._append_unique(missing, "sql_result")
            if not has_doc:
                self._append_unique(missing, "prospectus_evidence")
        return missing

    def _need_label(self, need: str) -> str:
        if need in {"sql", "db", "database", "sql_result"}:
            return "sql_result"
        if need in {"text", "pdf", "prospectus", "prospectus_evidence"}:
            return "prospectus_evidence"
        return need

    def _source_preference(self, plan: QuestionPlan) -> str | None:
        entities = getattr(plan, "entities", {}) or {}
        explicit = entities.get("source_preference") or entities.get("preferred_source")
        text = " ".join(
            str(part).lower()
            for part in [
                explicit,
                getattr(plan, "reason", ""),
                getattr(plan, "task_type", ""),
                getattr(plan, "evidence_need", []),
            ]
        )
        if any(token in text for token in ("prospectus", "pdf", "disclosure")):
            return "prospectus"
        if any(token in text for token in ("database", "db", "daily quote", "holding table", "industry table")):
            return "database"
        return None

    def _preferred_evidence(self, evidences: list[Evidence], preference: str) -> list[Evidence]:
        if preference == "prospectus":
            return [item for item in evidences if item.source_type in {"pdf", "txt"}]
        if preference == "database":
            return [item for item in evidences if item.source_type == "db" or item.evidence_type == "sql_result"]
        return []

    def _fact_conflicts(self, evidences: list[Evidence]) -> list[dict[str, Any]]:
        facts_by_key: dict[str, dict[str, list[str]]] = {}
        for evidence in evidences:
            facts = (getattr(evidence, "metadata", {}) or {}).get("facts", {})
            if not isinstance(facts, dict):
                continue
            for key, value in facts.items():
                values = facts_by_key.setdefault(str(key), {})
                ids = values.setdefault(str(value), [])
                ids.append(evidence.evidence_id)

        conflicts: list[dict[str, Any]] = []
        for key, values in facts_by_key.items():
            if len(values) > 1:
                conflicts.append({"fact": key, "values": values})
        return conflicts

    def _formula_conflicts(self, evidences: list[Evidence]) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        for evidence in evidences:
            formula = (getattr(evidence, "metadata", {}) or {}).get("formula")
            if not isinstance(formula, dict):
                continue
            identifier = formula.get("identifier")
            expected = self._computed_formula_value(identifier, formula.get("inputs", {}))
            actual = formula.get("result")
            if expected is None or actual is None:
                continue
            tolerance = float(formula.get("tolerance", 0.01))
            if abs(float(actual) - expected) > tolerance:
                conflicts.append(
                    {
                        "evidence_id": evidence.evidence_id,
                        "formula": identifier,
                        "expected": expected,
                        "actual": actual,
                    }
                )
        return conflicts

    def _computed_formula_value(self, identifier: str | None, inputs: dict[str, Any]) -> float | None:
        if identifier == "daily_percent_change":
            close = inputs.get("close")
            previous_close = inputs.get("previous_close")
            if close is None or previous_close in {None, 0}:
                return None
            return (float(close) / float(previous_close) - 1.0) * 100.0
        if identifier == "limit_up_days":
            returns = inputs.get("returns")
            threshold = float(inputs.get("threshold", 0.098))
            if isinstance(returns, list):
                return float(sum(1 for value in returns if float(value) >= threshold))
        if identifier == "price_range":
            high = inputs.get("high")
            low = inputs.get("low")
            if high is not None and low is not None:
                return float(high) - float(low)
        if identifier in {"open_above_previous_close_days", "open_above_previous_close"}:
            rows = inputs.get("rows")
            if isinstance(rows, list):
                return float(
                    sum(
                        1
                        for row in rows
                        if row.get("open") is not None
                        and row.get("previous_close") is not None
                        and float(row["open"]) > float(row["previous_close"])
                    )
                )
            open_price = inputs.get("open")
            previous_close = inputs.get("previous_close")
            if open_price is not None and previous_close is not None:
                return 1.0 if float(open_price) > float(previous_close) else 0.0
        return None

    def _metadata_consistency_conflicts(
        self,
        plan: QuestionPlan,
        evidences: list[Evidence],
    ) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        constraints = getattr(plan, "answer_constraints", AnswerConstraints())
        for evidence in evidences:
            metadata = getattr(evidence, "metadata", {}) or {}
            expected_unit = getattr(constraints, "unit", None)
            if not expected_unit and getattr(constraints, "output_type", None) == "percentage":
                expected_unit = "%"
            if expected_unit and metadata.get("unit") and metadata["unit"] != expected_unit:
                conflicts.append(
                    {
                        "kind": "unit",
                        "evidence_id": evidence.evidence_id,
                        "expected": expected_unit,
                        "actual": metadata["unit"],
                    }
                )

            self._append_metadata_mismatch(conflicts, evidence, metadata, "date", "expected_date")
            self._append_metadata_mismatch(
                conflicts,
                evidence,
                metadata,
                "report_period",
                "expected_report_period",
            )

            if "formatted_value" in metadata and "result_value" in metadata:
                expected_formatted = self.format_value(metadata["result_value"], constraints)
                if metadata["formatted_value"] != expected_formatted:
                    conflicts.append(
                        {
                            "kind": "rounding",
                            "evidence_id": evidence.evidence_id,
                            "expected": expected_formatted,
                            "actual": metadata["formatted_value"],
                        }
                    )
        return conflicts

    def _append_metadata_mismatch(
        self,
        conflicts: list[dict[str, Any]],
        evidence: Evidence,
        metadata: dict[str, Any],
        actual_key: str,
        expected_key: str,
    ) -> None:
        if expected_key in metadata and actual_key in metadata and metadata[actual_key] != metadata[expected_key]:
            conflicts.append(
                {
                    "kind": actual_key,
                    "evidence_id": evidence.evidence_id,
                    "expected": metadata[expected_key],
                    "actual": metadata[actual_key],
                }
            )

    def _raw_table_missing(self, plan: QuestionPlan, evidences: list[Evidence]) -> bool:
        precise_table_task = getattr(plan, "task_type", "") in {
            "financial_table_fact",
            "prospectus_table_fact",
            "table_fact",
        }
        if "table" in (getattr(plan, "evidence_need", []) or []):
            precise_table_task = True
        return precise_table_task and any(
            (getattr(item, "metadata", {}) or {}).get("raw_table_unavailable") for item in evidences
        )

    def _format_number(self, value: Any, precision: int | None) -> str:
        if precision is None:
            return str(value)
        return f"{float(value):.{precision}f}"

    def _format_multi_item(self, item: Any, precision: int | None, unit: str) -> str:
        if isinstance(item, dict):
            label = item.get("label") or item.get("year") or item.get("period") or item.get("name")
            value = item.get("value")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            label, value = item[0], item[1]
        else:
            return str(item)
        return f"{label}: {self._format_number(value, precision)}{unit}"

    def _format_ranked_item(self, item: Any, default_rank: int, unit: str) -> str:
        if isinstance(item, dict):
            rank = item.get("rank", default_rank)
            name = item.get("name") or item.get("label") or item.get("id")
            value = item.get("value")
            if value is None:
                return f"{rank}. {name}"
            suffix = f" {unit}" if unit else ""
            return f"{rank}. {name}: {value}{suffix}"
        return f"{default_rank}. {item}"

    def _append_unique(self, values: list[str], value: str) -> None:
        if value not in values:
            values.append(value)


def report_to_dict(report: VerificationReport) -> dict[str, Any]:
    if hasattr(report, "to_dict"):
        return report.to_dict()
    return asdict(report)
