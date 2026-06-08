from __future__ import annotations

from src.local_platform.mapping import map_chat_response


def test_map_chat_response_includes_stable_contract_fields():
    result = {
        "answer": "A structured answer",
        "sources": [
            {
                "evidence_id": "sql-1",
                "evidence_type": "sql_result",
                "source_type": "db",
                "content": '[{"value": 1}]',
                "source": "financial.db",
                "metadata": {"sql": "select 1", "rows": [{"value": 1}]},
            }
        ],
        "question_plan": {"route": "text_to_sql", "task_type": "point_lookup"},
        "verification_report": {"status": "pass", "notes": []},
        "trace": {"tool_sequence": ["plan", "text_to_sql", "answer"]},
    }

    response = map_chat_response(
        question="What happened?",
        orchestrator_result=result,
        latency_ms=42,
    )

    assert response["answer"] == "A structured answer"
    assert response["sources"][0]["id"] == "sql-1"
    assert response["sources"][0]["kind"] == "sql_result"
    assert response["sources"][0]["metadata"]["rows"] == [{"value": 1}]
    assert response["question_plan"] == {"route": "text_to_sql", "task_type": "point_lookup"}
    assert response["verification_report"] == {"status": "pass", "notes": []}
    assert response["trace"] == {"tool_sequence": ["plan", "text_to_sql", "answer"]}
    assert response["latency_ms"] == 42
    assert response["error"] is None


def test_map_chat_response_can_return_readable_error_payload():
    response = map_chat_response(
        question="What happened?",
        orchestrator_result=None,
        latency_ms=5,
        error={"code": "configuration_error", "message": "Database path is not configured"},
    )

    assert response["answer"] == ""
    assert response["sources"] == []
    assert response["question_plan"] is None
    assert response["verification_report"] is None
    assert response["trace"] == []
    assert response["latency_ms"] == 5
    assert response["error"] == {
        "code": "configuration_error",
        "message": "Database path is not configured",
    }


def test_map_chat_response_preserves_uploaded_prospectus_source_metadata():
    result = {
        "answer": "The uploaded prospectus mentions liquidity risk.",
        "sources": [
            {
                "evidence_id": "prospectus-1",
                "evidence_type": "text",
                "source_type": "pdf",
                "content": "liquidity risk",
                "source": "uploads/prospectus.pdf",
                "metadata": {
                    "collection": "prospectus_uploads",
                    "local_origin": "ui_upload",
                    "document_id": "doc_uploaded",
                },
            }
        ],
        "question_plan": {"route": "pdf_rag", "task_type": "disclosure_lookup"},
        "verification_report": {"status": "pass"},
        "trace": {"tool_sequence": ["plan", "pdf_rag", "verify"]},
    }

    response = map_chat_response("risk?", result, latency_ms=12)

    source = response["sources"][0]
    assert source["id"] == "prospectus-1"
    assert source["source"] == "uploads/prospectus.pdf"
    assert source["metadata"]["collection"] == "prospectus_uploads"
    assert source["metadata"]["local_origin"] == "ui_upload"
    assert source["metadata"]["document_id"] == "doc_uploaded"
