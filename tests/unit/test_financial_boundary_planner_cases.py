import json
from pathlib import Path

from src.agentic.planner import FinancialQuestionPlanner
from src.financial_dataset.golden_fixtures import (
    CoverageMatrix,
    validate_minimum_coverage,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "financial_boundary_planner_cases.json"
)


def _load_cases():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _assert_expected_subset(actual, expected):
    actual_dict = actual.to_dict() if hasattr(actual, "to_dict") else actual
    for key, expected_value in expected.items():
        assert actual_dict.get(key) == expected_value


def test_financial_boundary_planner_fixture_coverage_and_cases():
    cases = _load_cases()
    validate_minimum_coverage(cases, CoverageMatrix.default())
    planner = FinancialQuestionPlanner()

    for case in cases:
        plan = planner.plan(case["question"])

        assert plan.route == case["expected_route"], case["id"]
        assert plan.task_type == case["task_family"], case["id"]

        if "expected_hybrid_mode" in case:
            assert plan.hybrid_mode == case["expected_hybrid_mode"], case["id"]

        _assert_expected_subset(plan.entities, case["expected_entities"])
        _assert_expected_subset(plan.time_scope, case["expected_time_scope"])
        _assert_expected_subset(
            plan.answer_constraints, case["expected_answer_constraints"]
        )

        if "expected_formula" in case:
            assert plan.formula == case["expected_formula"], case["id"]

        if "expected_entity_mapping" in case:
            expected_mapping = case["expected_entity_mapping"]["mapping"]
            assert any(
                step.get("mapping") == expected_mapping for step in plan.sub_questions
            ), case["id"]

        if "expected_sql_subquestion" in case:
            assert any(
                step.get("question") == case["expected_sql_subquestion"]
                for step in plan.sub_questions
            ), case["id"]

        if "expected_prospectus_subquestion" in case:
            assert any(
                step.get("question") == case["expected_prospectus_subquestion"]
                for step in plan.sub_questions
            ), case["id"]
