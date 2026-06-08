from src.agentic.types import (
    AnswerConstraints,
    Evidence,
    EvidencePackage,
    QuestionPlan,
    TimeScope,
    VerificationReport,
)


def test_question_plan_serializes_nested_fields():
    plan = QuestionPlan(
        route="text_to_sql",
        task_type="quote_formula",
        entities={"stock_codes": ["000001"]},
        time_scope=TimeScope(kind="trading_date", value="20210105"),
        formula="daily_percent_change",
        evidence_need=["sql_result"],
        sub_questions=[],
        answer_constraints=AnswerConstraints(output_type="percentage", precision=2),
        reason="needs quote calculation",
        formula_params={"threshold": 0.098},
        raw_formula_text="close / previous_close - 1 >= 9.8%",
    )

    data = plan.to_dict()

    assert data["route"] == "text_to_sql"
    assert data["time_scope"]["kind"] == "trading_date"
    assert data["answer_constraints"]["precision"] == 2
    assert data["formula_params"]["threshold"] == 0.098
    assert data["raw_formula_text"] == "close / previous_close - 1 >= 9.8%"
    assert QuestionPlan.from_dict(data) == plan


def test_evidence_package_serializes_sql_metadata():
    evidence = Evidence(
        evidence_id="sql-1",
        evidence_type="sql_result",
        source_type="db",
        content="stock_code=000001, change=1.23%",
        source="bosera.db",
        metadata={"sql": "SELECT 1", "row_count": 1},
    )
    package = EvidencePackage(path="text_to_sql", question="q", evidences=[evidence])

    data = package.to_dict()

    assert data["evidences"][0]["metadata"]["sql"] == "SELECT 1"
    assert EvidencePackage.from_dict(data) == package


def test_verification_report_marks_missing_evidence():
    report = VerificationReport(
        status="insufficient",
        selected_evidence_ids=[],
        conflicts=[],
        missing_evidence=["raw_table"],
        notes=["Only placeholder was retrieved"],
    )

    data = report.to_dict()

    assert data["status"] == "insufficient"
    assert VerificationReport.from_dict(data) == report
