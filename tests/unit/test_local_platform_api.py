from __future__ import annotations

from fastapi.testclient import TestClient

import src.local_platform.api as api_module
from src.local_platform.api import create_app
from src.local_platform.config import PlatformConfig
from src.local_platform.service import UploadParseError, UploadStorageError


class FakeService:
    def __init__(self) -> None:
        self.questions: list[str] = []
        self.uploads: list[tuple[str, bytes]] = []

    def health(self) -> dict:
        return {
            "status": "ready",
            "ready": True,
            "dependencies": {"sql_database": {"ready": True}},
            "configuration": {"sql_db_path_source": "test"},
        }

    def platform(self) -> dict:
        return {
            "session": {"label": "Local demo", "mode": "no-login"},
            "system_status": {"label": "SQL-first local Agentic RAG", "ready": True},
            "feature_flags": {"auth": False, "upload_pdf": False, "prospectus_evidence": False},
            "knowledge_base": {"sql_database": {"ready": True}},
            "architecture_docs": {"available": True, "links": []},
        }

    def answer(self, question: str) -> dict:
        self.questions.append(question)
        return {
            "id": "chat-1",
            "question": question,
            "answer": "mock answer",
            "sources": [],
            "question_plan": {"route": "text_to_sql"},
            "verification_report": {"status": "pass"},
            "trace": [],
            "latency_ms": 1,
            "error": None,
        }

    def upload_prospectus(self, filename: str, content: bytes) -> dict:
        self.uploads.append((filename, content))
        return {
            "status": "indexed_searchable",
            "filename": filename,
            "saved_path": f"uploads/{filename}",
            "document_id": "txt_123",
            "doc_type": "prospectus_txt",
            "text_length": len(content),
            "table_placeholders": [],
            "collection": "prospectus_uploads",
            "chunk_count": 1,
            "vector_count": 1,
            "indexed": True,
            "searchable": True,
            "index_ready": True,
            "search_ready": True,
            "prospectus_enabled": False,
        }


def _client(service: FakeService) -> TestClient:
    config = PlatformConfig(
        sql_db_path=None,
        sql_db_path_source=None,
        ready=False,
        diagnostics={"missing": ["sql_db_path"], "invalid": []},
        host="127.0.0.1",
        port=8010,
        cors_origins=["http://localhost:5173"],
        upload_dir=None,
    )
    return TestClient(create_app(config=config, service=service))


def test_health_and_platform_endpoints_return_shell_fields():
    service = FakeService()
    client = _client(service)

    health = client.get("/api/health")
    platform = client.get("/api/platform")

    assert health.status_code == 200
    assert set(health.json()) == {"status", "ready", "dependencies", "configuration"}
    assert platform.status_code == 200
    assert set(platform.json()) == {
        "session",
        "system_status",
        "feature_flags",
        "knowledge_base",
        "architecture_docs",
    }


def test_cors_allows_local_vite_dev_origin():
    service = FakeService()
    client = _client(service)

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_chat_rejects_empty_question_without_invoking_service():
    service = FakeService()
    client = _client(service)

    response = client.post("/api/chat", json={"question": "   "})

    assert response.status_code == 422
    assert service.questions == []


def test_chat_response_is_stored_in_in_memory_history_and_can_be_cleared():
    service = FakeService()
    client = _client(service)

    chat = client.post("/api/chat", json={"question": "Show revenue"})
    history = client.get("/api/history")
    cleared = client.delete("/api/history")

    assert chat.status_code == 200
    assert chat.json()["answer"] == "mock answer"
    assert history.json()["messages"][0]["question"] == "Show revenue"
    assert cleared.json() == {"cleared": True}
    assert client.get("/api/history").json() == {"messages": []}


def test_chat_offloads_blocking_answer_work(monkeypatch):
    service = FakeService()
    calls = []

    async def fake_to_thread(func, *args):
        calls.append((func, args))
        return func(*args)

    monkeypatch.setattr(api_module.asyncio, "to_thread", fake_to_thread)
    client = _client(service)

    response = client.post("/api/chat", json={"question": "Show revenue"})

    assert response.status_code == 200
    assert calls == [(service.answer, ("Show revenue",))]


def test_prospectus_upload_accepts_multipart_file():
    service = FakeService()
    client = _client(service)

    response = client.post(
        "/api/prospectus/upload",
        files={"file": ("sample.txt", b"Prospectus text", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "indexed_searchable"
    assert response.json()["collection"] == "prospectus_uploads"
    assert response.json()["indexed"] is True
    assert response.json()["searchable"] is True
    assert service.uploads == [("sample.txt", b"Prospectus text")]


def test_prospectus_upload_can_return_already_indexed_status():
    service = FakeService()

    def duplicate_upload(filename: str, content: bytes) -> dict:
        service.uploads.append((filename, content))
        return {
            "status": "already_indexed",
            "filename": filename,
            "document_id": "txt_existing",
            "collection": "prospectus_uploads",
            "indexed": True,
            "searchable": True,
            "index_ready": True,
            "search_ready": True,
        }

    service.upload_prospectus = duplicate_upload
    client = _client(service)

    response = client.post(
        "/api/prospectus/upload",
        files={"file": ("sample.txt", b"Prospectus text", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "already_indexed"
    assert response.json()["indexed"] is True
    assert response.json()["searchable"] is True


def test_prospectus_upload_returns_index_failed_as_partial_success():
    service = FakeService()

    def failed_index(filename: str, content: bytes) -> dict:
        service.uploads.append((filename, content))
        return {
            "status": "index_failed",
            "filename": filename,
            "document_id": "txt_123",
            "collection": "prospectus_uploads",
            "indexed": False,
            "searchable": False,
            "index_ready": False,
            "search_ready": False,
            "diagnostics": ["embedding provider unavailable"],
            "error": "embedding provider unavailable",
        }

    service.upload_prospectus = failed_index
    client = _client(service)

    response = client.post(
        "/api/prospectus/upload",
        files={"file": ("sample.txt", b"Prospectus text", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "index_failed"
    assert response.json()["indexed"] is False
    assert response.json()["searchable"] is False
    assert response.json()["diagnostics"] == ["embedding provider unavailable"]


def test_prospectus_upload_rejects_unsupported_file():
    service = FakeService()
    client = _client(service)

    response = client.post(
        "/api/prospectus/upload",
        files={"file": ("sample.docx", b"not supported", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert ".pdf" in response.json()["detail"]
    assert ".txt" in response.json()["detail"]
    assert service.uploads == []


def test_prospectus_upload_rejects_missing_file_with_readable_error():
    service = FakeService()
    client = _client(service)

    response = client.post("/api/prospectus/upload")

    assert response.status_code == 422
    assert response.json()["detail"] == "Upload file is required."
    assert service.uploads == []


def test_prospectus_upload_reports_parse_failures_with_readable_error():
    service = FakeService()

    def broken_upload(filename: str, content: bytes) -> dict:
        raise UploadParseError("sample.txt could not be parsed: parser dependency missing")

    service.upload_prospectus = broken_upload
    client = _client(service)

    response = client.post(
        "/api/prospectus/upload",
        files={"file": ("sample.txt", b"bad", "text/plain")},
    )

    assert response.status_code == 422
    assert "could not be parsed" in response.json()["detail"]


def test_prospectus_upload_reports_storage_failures_with_readable_error():
    service = FakeService()

    def broken_upload(filename: str, content: bytes) -> dict:
        raise UploadStorageError("sample.txt could not be saved: upload directory unavailable")

    service.upload_prospectus = broken_upload
    client = _client(service)

    response = client.post(
        "/api/prospectus/upload",
        files={"file": ("sample.txt", b"bad", "text/plain")},
    )

    assert response.status_code == 422
    assert "could not be saved" in response.json()["detail"]
