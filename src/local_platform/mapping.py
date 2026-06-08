from __future__ import annotations

from typing import Any


def map_chat_response(
    question: str,
    orchestrator_result: dict[str, Any] | None,
    latency_ms: int,
    error: dict[str, Any] | None = None,
    message_id: str | None = None,
) -> dict[str, Any]:
    if error:
        return {
            "id": message_id,
            "question": question,
            "answer": "",
            "sources": [],
            "question_plan": None,
            "verification_report": None,
            "trace": [],
            "latency_ms": latency_ms,
            "error": error,
        }

    result = orchestrator_result or {}
    return {
        "id": message_id,
        "question": question,
        "answer": str(result.get("answer") or ""),
        "sources": [_map_source(item) for item in result.get("sources") or []],
        "question_plan": result.get("question_plan"),
        "verification_report": result.get("verification_report"),
        "trace": result.get("trace") or [],
        "latency_ms": latency_ms,
        "error": None,
    }


def _map_source(source: dict[str, Any]) -> dict[str, Any]:
    metadata = source.get("metadata") or {}
    return {
        "id": source.get("evidence_id"),
        "kind": source.get("evidence_type"),
        "source_type": source.get("source_type"),
        "content": source.get("content"),
        "source": source.get("source"),
        "score": source.get("score"),
        "page": source.get("page"),
        "metadata": metadata,
        "evidence": source,
    }
