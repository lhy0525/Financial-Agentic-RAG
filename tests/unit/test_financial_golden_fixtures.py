import pytest

from src.financial_dataset.golden_fixtures import (
    CoverageMatrix,
    validate_fixture,
    validate_minimum_coverage,
)


def _case(case_id, route, task_family, tags):
    case = {
        "id": case_id,
        "question": f"{case_id} question",
        "expected_route": route,
        "task_family": task_family,
        "expected_entities": {},
        "expected_time_scope": {},
        "expected_evidence_family": task_family,
        "expected_answer_constraints": {},
        "tags": tags,
    }
    if route == "hybrid":
        case.update(
            {
                "expected_hybrid_mode": "sql_first",
                "expected_sql_subquestion": "sql subquestion",
                "expected_prospectus_subquestion": "prospectus subquestion",
                "expected_entity_mapping": {},
            }
        )
    return case


def test_validate_fixture_requires_skip_reason_when_unavailable():
    case = _case("missing-data", "text_to_sql", "quote formula", ["formula"])
    case["requires_data"] = ["sqlite_db"]
    case["data_available"] = False

    with pytest.raises(ValueError, match="skip_reason"):
        validate_fixture(case)


def test_validate_minimum_coverage_passes_for_required_routes_and_tags():
    cases = [
        _case("sql", "text_to_sql", "quote formula", ["formula"]),
        _case("pdf", "pdf_rag", "business disclosure", ["alias_resolution"]),
        _case("hybrid", "hybrid", "hybrid", ["latest", "report_period"]),
    ]

    validate_minimum_coverage(cases, CoverageMatrix.default())


def test_validate_minimum_coverage_reports_missing_family():
    cases = [_case("sql", "text_to_sql", "quote formula", ["formula"])]

    with pytest.raises(ValueError, match="missing"):
        validate_minimum_coverage(cases, CoverageMatrix.default())
