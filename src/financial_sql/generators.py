from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Callable, Protocol
import urllib.request

from src.financial_sql.agent_types import SQLCandidate, SQLSource


class SQLGenerator(Protocol):
    source: SQLSource

    def generate(self, plan: Any, question: str, context: dict[str, Any]) -> SQLCandidate | None:
        ...


class RuleSQLGenerator:
    source: SQLSource = "rule"

    def __init__(self, compile_fn: Callable[[Any], tuple[str, dict[str, Any]]]) -> None:
        self._compile_fn = compile_fn

    def generate(self, plan: Any, question: str, context: dict[str, Any]) -> SQLCandidate | None:
        sql, metadata = self._compile_fn(plan)
        return SQLCandidate(source="rule", sql=sql, metadata=metadata)


class LoraSQLGenerator:
    source: SQLSource = "lora"

    def __init__(self, endpoint: str, timeout_seconds: float = 10.0) -> None:
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def generate(self, plan: Any, question: str, context: dict[str, Any]) -> SQLCandidate | None:
        payload = {
            "question": question,
            "plan": _to_jsonable(plan),
            "context": context,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8").strip()
        if not raw:
            return None
        sql = _extract_sql(raw)
        if not sql:
            return None
        return SQLCandidate(source="lora", sql=sql, metadata={"endpoint": self.endpoint})


class ApiSQLGenerator:
    source: SQLSource = "api"

    def __init__(
        self,
        endpoint: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def generate(self, plan: Any, question: str, context: dict[str, Any]) -> SQLCandidate | None:
        payload = {
            "model": self.model,
            "question": question,
            "plan": _to_jsonable(plan),
            "context": context,
            "examples": context.get("examples", []),
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8").strip()
        if not raw:
            return None
        sql = _extract_sql(raw)
        if not sql:
            return None
        return SQLCandidate(source="api", sql=sql, metadata={"endpoint": self.endpoint, "model": self.model})


class SQLExampleRetriever:
    def __init__(self, examples_path: str | Path | None, top_k: int = 3) -> None:
        self.examples_path = Path(examples_path) if examples_path else None
        self.top_k = max(0, int(top_k))

    def retrieve(self, question: str) -> list[dict[str, str]]:
        if self.examples_path is None or self.top_k <= 0 or not self.examples_path.exists():
            return []
        payload = json.loads(self.examples_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return []
        examples = [item for item in payload if isinstance(item, dict) and item.get("question") and item.get("sql")]
        query_terms = _terms(question)
        ranked = sorted(
            examples,
            key=lambda item: _example_score(query_terms, str(item.get("question", ""))),
            reverse=True,
        )
        return [
            {"question": str(item["question"]), "sql": str(item["sql"])}
            for item in ranked[: self.top_k]
            if _example_score(query_terms, str(item.get("question", ""))) > 0
        ]


def _extract_sql(raw: str) -> str | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(payload, dict):
        value = payload.get("sql") or payload.get("query")
        return str(value).strip() if value else None
    if isinstance(payload, str):
        return payload.strip()
    return None


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return value


def _terms(text: str) -> set[str]:
    return {item.lower() for item in re.findall(r"[\w\u4e00-\u9fff]+", text)}


def _example_score(query_terms: set[str], question: str) -> int:
    if not query_terms:
        return 0
    return len(query_terms.intersection(_terms(question)))
