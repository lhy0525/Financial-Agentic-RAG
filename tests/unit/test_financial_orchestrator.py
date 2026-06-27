from __future__ import annotations

from src.agentic.orchestrator import FinancialOrchestrator
from src.agentic.types import AnswerConstraints, Evidence, EvidencePackage, QuestionPlan, TimeScope


class FakePlanner:
    def __init__(self, plan: QuestionPlan) -> None:
        self._plan = plan

    def plan(self, question: str) -> QuestionPlan:
        return self._plan


class RecordingSQLTool:
    def __init__(self, evidences: list[Evidence], metadata: dict | None = None) -> None:
        self.evidences = evidences
        self.metadata = metadata or {}
        self.calls: list[tuple[QuestionPlan, str]] = []

    def query(self, plan: QuestionPlan, question: str) -> EvidencePackage:
        self.calls.append((plan, question))
        return EvidencePackage("text_to_sql", question, self.evidences, metadata=self.metadata)


class RecordingProspectusTool:
    def __init__(self, evidences: list[Evidence]) -> None:
        self.evidences = evidences
        self.calls: list[str] = []

    def query(self, question: str) -> EvidencePackage:
        self.calls.append(question)
        return EvidencePackage("pdf_rag", question, self.evidences)


def _plan(
    route: str,
    hybrid_mode: str | None = None,
    sub_questions: list[dict[str, str]] | None = None,
    constraints: AnswerConstraints | None = None,
) -> QuestionPlan:
    evidence_need = ["sql_result"] if route == "text_to_sql" else ["text"]
    if route == "hybrid":
        evidence_need = ["sql_result", "text"]
    return QuestionPlan(
        route=route,
        task_type="latest_record_lookup",
        entities={"stock_codes": ["000637"]},
        time_scope=TimeScope("latest", None),
        formula=None,
        evidence_need=evidence_need,
        sub_questions=sub_questions or [],
        answer_constraints=constraints or AnswerConstraints(),
        reason="test",
        hybrid_mode=hybrid_mode,
    )


def test_orchestrator_answers_sql_only_question_with_structured_trace():
    sql_tool = RecordingSQLTool(
        [Evidence("sql-1", "sql_result", "db", '[{"industry": "refining chemicals"}]', "bosera.db")]
    )
    orchestrator = FinancialOrchestrator(
        planner=FakePlanner(_plan("text_to_sql")),
        sql_tool=sql_tool,
        prospectus_tool=None,
    )

    result = orchestrator.answer("question")

    assert result["verification_report"]["status"] == "pass"
    assert result["sources"][0]["evidence_id"] == "sql-1"
    assert "refining chemicals" in result["answer"]
    assert result["trace"]["tool_sequence"] == ["plan", "text_to_sql", "merge", "verify", "answer"]


def test_orchestrator_formats_result_value_with_answer_constraints():
    sql_tool = RecordingSQLTool(
        [
            Evidence(
                "sql-1",
                "sql_result",
                "db",
                "raw result",
                "bosera.db",
                metadata={"result_value": 1.23456},
            )
        ]
    )
    orchestrator = FinancialOrchestrator(
        planner=FakePlanner(_plan("text_to_sql", constraints=AnswerConstraints(output_type="percentage", precision=2))),
        sql_tool=sql_tool,
        prospectus_tool=None,
    )

    result = orchestrator.answer("question")

    assert result["answer"] == "1.23%"


def test_orchestrator_formats_ranked_rows_with_units_and_order():
    sql_tool = RecordingSQLTool(
        [
            Evidence(
                "sql-1",
                "sql_result",
                "db",
                "rows",
                "bosera.db",
                metadata={
                    "rows": [
                        {"rank": 1, "name": "Fund A", "value": 10},
                        {"rank": 2, "name": "Fund B", "value": 8},
                    ]
                },
            )
        ]
    )
    orchestrator = FinancialOrchestrator(
        planner=FakePlanner(_plan("text_to_sql", constraints=AnswerConstraints(output_type="top_n", unit="shares", top_n=2))),
        sql_tool=sql_tool,
        prospectus_tool=None,
    )

    result = orchestrator.answer("question")

    assert result["answer"] == "1. Fund A: 10 shares; 2. Fund B: 8 shares"


def test_orchestrator_preserves_leading_zero_identifier_result():
    sql_tool = RecordingSQLTool(
        [
            Evidence(
                "sql-1",
                "sql_result",
                "db",
                "code",
                "bosera.db",
                metadata={"result_value": "000637"},
            )
        ]
    )
    orchestrator = FinancialOrchestrator(
        planner=FakePlanner(_plan("text_to_sql", constraints=AnswerConstraints(output_type="identifier"))),
        sql_tool=sql_tool,
        prospectus_tool=None,
    )

    result = orchestrator.answer("question")

    assert result["answer"] == "000637"


def test_orchestrator_executes_doc_first_hybrid_sub_questions_in_order():
    sql_tool = RecordingSQLTool([Evidence("sql-1", "sql_result", "db", "quote rows", "bosera.db")])
    prospectus_tool = RecordingProspectusTool(
        [
            Evidence(
                "txt-1",
                "text",
                "txt",
                "issuer is Acme",
                "prospectus.txt",
                metadata={"entities": {"company_names": ["Acme"]}},
            )
        ]
    )
    plan = _plan(
        "hybrid",
        hybrid_mode="doc_first",
        sub_questions=[
            {"path": "pdf_rag", "question": "find issuer"},
            {"path": "text_to_sql", "question": "find latest quote for {company_names}"},
        ],
    )
    orchestrator = FinancialOrchestrator(FakePlanner(plan), sql_tool, prospectus_tool)

    result = orchestrator.answer("original")

    assert prospectus_tool.calls == ["find issuer"]
    assert sql_tool.calls[0][1] == "find latest quote for Acme"
    assert result["trace"]["tool_sequence"] == [
        "plan",
        "pdf_rag",
        "text_to_sql",
        "merge",
        "verify",
        "answer",
    ]


def test_orchestrator_returns_uploaded_prospectus_evidence_for_pdf_rag_question():
    prospectus_tool = RecordingProspectusTool(
        [
            Evidence(
                "prospectus-1",
                "text",
                "pdf",
                "The prospectus discloses liquidity risk.",
                "uploaded/prospectus.pdf",
                metadata={
                    "collection": "prospectus_uploads",
                    "local_origin": "ui_upload",
                    "document_id": "doc_uploaded",
                },
            )
        ]
    )
    orchestrator = FinancialOrchestrator(
        planner=FakePlanner(_plan("pdf_rag")),
        sql_tool=None,
        prospectus_tool=prospectus_tool,
    )

    result = orchestrator.answer("What risk is disclosed?")

    assert prospectus_tool.calls == ["What risk is disclosed?"]
    assert result["verification_report"]["status"] == "pass"
    assert result["sources"][0]["source"] == "uploaded/prospectus.pdf"
    assert result["sources"][0]["metadata"]["collection"] == "prospectus_uploads"
    assert result["sources"][0]["metadata"]["local_origin"] == "ui_upload"
    assert result["trace"]["tool_sequence"] == ["plan", "pdf_rag", "merge", "verify", "answer"]


def test_orchestrator_accepts_planner_target_path_hybrid_steps():
    sql_tool = RecordingSQLTool(
        [
            Evidence(
                "sql-1",
                "sql_result",
                "db",
                "resolved company",
                "bosera.db",
                metadata={"entities": {"company_names": ["Acme"]}},
            )
        ]
    )
    prospectus_tool = RecordingProspectusTool([Evidence("txt-1", "text", "txt", "disclosure", "p.txt")])
    plan = _plan(
        "hybrid",
        hybrid_mode="sql_first",
        sub_questions=[
            {"target_path": "text_to_sql", "question": "resolve stock"},
            {
                "target_path": "entity_mapping",
                "mapping": "sql_stock_result_to_prospectus_company_name",
                "question": "map company",
            },
            {"target_path": "pdf_rag", "question": "find disclosure for {company_names}"},
        ],
    )
    orchestrator = FinancialOrchestrator(FakePlanner(plan), sql_tool, prospectus_tool)

    result = orchestrator.answer("original")

    assert prospectus_tool.calls == ["find disclosure for Acme"]
    assert result["verification_report"]["status"] == "pass"


def test_orchestrator_derives_sql_sub_plan_for_real_hybrid_task_type():
    sql_tool = RecordingSQLTool(
        [
            Evidence(
                "sql-1",
                "sql_result",
                "db",
                "resolved company",
                "bosera.db",
                metadata={"entities": {"company_names": ["Acme"]}},
            )
        ]
    )
    prospectus_tool = RecordingProspectusTool([Evidence("txt-1", "text", "txt", "disclosure", "p.txt")])
    plan = QuestionPlan(
        route="hybrid",
        task_type="hybrid",
        entities={"stock_codes": ["000001"]},
        time_scope=TimeScope(kind="trading_date", value="20210105"),
        formula="daily_percent_change",
        evidence_need=["sql_result", "text"],
        sub_questions=[
            {"target_path": "text_to_sql", "question": "resolve stock"},
            {"target_path": "pdf_rag", "question": "find disclosure for {company_names}"},
        ],
        answer_constraints=AnswerConstraints(output_type="percentage", precision=2),
        reason="hybrid test",
        hybrid_mode="sql_first",
    )
    orchestrator = FinancialOrchestrator(FakePlanner(plan), sql_tool, prospectus_tool)

    orchestrator.answer("original")

    assert sql_tool.calls[0][0].route == "text_to_sql"
    assert sql_tool.calls[0][0].task_type == "quote_formula"


def test_orchestrator_returns_partial_when_first_hybrid_step_has_no_dependency_evidence():
    sql_tool = RecordingSQLTool([])
    prospectus_tool = RecordingProspectusTool([Evidence("txt-1", "text", "txt", "should not run", "p.txt")])
    plan = _plan(
        "hybrid",
        hybrid_mode="sql_first",
        sub_questions=[
            {"path": "text_to_sql", "question": "find company code"},
            {"path": "pdf_rag", "question": "find disclosure for {company_names}"},
        ],
    )
    orchestrator = FinancialOrchestrator(FakePlanner(plan), sql_tool, prospectus_tool)

    result = orchestrator.answer("original")

    assert prospectus_tool.calls == []
    assert result["verification_report"]["status"] in {"partial", "insufficient"}
    assert "hybrid_dependency" in result["verification_report"]["missing_evidence"]
    assert result["trace"]["tool_sequence"] == ["plan", "text_to_sql", "merge", "verify", "answer"]


def test_orchestrator_trace_preserves_sql_route_metadata():
    sql_tool = RecordingSQLTool(
        [],
        metadata={
            "status": "failed",
            "sql_source": "repair",
            "accepted_result_kind": None,
            "final_failure_code": "all_candidates_failed",
            "repair_attempts": 1,
            "fallback_attempts": [{"source": "repair", "failure_code": "execution_error"}],
            "sql_route_events": [
                {"event": "candidate_generated", "source": "rule"},
                {"event": "repair_reexecuted", "source": "repair"},
            ],
        },
    )
    orchestrator = FinancialOrchestrator(
        planner=FakePlanner(_plan("text_to_sql")),
        sql_tool=sql_tool,
        prospectus_tool=None,
    )

    result = orchestrator.answer("question")

    sql_stage = next(stage for stage in result["trace"]["stages"] if stage["stage"] == "sql_evidence")
    assert sql_stage["sql_source"] == "repair"
    assert sql_stage["accepted_result_kind"] is None
    assert sql_stage["final_failure_code"] == "all_candidates_failed"
    assert sql_stage["repair_attempts"] == 1
    assert sql_stage["fallback_attempts"] == [{"source": "repair", "failure_code": "execution_error"}]
    assert sql_stage["sql_route_events"] == [
        {"event": "candidate_generated", "source": "rule"},
        {"event": "repair_reexecuted", "source": "repair"},
    ]


def test_hybrid_trace_preserves_sql_route_metadata():
    sql_tool = RecordingSQLTool(
        [],
        metadata={
            "status": "failed",
            "sql_source": "api",
            "final_failure_code": "unsafe_sql",
            "accepted_result_kind": None,
            "fallback_attempts": [{"source": "api", "failure_code": "compile_failed"}],
            "sql_route_events": [{"event": "candidate_generated", "source": "api"}],
        },
    )
    prospectus_tool = RecordingProspectusTool([Evidence("txt-1", "text", "txt", "doc", "p.txt")])
    plan = _plan(
        "hybrid",
        hybrid_mode="sql_first",
        sub_questions=[
            {"path": "text_to_sql", "question": "resolve stock"},
            {"path": "pdf_rag", "question": "find disclosure"},
        ],
    )
    orchestrator = FinancialOrchestrator(FakePlanner(plan), sql_tool, prospectus_tool)

    result = orchestrator.answer("question")

    sql_stage = next(stage for stage in result["trace"]["stages"] if stage["stage"] == "sql_evidence")
    assert sql_stage["sql_source"] == "api"
    assert sql_stage["final_failure_code"] == "unsafe_sql"
    assert sql_stage["sql_route_events"] == [{"event": "candidate_generated", "source": "api"}]
