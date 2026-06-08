from __future__ import annotations

from typing import Any

from src.agentic.merger import EvidenceMerger
from src.agentic.types import AnswerConstraints, Evidence, EvidencePackage, QuestionPlan, TimeScope
from src.agentic.verifier import FinancialVerifier


def _plan(
    route: str = "hybrid",
    evidence_need: list[str] | None = None,
    task_type: str = "point_lookup",
    output_type: str = "text",
    entities: dict[str, Any] | None = None,
    constraints: AnswerConstraints | None = None,
) -> QuestionPlan:
    return QuestionPlan(
        route=route,
        task_type=task_type,
        entities=entities or {},
        time_scope=TimeScope("not_applicable", None),
        formula=None,
        evidence_need=evidence_need or ["sql_result", "text"],
        sub_questions=[],
        answer_constraints=constraints or AnswerConstraints(output_type=output_type, precision=2),
        reason="test",
    )


def test_merger_deduplicates_same_source_content_and_preserves_traceability_metadata():
    first = Evidence(
        "txt-1",
        "text",
        "txt",
        "same fact",
        "prospectus-a.txt",
        metadata={"chunk_id": "c1"},
    )
    duplicate = Evidence(
        "txt-2",
        "text",
        "txt",
        "same fact",
        "prospectus-a.txt",
        metadata={"chunk_id": "c2"},
    )
    sql = Evidence("sql-1", "sql_result", "db", "row", "bosera.db", metadata={"sql": "SELECT 1"})

    merged = EvidenceMerger().merge(
        [
            EvidencePackage("pdf_rag", "q", [first], trace_id="trace-doc-1"),
            EvidencePackage("pdf_rag", "q", [duplicate], trace_id="trace-doc-2"),
            EvidencePackage("text_to_sql", "q", [sql], trace_id="trace-sql"),
        ]
    )

    assert [item.evidence_id for item in merged] == ["txt-1", "sql-1"]
    assert merged[0].metadata["chunk_id"] == "c1"
    assert merged[0].metadata["package_path"] == "pdf_rag"
    assert merged[0].metadata["trace_ids"] == ["trace-doc-1", "trace-doc-2"]
    assert merged[0].metadata["duplicate_evidence_ids"] == ["txt-1", "txt-2"]
    assert merged[0].metadata["duplicate_sources"] == ["prospectus-a.txt"]


def test_merger_preserves_original_traceability_when_stronger_duplicate_replaces_retained():
    weak = Evidence(
        "txt-weak",
        "text",
        "txt",
        "same fact",
        "prospectus-a.txt",
        score=0.2,
        metadata={"chunk_id": "weak", "source_path": "original-source"},
    )
    strong = Evidence(
        "txt-strong",
        "text",
        "txt",
        "same fact",
        "prospectus-a.txt",
        score=0.9,
        metadata={"chunk_id": "strong"},
    )

    merged = EvidenceMerger().merge(
        [
            EvidencePackage("pdf_rag", "q", [weak], trace_id="trace-weak"),
            EvidencePackage("pdf_rag", "q", [strong], trace_id="trace-strong"),
        ]
    )

    assert [item.evidence_id for item in merged] == ["txt-strong"]
    assert merged[0].metadata["chunk_id"] == "strong"
    assert merged[0].metadata["source_path"] == "original-source"
    assert merged[0].metadata["package_path"] == "pdf_rag"
    assert merged[0].metadata["trace_ids"] == ["trace-weak", "trace-strong"]
    assert merged[0].metadata["duplicate_evidence_ids"] == ["txt-weak", "txt-strong"]
    assert merged[0].metadata["duplicate_sources"] == ["prospectus-a.txt"]


def test_verifier_marks_missing_hybrid_prospectus_evidence_as_partial():
    plan = _plan(route="hybrid", evidence_need=["sql_result", "text"])
    evidence = Evidence("sql-1", "sql_result", "db", "row", "bosera.db")

    report = FinancialVerifier().verify(plan, [evidence])

    assert report.status == "partial"
    assert "prospectus_evidence" in report.missing_evidence


def test_verifier_prioritizes_requested_prospectus_source_for_conflicting_facts():
    plan = _plan(
        route="hybrid",
        evidence_need=["sql_result", "text"],
        entities={"source_preference": "prospectus"},
    )
    sql = Evidence(
        "sql-1",
        "sql_result",
        "db",
        "registered capital: 10",
        "bosera.db",
        metadata={"facts": {"registered_capital": "10"}},
    )
    doc = Evidence(
        "txt-1",
        "text",
        "txt",
        "registered capital: 12",
        "prospectus.txt",
        metadata={"facts": {"registered_capital": "12"}},
    )

    report = FinancialVerifier().verify(plan, [sql, doc])

    assert report.status == "pass"
    assert report.selected_evidence_ids == ["txt-1"]
    assert report.conflicts == []
    assert "prospectus source priority" in " ".join(report.notes)


def test_verifier_detects_formula_conflicts_for_supported_financial_patterns():
    plan = _plan(route="text_to_sql", evidence_need=["sql_result"], output_type="percentage")
    evidences = [
        Evidence(
            "daily",
            "sql_result",
            "db",
            "daily return",
            "bosera.db",
            metadata={
                "formula": {
                    "identifier": "daily_percent_change",
                    "inputs": {"close": 11.0, "previous_close": 10.0},
                    "result": 9.0,
                }
            },
        ),
        Evidence(
            "limit",
            "sql_result",
            "db",
            "limit up days",
            "bosera.db",
            metadata={
                "formula": {
                    "identifier": "limit_up_days",
                    "inputs": {"returns": [0.101, 0.05, 0.12], "threshold": 0.098},
                    "result": 1,
                }
            },
        ),
        Evidence(
            "range",
            "sql_result",
            "db",
            "price range",
            "bosera.db",
            metadata={
                "formula": {
                    "identifier": "price_range",
                    "inputs": {"high": 15.5, "low": 10.0},
                    "result": 5.0,
                }
            },
        ),
        Evidence(
            "open",
            "sql_result",
            "db",
            "open above previous close",
            "bosera.db",
            metadata={
                "formula": {
                    "identifier": "open_above_previous_close_days",
                    "inputs": {
                        "rows": [
                            {"open": 10.5, "previous_close": 10.0},
                            {"open": 9.9, "previous_close": 10.0},
                        ]
                    },
                    "result": 2,
                }
            },
        ),
    ]

    report = FinancialVerifier().verify(plan, evidences)

    assert report.status == "conflict"
    assert {item["formula"] for item in report.conflicts} == {
        "daily_percent_change",
        "limit_up_days",
        "price_range",
        "open_above_previous_close_days",
    }


def test_verifier_detects_unit_date_report_period_and_rounding_metadata_conflicts():
    plan = _plan(
        route="text_to_sql",
        evidence_need=["sql_result"],
        constraints=AnswerConstraints(output_type="percentage", precision=2, unit="%"),
    )
    evidence = Evidence(
        "sql-1",
        "sql_result",
        "db",
        "1.234%",
        "bosera.db",
        metadata={
            "result_value": 1.234,
            "formatted_value": "1.234",
            "unit": "decimal",
            "date": "2020-01-02",
            "expected_date": "2020-01-03",
            "report_period": "2022Q2",
            "expected_report_period": "2022Q4",
        },
    )

    report = FinancialVerifier().verify(plan, [evidence])

    assert report.status == "conflict"
    conflict_kinds = {item["kind"] for item in report.conflicts}
    assert {"unit", "date", "report_period", "rounding"}.issubset(conflict_kinds)


def test_verifier_marks_placeholder_table_as_partial_for_precise_table_facts():
    plan = _plan(route="pdf_rag", evidence_need=["table"], task_type="financial_table_fact")
    evidence = Evidence(
        "txt-1",
        "table",
        "txt",
        "<|TABLE_0001_0000.xlsx|>",
        "prospectus.txt",
        metadata={"raw_table_unavailable": True},
    )

    report = FinancialVerifier().verify(plan, [evidence])

    assert report.status == "partial"
    assert "raw_table" in report.missing_evidence


def test_format_value_handles_financial_answer_constraints():
    verifier = FinancialVerifier()

    assert verifier.format_value(1.2345, AnswerConstraints(output_type="percentage", precision=2)) == "1.23%"
    assert verifier.format_value(1234.5, AnswerConstraints(output_type="money", precision=1, unit="wan yuan")) == "1234.5wan yuan"
    assert verifier.format_value("000637", AnswerConstraints(output_type="identifier")) == "000637"
    assert verifier.format_value(
        [("2022", 3.456), ("2023", 7.891)],
        AnswerConstraints(output_type="multi_value", precision=1, unit="%"),
    ) == "2022: 3.5%; 2023: 7.9%"
    assert verifier.format_value(
        [{"rank": 1, "name": "A", "value": 10}, {"rank": 2, "name": "B", "value": 8}],
        AnswerConstraints(output_type="ranked", unit="100m yuan"),
    ) == "1. A: 10 100m yuan; 2. B: 8 100m yuan"
