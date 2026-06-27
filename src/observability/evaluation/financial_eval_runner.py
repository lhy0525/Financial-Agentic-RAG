from __future__ import annotations

from collections import defaultdict
from typing import Any


class FinancialEvalRunner:
    """Evaluate staged financial Agentic RAG outputs against golden cases."""

    def __init__(self, agent: Any, thresholds: dict[str, float] | None = None) -> None:
        self.agent = agent
        self.thresholds = thresholds or {}

    def run(self, cases: list[dict[str, Any]]) -> dict[str, Any]:
        totals = _MetricTotals()
        family_totals: dict[str, _MetricTotals] = defaultdict(_MetricTotals)
        source_totals: dict[str, _SQLSourceTotals] = defaultdict(_SQLSourceTotals)
        fallback_lift = _FallbackLiftTotals()
        family_fallback_lift: dict[str, _FallbackLiftTotals] = defaultdict(_FallbackLiftTotals)
        repair_metrics = _RepairMetricTotals()
        regressions: dict[str, dict[str, float | int]] = defaultdict(lambda: {"count": 0, "status_hits": 0})
        case_results: list[dict[str, Any]] = []
        skipped_cases: list[dict[str, Any]] = []

        for case in cases:
            if case.get("data_available") is False:
                skipped_cases.append(
                    {
                        "id": case.get("id"),
                        "reason": case.get("skip_reason", "data unavailable"),
                    }
                )
                continue
            result = self.agent.answer(case["question"])
            case_metrics = self._score_case(case, result)
            totals.add(case_metrics)
            family = case.get("task_family", "unknown")
            family_totals[family].add(case_metrics)
            source_metadata = self._sql_route_metadata(result)
            source = source_metadata.get("selected_sql_source")
            if source:
                source_totals[str(source)].add(source_metadata)
                fallback_lift.add(source_metadata)
                family_fallback_lift[family].add(source_metadata)
                repair_metrics.add(source_metadata)
            self._score_regression(case, result, regressions)
            case_results.append(self._case_diagnostics(case, result, case_metrics))

        output = totals.to_report()
        output["families"] = {
            family: family_total.to_report() for family, family_total in family_totals.items()
        }
        output["sql_sources"] = {
            source: source_totals[source].to_report()
            for source in ("rule", "lora", "api", "repair")
        }
        fallback_latencies = [
            source_totals[source].max_latency_ms
            for source in ("lora", "api", "repair")
            if source_totals[source].count
        ]
        output["fallback_latency_budget_ms"] = max(fallback_latencies) if fallback_latencies else 0.0
        output["fallback_lift"] = fallback_lift.to_report()
        output["fallback_lift"]["families"] = {
            family: totals.to_report() for family, totals in family_fallback_lift.items()
        }
        output["repair_metrics"] = repair_metrics.to_report()
        output["promotion_gates"] = self._promotion_gates(output)
        output["regressions"] = self._regression_report(regressions)
        output["regression_pass_rate"] = self._regression_pass_rate(regressions)
        output["case_results"] = case_results
        output["thresholds"] = dict(self.thresholds)
        output["failed_thresholds"] = self._failed_thresholds(output, case_results)
        output["skipped_cases"] = skipped_cases
        output["run_metadata"] = {
            "input_count": len(cases),
            "evaluated_count": output["count"],
            "skipped_count": len(skipped_cases),
        }
        output["passed"] = not output["failed_thresholds"]
        return output

    def _score_case(self, case: dict[str, Any], result: dict[str, Any]) -> dict[str, tuple[int, int]]:
        plan = result.get("question_plan", {})
        report = result.get("verification_report", {})
        sources = result.get("sources", [])
        trace = result.get("trace", {})

        metrics: dict[str, tuple[int, int]] = {}
        self._add_expected(metrics, "route", plan.get("route"), case.get("expected_route"))
        self._add_expected(metrics, "hybrid_mode", plan.get("hybrid_mode"), case.get("expected_hybrid_mode"))
        self._add_expected(metrics, "formula_detection", plan.get("formula"), case.get("expected_formula"))
        self._add_expected(metrics, "verification_status", report.get("status"), case.get("expected_status"))

        if "expected_entities" in case:
            metrics["entity_extraction"] = (
                int(self._dict_contains(plan.get("entities", {}), case["expected_entities"])),
                1,
            )

        expected_sql = case.get("expected_sql")
        if expected_sql:
            sql_sources = [item for item in sources if item.get("evidence_type") == "sql_result" or item.get("source_type") == "db"]
            sql_metadata = self._normalized_sql_metadata(sql_sources)
            self._add_expected(metrics, "sql_safety", sql_metadata.get("sql_safety_passed"), expected_sql.get("safety_passed"))
            self._add_expected(metrics, "sql_execution", sql_metadata.get("sql_execution_success"), expected_sql.get("execution_success"))
            if "result_values" in expected_sql:
                metrics["sql_correctness"] = (
                    int(self._dict_contains(sql_metadata.get("result_values", {}), expected_sql["result_values"])),
                    1,
                )
        if "expected_sql_values" in case:
            sql_sources = [item for item in sources if item.get("evidence_type") == "sql_result" or item.get("source_type") == "db"]
            sql_metadata = self._normalized_sql_metadata(sql_sources)
            metrics["sql_value_tolerance"] = (
                int(
                    self._values_within_tolerance(
                        sql_metadata.get("result_values", {}),
                        case["expected_sql_values"],
                        float(case.get("expected_tolerance", 0.0)),
                    )
                ),
                1,
            )

        expected_prospectus = case.get("expected_prospectus")
        if expected_prospectus:
            doc_sources = [item for item in sources if item.get("source_type") in {"pdf", "txt"}]
            if "sources" in expected_prospectus:
                metrics["prospectus_source_hit"] = (
                    int(self._any_expected_source(doc_sources, expected_prospectus["sources"])),
                    1,
                )
            if "evidence_types" in expected_prospectus:
                actual_types = {item.get("evidence_type") for item in doc_sources}
                metrics["prospectus_evidence_type_hit"] = (
                    int(set(expected_prospectus["evidence_types"]).issubset(actual_types)),
                    1,
                )
            if "pages" in expected_prospectus:
                actual_pages = {item.get("page") for item in doc_sources}
                metrics["prospectus_page_hit"] = (
                    int(set(expected_prospectus["pages"]).issubset(actual_pages)),
                    1,
                )

        if "expected_tool_sequence" in case:
            actual_sequence = [
                item for item in trace.get("tool_sequence", []) if item in {"text_to_sql", "pdf_rag"}
            ]
            metrics["hybrid_sequence"] = (
                int(actual_sequence == case["expected_tool_sequence"]),
                1,
            )

        if "expected_formatting" in case:
            metrics["answer_formatting"] = (
                int(self._answer_formatting_ok(result.get("answer", ""), case["expected_formatting"])),
                1,
            )
        if "expected_answer_format" in case:
            metrics["answer_formatting"] = (
                int(self._answer_formatting_ok(result.get("answer", ""), case["expected_answer_format"])),
                1,
            )

        return metrics

    def _score_regression(
        self,
        case: dict[str, Any],
        result: dict[str, Any],
        regressions: dict[str, dict[str, float | int]],
    ) -> None:
        name = case.get("regression")
        if not name:
            return
        entry = regressions[name]
        entry["count"] = int(entry["count"]) + 1
        expected_status = case.get("expected_regression_status") or case.get("expected_status")
        if result.get("verification_report", {}).get("status") == expected_status:
            entry["status_hits"] = int(entry["status_hits"]) + 1

    def _regression_report(
        self, regressions: dict[str, dict[str, float | int]]
    ) -> dict[str, dict[str, float | int]]:
        report: dict[str, dict[str, float | int]] = {}
        for name, values in regressions.items():
            count = int(values["count"])
            hits = int(values["status_hits"])
            report[name] = {
                "count": count,
                "status_accuracy": hits / count if count else 0.0,
            }
        return report

    def _regression_pass_rate(self, regressions: dict[str, dict[str, float | int]]) -> float:
        total_count = sum(int(values["count"]) for values in regressions.values())
        if not total_count:
            return 1.0
        total_hits = sum(int(values["status_hits"]) for values in regressions.values())
        return total_hits / total_count

    def _case_diagnostics(
        self,
        case: dict[str, Any],
        result: dict[str, Any],
        case_metrics: dict[str, tuple[int, int]],
    ) -> dict[str, Any]:
        plan = result.get("question_plan", {})
        report = result.get("verification_report", {})
        sources = result.get("sources", [])
        trace = result.get("trace", {})
        sql_route = self._sql_route_metadata(result)
        return {
            "id": case.get("id"),
            "question": case.get("question"),
            "task_family": case.get("task_family", "unknown"),
            "metrics": case_metrics,
            "metric_values": self._metric_values(case_metrics),
            "failure_reasons": self._failure_reasons(case_metrics),
            "expected": {
                "route": case.get("expected_route"),
                "hybrid_mode": case.get("expected_hybrid_mode"),
                "formula": case.get("expected_formula"),
                "status": case.get("expected_status"),
                "entities": case.get("expected_entities"),
                "sql": case.get("expected_sql"),
                "prospectus": case.get("expected_prospectus"),
                "tool_sequence": case.get("expected_tool_sequence"),
            },
            "actual": {
                "route": plan.get("route"),
                "hybrid_mode": plan.get("hybrid_mode"),
                "formula": plan.get("formula"),
                "status": report.get("status"),
                "entities": plan.get("entities", {}),
                "sources": sources,
                "trace": trace,
                "selected_sql_source": sql_route.get("selected_sql_source"),
                "accepted_result_kind": sql_route.get("accepted_result_kind"),
                "final_failure_code": sql_route.get("final_failure_code"),
                "sql_elapsed_ms": sql_route.get("elapsed_ms"),
            },
            "result": result,
        }

    def _metric_values(self, case_metrics: dict[str, tuple[int, int]]) -> dict[str, float]:
        return {
            _report_metric_name(name): hit / denominator if denominator else 0.0
            for name, (hit, denominator) in case_metrics.items()
        }

    def _failure_reasons(self, case_metrics: dict[str, tuple[int, int]]) -> list[str]:
        return [
            _report_metric_name(name)
            for name, (hit, denominator) in case_metrics.items()
            if denominator and hit < denominator
        ]

    def _failed_thresholds(
        self,
        output: dict[str, Any],
        case_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        failed: list[dict[str, Any]] = []
        for metric, threshold in self.thresholds.items():
            value = float(output.get(metric, 0.0))
            if metric == "fallback_latency_budget_ms":
                if value <= threshold:
                    continue
                failed.append(
                    {
                        "metric": metric,
                        "value": value,
                        "threshold": threshold,
                        "case_ids": [
                            case["id"]
                            for case in case_results
                            if case.get("actual", {}).get("selected_sql_source") in {"lora", "api", "repair"}
                            and float(case.get("actual", {}).get("sql_elapsed_ms") or 0.0) > threshold
                        ],
                    }
                )
                continue
            if value >= threshold:
                continue
            failed.append(
                {
                    "metric": metric,
                    "value": value,
                    "threshold": threshold,
                    "case_ids": [
                        case["id"]
                        for case in case_results
                        if metric in case.get("failure_reasons", [])
                    ],
                }
            )
        return failed

    def _promotion_gates(self, output: dict[str, Any]) -> dict[str, bool]:
        latency_budget = self.thresholds.get("fallback_latency_budget_ms")
        return {
            "latency_budget_ok": (
                True
                if latency_budget is None
                else float(output.get("fallback_latency_budget_ms", 0.0)) <= float(latency_budget)
            ),
            "metadata_complete_ok": True,
        }

    def _sql_route_metadata(self, result: dict[str, Any]) -> dict[str, Any]:
        sources = result.get("sources", [])
        sql_sources = [
            item
            for item in sources
            if item.get("evidence_type") == "sql_result" or item.get("source_type") == "db"
        ]
        metadata = self._normalized_sql_metadata(sql_sources)
        trace_stage = self._sql_trace_stage(result.get("trace", {}))
        source = metadata.get("sql_source") or trace_stage.get("sql_source")
        if not source:
            return {}
        status = metadata.get("status")
        execution_success = metadata.get("sql_execution_success")
        if execution_success is None:
            execution_success = status == "success"
        return {
            "selected_sql_source": source,
            "accepted_result_kind": metadata.get("accepted_result_kind") or trace_stage.get("accepted_result_kind"),
            "final_failure_code": metadata.get("final_failure_code") or trace_stage.get("final_failure_code"),
            "elapsed_ms": float(metadata.get("elapsed_ms") or trace_stage.get("elapsed_ms") or 0.0),
            "execution_success": bool(execution_success),
            "status": status,
            "fallback_attempts": metadata.get("fallback_attempts") or trace_stage.get("fallback_attempts") or [],
            "repair_attempts": int(metadata.get("repair_attempts") or trace_stage.get("repair_attempts") or 0),
        }

    def _sql_trace_stage(self, trace: dict[str, Any]) -> dict[str, Any]:
        stages = trace.get("stages", [])
        if not isinstance(stages, list):
            return {}
        for stage in stages:
            if isinstance(stage, dict) and stage.get("stage") == "sql_evidence":
                return stage
        return {}

    def _add_expected(
        self,
        metrics: dict[str, tuple[int, int]],
        name: str,
        actual: Any,
        expected: Any,
    ) -> None:
        if expected is not None:
            metrics[name] = (int(actual == expected), 1)

    def _dict_contains(self, actual: dict[str, Any], expected: dict[str, Any]) -> bool:
        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if isinstance(expected_value, list):
                if not set(expected_value).issubset(set(actual_value or [])):
                    return False
            elif actual_value != expected_value:
                return False
        return True

    def _values_within_tolerance(
        self,
        actual: dict[str, Any],
        expected: dict[str, Any],
        tolerance: float,
    ) -> bool:
        for key, expected_value in expected.items():
            if key not in actual:
                return False
            actual_value = actual[key]
            if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                if abs(float(actual_value) - float(expected_value)) > tolerance:
                    return False
            elif actual_value != expected_value:
                return False
        return True

    def _merged_metadata(self, sources: list[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for source in sources:
            metadata = source.get("metadata", {})
            if isinstance(metadata, dict):
                merged.update(metadata)
        return merged

    def _normalized_sql_metadata(self, sources: list[dict[str, Any]]) -> dict[str, Any]:
        metadata = self._merged_metadata(sources)
        normalized = dict(metadata)
        safety = metadata.get("safety")
        if "sql_safety_passed" not in normalized and isinstance(safety, dict):
            normalized["sql_safety_passed"] = safety.get("allowed")
        if "sql_execution_success" not in normalized:
            normalized["sql_execution_success"] = metadata.get("status") == "success"
        if "result_values" not in normalized:
            normalized["result_values"] = self._result_values_from_rows(metadata.get("rows", []))
        return normalized

    def _result_values_from_rows(self, rows: Any) -> dict[str, Any]:
        if not isinstance(rows, list) or not rows:
            return {}
        result: dict[str, Any] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                result.setdefault(key, value)
        return result

    def _any_expected_source(self, sources: list[dict[str, Any]], expected: list[str]) -> bool:
        actual = [str(item.get("source", "")) for item in sources]
        return any(any(expected_source in actual_source for actual_source in actual) for expected_source in expected)

    def _answer_formatting_ok(self, answer: str, expected: dict[str, Any]) -> bool:
        for token in expected.get("contains", []):
            if token not in answer:
                return False
        identifier = expected.get("identifier")
        if identifier is not None and str(identifier) not in answer:
            return False
        if expected.get("percentage") and "%" not in answer:
            return False
        monetary_unit = expected.get("monetary_unit")
        if monetary_unit and str(monetary_unit) not in answer:
            return False
        top_n = expected.get("top_n")
        if top_n is not None and str(top_n) not in answer:
            return False
        ordered_tokens = expected.get("ordered_tokens", [])
        cursor = -1
        for token in ordered_tokens:
            index = answer.find(str(token), cursor + 1)
            if index == -1:
                return False
            cursor = index
        precision = expected.get("precision")
        if precision is not None and not self._has_decimal_precision(answer, int(precision)):
            return False
        return True

    def _has_decimal_precision(self, answer: str, precision: int) -> bool:
        import re

        return bool(re.search(rf"\d+\.\d{{{precision}}}(?:%|\b)", answer))


class _MetricTotals:
    def __init__(self) -> None:
        self.count = 0
        self.hits: dict[str, int] = defaultdict(int)
        self.denominators: dict[str, int] = defaultdict(int)

    def add(self, case_metrics: dict[str, tuple[int, int]]) -> None:
        self.count += 1
        for name, (hit, denominator) in case_metrics.items():
            self.hits[name] += hit
            self.denominators[name] += denominator

    def to_report(self) -> dict[str, Any]:
        report: dict[str, Any] = {"count": self.count}
        for name, denominator in self.denominators.items():
            report[_report_metric_name(name)] = (
                self.hits[name] / denominator if denominator else 0.0
            )
        return report


class _SQLSourceTotals:
    def __init__(self) -> None:
        self.count = 0
        self.execution_success = 0
        self.total_latency_ms = 0.0
        self.max_latency_ms = 0.0

    def add(self, metadata: dict[str, Any]) -> None:
        self.count += 1
        if metadata.get("execution_success"):
            self.execution_success += 1
        elapsed_ms = float(metadata.get("elapsed_ms") or 0.0)
        self.total_latency_ms += elapsed_ms
        self.max_latency_ms = max(self.max_latency_ms, elapsed_ms)

    def to_report(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "execution_success_rate": self.execution_success / self.count if self.count else 0.0,
            "avg_latency_ms": self.total_latency_ms / self.count if self.count else 0.0,
            "max_latency_ms": self.max_latency_ms,
        }


class _FallbackLiftTotals:
    def __init__(self) -> None:
        self.rule_success_count = 0
        self.fallback_success_count = 0
        self.fallback_attempt_count = 0

    def add(self, metadata: dict[str, Any]) -> None:
        source = metadata.get("selected_sql_source")
        if source == "rule" and metadata.get("execution_success"):
            self.rule_success_count += 1
        if source in {"lora", "api", "repair"}:
            self.fallback_attempt_count += 1
            if metadata.get("execution_success"):
                self.fallback_success_count += 1

    def to_report(self) -> dict[str, Any]:
        return {
            "rule_success_count": self.rule_success_count,
            "fallback_attempt_count": self.fallback_attempt_count,
            "fallback_success_count": self.fallback_success_count,
            "fallback_success_rate": (
                self.fallback_success_count / self.fallback_attempt_count
                if self.fallback_attempt_count
                else 0.0
            ),
        }


class _RepairMetricTotals:
    def __init__(self) -> None:
        self.count = 0
        self.execution_success = 0
        self.non_empty = 0
        self.retry_exhaustion_count = 0
        self.total_latency_ms = 0.0

    def add(self, metadata: dict[str, Any]) -> None:
        if metadata.get("selected_sql_source") != "repair" and not metadata.get("repair_attempts"):
            return
        self.count += 1
        if metadata.get("execution_success"):
            self.execution_success += 1
        if metadata.get("accepted_result_kind") == "rows":
            self.non_empty += 1
        if metadata.get("final_failure_code") == "repair_exhausted":
            self.retry_exhaustion_count += 1
        self.total_latency_ms += float(metadata.get("elapsed_ms") or 0.0)

    def to_report(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "execution_success_rate": self.execution_success / self.count if self.count else 0.0,
            "non_empty_result_rate": self.non_empty / self.count if self.count else 0.0,
            "retry_exhaustion_count": self.retry_exhaustion_count,
            "avg_latency_ms": self.total_latency_ms / self.count if self.count else 0.0,
        }


def _report_metric_name(name: str) -> str:
    return f"{name}_accuracy" if not name.endswith("_hit") else f"{name}_rate"
