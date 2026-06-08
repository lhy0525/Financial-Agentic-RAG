from __future__ import annotations

from src.observability.evaluation.financial_eval_runner import FinancialEvalRunner


class FailingAgent:
    def answer(self, question):
        return {
            "question_plan": {"route": "text_to_sql", "entities": {}, "formula": None},
            "verification_report": {"status": "pass"},
            "answer": "answer",
            "sources": [],
            "trace": {"tool_sequence": ["plan", "text_to_sql"]},
        }


def test_threshold_failure_reports_metric_and_case_id():
    cases = [
        {
            "id": "route-fail",
            "question": "q",
            "expected_route": "pdf_rag",
            "expected_status": "pass",
            "task_family": "business disclosure",
        }
    ]
    thresholds = {"route_accuracy": 1.0}

    result = FinancialEvalRunner(agent=FailingAgent(), thresholds=thresholds).run(cases)

    assert result["passed"] is False
    assert result["thresholds"]["route_accuracy"] == 1.0
    assert result["failed_thresholds"][0]["metric"] == "route_accuracy"
    assert result["failed_thresholds"][0]["case_ids"] == ["route-fail"]


def test_case_level_diagnostics_include_expected_and_actual_values():
    cases = [
        {
            "id": "diagnostic",
            "question": "q",
            "expected_route": "pdf_rag",
            "expected_status": "insufficient",
            "task_family": "business disclosure",
        }
    ]

    result = FinancialEvalRunner(agent=FailingAgent()).run(cases)

    case = result["case_results"][0]
    assert case["id"] == "diagnostic"
    assert case["question"] == "q"
    assert case["expected"]["route"] == "pdf_rag"
    assert case["expected"]["status"] == "insufficient"
    assert case["actual"]["route"] == "text_to_sql"
    assert case["actual"]["status"] == "pass"
    assert "route_accuracy" in case["failure_reasons"]
    assert "verification_status_accuracy" in case["failure_reasons"]


def test_stable_machine_readable_top_level_fields():
    result = FinancialEvalRunner(agent=FailingAgent()).run([])

    assert set(result).issuperset(
        {
            "count",
            "families",
            "regressions",
            "case_results",
            "thresholds",
            "failed_thresholds",
            "skipped_cases",
            "run_metadata",
            "passed",
        }
    )


def test_unavailable_data_cases_are_skipped_with_reason():
    result = FinancialEvalRunner(agent=FailingAgent()).run(
        [
            {
                "id": "missing-db",
                "question": "q",
                "data_available": False,
                "skip_reason": "sqlite db unavailable",
            }
        ]
    )

    assert result["count"] == 0
    assert result["skipped_cases"] == [
        {"id": "missing-db", "reason": "sqlite db unavailable"}
    ]
