from __future__ import annotations

from dataclasses import dataclass
from typing import Any


REQUIRED_FIXTURE_KEYS = {
    "id",
    "question",
    "expected_route",
    "task_family",
    "expected_entities",
    "expected_time_scope",
    "expected_evidence_family",
    "expected_answer_constraints",
    "tags",
}

REQUIRED_HYBRID_KEYS = {
    "expected_hybrid_mode",
    "expected_sql_subquestion",
    "expected_prospectus_subquestion",
    "expected_entity_mapping",
}


@dataclass(frozen=True)
class CoverageMatrix:
    routes: frozenset[str]
    tags: frozenset[str]

    @classmethod
    def default(cls) -> "CoverageMatrix":
        return cls(
            routes=frozenset({"text_to_sql", "pdf_rag", "hybrid"}),
            tags=frozenset({"latest", "report_period", "formula", "alias_resolution"}),
        )


def validate_fixture(case: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIXTURE_KEYS - case.keys())
    if missing:
        raise ValueError(f"fixture {case.get('id', '<unknown>')} missing required keys: {missing}")

    if case["expected_route"] == "hybrid":
        missing_hybrid = sorted(REQUIRED_HYBRID_KEYS - case.keys())
        if missing_hybrid:
            raise ValueError(
                f"fixture {case.get('id', '<unknown>')} missing hybrid keys: {missing_hybrid}"
            )

    if case.get("data_available") is False and "skip_reason" not in case:
        raise ValueError(f"fixture {case.get('id', '<unknown>')} missing skip_reason")


def validate_minimum_coverage(
    cases: list[dict[str, Any]], matrix: CoverageMatrix | None = None
) -> None:
    matrix = CoverageMatrix.default() if matrix is None else matrix
    for case in cases:
        validate_fixture(case)

    present_routes = {case["expected_route"] for case in cases}
    present_tags = {tag for case in cases for tag in case["tags"]}
    missing_routes = sorted(matrix.routes - present_routes)
    missing_tags = sorted(matrix.tags - present_tags)
    if missing_routes or missing_tags:
        raise ValueError(
            f"missing minimum coverage routes={missing_routes}, tags={missing_tags}"
        )
