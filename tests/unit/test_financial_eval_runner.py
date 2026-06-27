from __future__ import annotations

from src.observability.evaluation.financial_eval_runner import FinancialEvalRunner


class FakeAgent:
    def answer(self, question):
        if question == "real-sql-metadata":
            return {
                "question_plan": {
                    "route": "text_to_sql",
                    "hybrid_mode": None,
                    "entities": {"stock_codes": ["000001"]},
                    "formula": "daily_percent_change",
                },
                "verification_report": {"status": "pass"},
                "answer": "000001 5.00%",
                "sources": [
                    {
                        "evidence_id": "sql-real",
                        "evidence_type": "sql_result",
                        "source_type": "db",
                        "source": "bosera.db",
                        "metadata": {
                            "status": "success",
                            "safety": {"allowed": True},
                            "rows": [{"鑲＄エ浠ｇ爜": "000001", "daily_percent_change": 5.0}],
                        },
                    }
                ],
                "trace": {"tool_sequence": ["plan", "text_to_sql", "merge", "verify", "answer"]},
            }
        if question == "formatted":
            return {
                "question_plan": {
                    "route": "text_to_sql",
                    "hybrid_mode": None,
                    "entities": {"fund_codes": ["000001"]},
                    "formula": None,
                },
                "verification_report": {"status": "pass"},
                "answer": "000001 2022: 1.20%; 2023: 2.35%; total 10.50wan yuan top 2",
                "sources": [
                    {
                        "evidence_id": "sql-2",
                        "evidence_type": "sql_result",
                        "source_type": "db",
                        "source": "bosera.db",
                        "metadata": {
                            "sql_safety_passed": True,
                            "sql_execution_success": True,
                            "result_values": {"return": 1.234, "amount": 10.504},
                        },
                    }
                ],
                "trace": {"tool_sequence": ["plan", "text_to_sql", "merge", "verify", "answer"]},
            }
        if question == "hybrid":
            return {
                "question_plan": {
                    "route": "hybrid",
                    "hybrid_mode": "sql_first",
                    "entities": {"stock_codes": ["000637"], "company_names": ["Acme"]},
                    "formula": "daily_percent_change",
                },
                "verification_report": {"status": "partial"},
                "answer": "000637 1.23%",
                "sources": [
                    {
                        "evidence_id": "sql-1",
                        "evidence_type": "sql_result",
                        "source_type": "db",
                        "source": "bosera.db",
                        "metadata": {
                            "sql_safety_passed": True,
                            "sql_execution_success": True,
                            "result_values": {"return": 1.23},
                        },
                    },
                    {
                        "evidence_id": "txt-1",
                        "evidence_type": "table",
                        "source_type": "txt",
                        "source": "prospectus.txt",
                        "page": 5,
                        "metadata": {"raw_table_unavailable": True},
                    },
                ],
                "trace": {"tool_sequence": ["plan", "text_to_sql", "pdf_rag", "merge", "verify", "answer"]},
            }
        return {
            "question_plan": {
                "route": "text_to_sql",
                "hybrid_mode": None,
                "entities": {"stock_codes": ["000637"]},
                "formula": None,
            },
            "verification_report": {"status": "pass"},
            "answer": "炼油化工",
            "sources": [],
            "trace": {"tool_sequence": ["plan", "text_to_sql", "merge", "verify", "answer"]},
        }


class SourceAwareAgent:
    def answer(self, question):
        source = "rule" if question == "rule" else "lora"
        elapsed_ms = 25.0 if source == "rule" else 125.0
        return {
            "question_plan": {"route": "text_to_sql", "hybrid_mode": None, "entities": {}, "formula": None},
            "verification_report": {"status": "pass"},
            "answer": "answer",
            "sources": [
                {
                    "evidence_id": f"sql-{source}",
                    "evidence_type": "sql_result",
                    "source_type": "db",
                    "source": "bosera.db",
                    "metadata": {
                        "status": "success",
                        "sql_source": source,
                        "accepted_result_kind": "rows",
                        "final_failure_code": None,
                        "elapsed_ms": elapsed_ms,
                        "safety": {"allowed": True},
                        "rows": [{"value": 1}],
                    },
                }
            ],
            "trace": {
                "tool_sequence": ["plan", "text_to_sql", "merge", "verify", "answer"],
                "stages": [
                    {
                        "stage": "sql_evidence",
                        "sql_source": source,
                        "accepted_result_kind": "rows",
                        "final_failure_code": None,
                    }
                ],
            },
        }


class RouteMetricsAgent:
    def answer(self, question):
        fixtures = {
            "rule-ok": ("rule", "success", None, 20.0, []),
            "lora-ok": ("lora", "success", None, 50.0, [{"source": "lora", "selected": True}]),
            "repair-ok": ("repair", "success", None, 75.0, [{"source": "repair", "selected": True}]),
            "repair-failed": ("repair", "failed", "repair_exhausted", 80.0, [{"source": "repair", "selected": False}]),
        }
        source, status, failure_code, elapsed_ms, attempts = fixtures[question]
        return {
            "question_plan": {"route": "text_to_sql", "hybrid_mode": None, "entities": {}, "formula": None},
            "verification_report": {"status": "pass" if status == "success" else "insufficient"},
            "answer": "answer" if status == "success" else "",
            "sources": [
                {
                    "evidence_id": f"sql-{question}",
                    "evidence_type": "sql_result",
                    "source_type": "db",
                    "source": "bosera.db",
                    "metadata": {
                        "status": status,
                        "sql_source": source,
                        "accepted_result_kind": "rows" if status == "success" else None,
                        "final_failure_code": failure_code,
                        "elapsed_ms": elapsed_ms,
                        "safety": {"allowed": True},
                        "fallback_attempts": attempts,
                        "repair_attempts": len([item for item in attempts if item["source"] == "repair"]),
                        "rows": [{"value": 1}] if status == "success" else [],
                    },
                }
            ],
            "trace": {"tool_sequence": ["plan", "text_to_sql"]},
        }


def test_eval_runner_reports_financial_metrics_and_family_breakdowns():
    cases = [
        {
            "id": "case-1",
            "question": "sql",
            "expected_route": "text_to_sql",
            "expected_status": "pass",
            "expected_entities": {"stock_codes": ["000637"]},
            "task_family": "latest-record lookup",
        },
        {
            "id": "case-2",
            "question": "hybrid",
            "expected_route": "hybrid",
            "expected_hybrid_mode": "sql_first",
            "expected_entities": {"stock_codes": ["000637"], "company_names": ["Acme"]},
            "expected_formula": "daily_percent_change",
            "expected_status": "partial",
            "expected_tool_sequence": ["text_to_sql", "pdf_rag"],
            "expected_sql": {
                "safety_passed": True,
                "execution_success": True,
                "result_values": {"return": 1.23},
            },
            "expected_prospectus": {
                "sources": ["prospectus.txt"],
                "evidence_types": ["table"],
                "pages": [5],
            },
            "expected_formatting": {
                "contains": ["000637", "%"],
                "identifier": "000637",
            },
            "regression": "missing_raw_table",
            "expected_regression_status": "partial",
            "task_family": "prospectus table facts",
        },
        {
            "id": "case-3",
            "question": "formatted",
            "expected_route": "text_to_sql",
            "expected_status": "pass",
            "expected_sql": {
                "safety_passed": True,
                "execution_success": True,
            },
            "expected_sql_values": {"return": 1.23, "amount": 10.5},
            "expected_tolerance": 0.01,
            "expected_answer_format": {
                "percentage": True,
                "precision": 2,
                "monetary_unit": "wan yuan",
                "identifier": "000001",
                "ordered_tokens": ["2022", "2023"],
                "top_n": 2,
            },
            "task_family": "fund scale",
        },
        {
            "id": "case-4",
            "question": "real-sql-metadata",
            "expected_route": "text_to_sql",
            "expected_status": "pass",
            "expected_sql": {
                "safety_passed": True,
                "execution_success": True,
                "result_values": {"daily_percent_change": 5.0},
            },
            "task_family": "quote formula",
        },
    ]

    result = FinancialEvalRunner(agent=FakeAgent()).run(cases)

    assert result["count"] == 4
    assert result["route_accuracy"] == 1.0
    assert result["hybrid_mode_accuracy"] == 1.0
    assert result["entity_extraction_accuracy"] == 1.0
    assert result["formula_detection_accuracy"] == 1.0
    assert result["sql_safety_accuracy"] == 1.0
    assert result["sql_execution_accuracy"] == 1.0
    assert result["sql_correctness_accuracy"] == 1.0
    assert result["prospectus_source_hit_rate"] == 1.0
    assert result["prospectus_evidence_type_hit_rate"] == 1.0
    assert result["prospectus_page_hit_rate"] == 1.0
    assert result["hybrid_sequence_accuracy"] == 1.0
    assert result["verification_status_accuracy"] == 1.0
    assert result["answer_formatting_accuracy"] == 1.0
    assert result["sql_value_tolerance_accuracy"] == 1.0
    assert result["families"]["latest-record lookup"]["count"] == 1
    assert result["families"]["prospectus table facts"]["verification_status_accuracy"] == 1.0
    assert result["families"]["fund scale"]["answer_formatting_accuracy"] == 1.0
    assert result["regressions"]["missing_raw_table"]["status_accuracy"] == 1.0


def test_eval_runner_reports_sql_source_breakdown_and_case_diagnostics():
    cases = [
        {"id": "rule-case", "question": "rule", "expected_route": "text_to_sql"},
        {"id": "lora-case", "question": "lora", "expected_route": "text_to_sql"},
    ]

    result = FinancialEvalRunner(agent=SourceAwareAgent()).run(cases)

    assert result["sql_sources"]["rule"]["count"] == 1
    assert result["sql_sources"]["lora"]["count"] == 1
    assert result["sql_sources"]["lora"]["execution_success_rate"] == 1.0
    assert result["case_results"][1]["actual"]["selected_sql_source"] == "lora"
    assert result["case_results"][1]["actual"]["accepted_result_kind"] == "rows"
    assert result["case_results"][1]["actual"]["final_failure_code"] is None


def test_eval_runner_reports_fallback_lift_and_repair_metrics():
    cases = [
        {"id": "rule-ok", "question": "rule-ok", "task_family": "lookup"},
        {"id": "lora-ok", "question": "lora-ok", "task_family": "lookup"},
        {"id": "repair-ok", "question": "repair-ok", "task_family": "lookup"},
        {"id": "repair-failed", "question": "repair-failed", "task_family": "lookup"},
    ]

    result = FinancialEvalRunner(agent=RouteMetricsAgent()).run(cases)

    assert result["fallback_lift"]["fallback_success_count"] == 2
    assert result["fallback_lift"]["families"]["lookup"]["fallback_success_count"] == 2
    assert result["repair_metrics"]["count"] == 2
    assert result["repair_metrics"]["execution_success_rate"] == 0.5
    assert result["repair_metrics"]["retry_exhaustion_count"] == 1
    assert result["repair_metrics"]["non_empty_result_rate"] == 0.5
