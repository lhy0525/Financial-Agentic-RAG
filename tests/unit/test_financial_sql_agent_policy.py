from __future__ import annotations

import io
import json

from src.financial_sql.fallback_policy import classify_terminal_outcome
from src.financial_sql.generators import ApiSQLGenerator, LoraSQLGenerator, SQLExampleRetriever


def test_empty_result_can_be_terminal_when_task_family_disallows_fallback():
    outcome = classify_terminal_outcome(
        status="empty",
        task_family="latest-record lookup",
        empty_result_policy="terminal",
    )

    assert outcome.accepted_result_kind == "empty"
    assert outcome.should_fallback is False
    assert outcome.failure_code == "empty_result"


def test_execution_error_is_fallback_eligible():
    outcome = classify_terminal_outcome(
        status="failed",
        task_family="point lookup",
        failure_code="execution_error",
        empty_result_policy="fallback",
    )

    assert outcome.accepted_result_kind is None
    assert outcome.should_fallback is True
    assert outcome.fallback_eligibility_reason == "repairable_failure"


def test_lora_sql_generator_posts_question_plan_and_returns_sql(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return io.BytesIO(json.dumps({"sql": "SELECT 1"}).encode("utf-8"))

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    candidate = LoraSQLGenerator("http://127.0.0.1:8888/SQL", timeout_seconds=1.5).generate(
        {"task_type": "raw_sql"},
        "question",
        {"reason": "fallback"},
    )

    assert candidate.sql == "SELECT 1"
    assert candidate.source == "lora"
    assert captured["url"] == "http://127.0.0.1:8888/SQL"
    assert captured["timeout"] == 1.5
    assert captured["body"]["question"] == "question"


def test_api_sql_generator_posts_model_and_examples(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return io.BytesIO(json.dumps({"sql": "SELECT api_value"}).encode("utf-8"))

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    candidate = ApiSQLGenerator(
        endpoint="http://127.0.0.1:9999/v1/sql",
        model="qwen-plus",
        api_key="secret",
        timeout_seconds=2.0,
    ).generate(
        {"task_type": "raw_sql"},
        "question",
        {"examples": [{"question": "old", "sql": "SELECT old"}]},
    )

    assert candidate.sql == "SELECT api_value"
    assert candidate.source == "api"
    assert captured["url"] == "http://127.0.0.1:9999/v1/sql"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["body"]["model"] == "qwen-plus"
    assert captured["body"]["examples"] == [{"question": "old", "sql": "SELECT old"}]
    assert captured["timeout"] == 2.0


def test_sql_example_retriever_returns_keyword_matches(tmp_path):
    examples_file = tmp_path / "examples.json"
    examples_file.write_text(
        json.dumps(
            [
                {"question": "stock close price", "sql": "SELECT close"},
                {"question": "fund holding ranking", "sql": "SELECT holding"},
            ]
        ),
        encoding="utf-8",
    )

    examples = SQLExampleRetriever(examples_file, top_k=1).retrieve("latest fund holding")

    assert examples == [{"question": "fund holding ranking", "sql": "SELECT holding"}]
