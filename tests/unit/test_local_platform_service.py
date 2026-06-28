from __future__ import annotations

import sqlite3

from src.local_platform.config import PlatformConfig
from src.local_platform.service import (
    LocalFinancialPlatformService,
    UploadParseError,
    UploadStorageError,
    UnsupportedUploadError,
)


def _config(db_path, prospectus_enabled=False):
    return PlatformConfig(
        sql_db_path=db_path,
        sql_db_path_source="test",
        ready=db_path is not None,
        diagnostics={"missing": [], "invalid": []},
        host="127.0.0.1",
        port=8010,
        cors_origins=["http://localhost:5173"],
        prospectus_enabled=prospectus_enabled,
        upload_dir=db_path.parent / "uploads" if db_path is not None else None,
    )


class FakeProspectusIndexService:
    collection = "prospectus_uploads"

    def __init__(self, upload_result=None, index_ready=True, upload_ready=True):
        self.upload_result = upload_result or {
            "status": "indexed_searchable",
            "collection": self.collection,
            "document_id": "doc_indexed",
            "doc_type": "prospectus_txt",
            "chunk_count": 2,
            "vector_count": 2,
            "indexed": True,
            "searchable": True,
            "index_ready": True,
            "search_ready": True,
            "local_origin": "ui_upload",
            "diagnostics": [],
        }
        self.index_ready = index_ready
        self.upload_ready = upload_ready
        self.index_calls = []

    def index_file(self, file_path, *, suffix, origin="ui_upload", force=False):
        self.index_calls.append(
            {"file_path": file_path, "suffix": suffix, "origin": origin, "force": force}
        )
        return self.upload_result

    def prospectus_index_status(self):
        return {
            "ready": self.index_ready,
            "enabled": True,
            "status": "ready" if self.index_ready else "not_ready",
            "collection": self.collection,
            "index_ready": self.index_ready,
            "search_ready": self.index_ready,
            "searchable": self.index_ready,
            "retrieval_paths": {
                "dense": {"ready": self.index_ready, "chunk_count": 2 if self.index_ready else 0},
                "sparse": {"ready": self.index_ready, "document_count": 1 if self.index_ready else 0},
                "hybrid": {"ready": self.index_ready},
            },
            "chunk_count": 2 if self.index_ready else 0,
            "document_count": 1 if self.index_ready else 0,
            "diagnostics": [] if self.index_ready else ["No indexed prospectus chunks found."],
        }

    def local_upload_indexing_status(self, upload_dir):
        return {
            "ready": self.upload_ready,
            "enabled": True,
            "status": "ready" if self.upload_ready else "unavailable",
            "collection": self.collection,
            "upload_dir": str(upload_dir),
            "writable": self.upload_ready,
            "indexing_enabled": True,
            "diagnostics": [] if self.upload_ready else ["upload directory is not writable"],
        }

    def build_tool(self):
        return object()


def test_service_constructs_sql_first_orchestrator_from_existing_components(tmp_path, monkeypatch):
    db_path = tmp_path / "financial.db"
    sqlite3.connect(db_path).close()
    constructed = {}

    class FakePlanner:
        pass

    class FakeSQLTool:
        def __init__(self, path, **kwargs):
            constructed["sql_path"] = path
            constructed["sql_kwargs"] = kwargs

    class FakeOrchestrator:
        def __init__(self, planner, sql_tool, prospectus_tool):
            constructed["planner"] = planner
            constructed["sql_tool"] = sql_tool
            constructed["prospectus_tool"] = prospectus_tool

        def answer(self, question):
            return {
                "answer": f"answered {question}",
                "sources": [],
                "question_plan": {"route": "text_to_sql"},
                "verification_report": {"status": "pass"},
                "trace": {"tool_sequence": ["plan", "text_to_sql"]},
            }

    monkeypatch.setattr("src.local_platform.service.FinancialQuestionPlanner", FakePlanner)
    monkeypatch.setattr("src.local_platform.service.TextToSQLEvidenceTool", FakeSQLTool)
    monkeypatch.setattr("src.local_platform.service.FinancialOrchestrator", FakeOrchestrator)

    response = LocalFinancialPlatformService(_config(db_path)).answer("question")

    assert response["answer"] == "answered question"
    assert constructed["sql_path"] == db_path
    assert "agent_config" in constructed["sql_kwargs"]
    assert isinstance(constructed["planner"], FakePlanner)
    assert isinstance(constructed["sql_tool"], FakeSQLTool)
    assert constructed["prospectus_tool"] is None


def test_service_uses_configured_prospectus_tool_factory_for_orchestrator(tmp_path, monkeypatch):
    db_path = tmp_path / "financial.db"
    sqlite3.connect(db_path).close()
    prospectus_tool = object()
    constructed = {}

    class FakeOrchestrator:
        def __init__(self, planner, sql_tool, prospectus_tool):
            constructed["prospectus_tool"] = prospectus_tool

        def answer(self, question):
            return {
                "answer": "ok",
                "sources": [],
                "question_plan": {"route": "hybrid"},
                "verification_report": {"status": "pass"},
                "trace": {"tool_sequence": ["plan", "pdf_rag"]},
            }

    monkeypatch.setattr("src.local_platform.service.FinancialOrchestrator", FakeOrchestrator)

    service = LocalFinancialPlatformService(
        _config(db_path, prospectus_enabled=True),
        prospectus_tool_factory=lambda: prospectus_tool,
        prospectus_index_ready=True,
    )
    platform = service.platform()
    response = service.answer("hybrid question")

    assert platform["feature_flags"]["prospectus_evidence"] is True
    assert platform["knowledge_base"]["prospectus_evidence"]["ready"] is True
    assert response["answer"] == "ok"
    assert constructed["prospectus_tool"] is prospectus_tool


def test_service_rebuilds_cached_orchestrator_when_prospectus_index_becomes_ready(tmp_path, monkeypatch):
    db_path = tmp_path / "financial.db"
    sqlite3.connect(db_path).close()
    prospectus_tool = object()
    constructed_tools = []

    class FakeOrchestrator:
        def __init__(self, planner, sql_tool, prospectus_tool):
            self.prospectus_tool = prospectus_tool
            constructed_tools.append(prospectus_tool)

        def answer(self, question):
            return {
                "answer": "ok",
                "sources": [],
                "question_plan": {"route": "text_to_sql"},
                "verification_report": {"status": "pass"},
                "trace": {"tool_sequence": ["plan", "text_to_sql"]},
            }

    monkeypatch.setattr("src.local_platform.service.FinancialOrchestrator", FakeOrchestrator)
    index_service = FakeProspectusIndexService(index_ready=False)
    service = LocalFinancialPlatformService(
        _config(db_path, prospectus_enabled=True),
        prospectus_tool_factory=lambda: prospectus_tool,
        prospectus_index_service=index_service,
    )

    service.answer("sql question before upload")
    index_service.index_ready = True
    service.answer("prospectus question after upload")

    assert constructed_tools == [None, prospectus_tool]


def test_prospectus_flag_is_unavailable_when_enabled_without_tool_factory(tmp_path):
    db_path = tmp_path / "financial.db"
    sqlite3.connect(db_path).close()

    platform = LocalFinancialPlatformService(
        _config(db_path, prospectus_enabled=True),
        prospectus_tool_factory=None,
        prospectus_index_service=FakeProspectusIndexService(index_ready=True),
    ).platform()

    assert platform["feature_flags"]["prospectus_evidence"] is True
    assert platform["knowledge_base"]["prospectus_evidence"]["ready"] is True
    assert platform["knowledge_base"]["prospectus_evidence"]["status"] == "ready"


def test_prospectus_flag_is_unavailable_without_index_readiness(tmp_path):
    db_path = tmp_path / "financial.db"
    sqlite3.connect(db_path).close()

    platform = LocalFinancialPlatformService(
        _config(db_path, prospectus_enabled=True),
        prospectus_tool_factory=lambda: object(),
        prospectus_index_service=FakeProspectusIndexService(index_ready=False),
    ).platform()

    assert platform["feature_flags"]["prospectus_evidence"] is False
    assert platform["knowledge_base"]["prospectus_evidence"]["ready"] is False
    assert platform["knowledge_base"]["prospectus_evidence"]["status"] == "index_not_ready"


def test_prospectus_flag_is_unavailable_when_tool_construction_fails(tmp_path):
    db_path = tmp_path / "financial.db"
    sqlite3.connect(db_path).close()

    def broken_tool_factory():
        raise RuntimeError("hybrid search dependencies unavailable")

    platform = LocalFinancialPlatformService(
        _config(db_path, prospectus_enabled=True),
        prospectus_tool_factory=broken_tool_factory,
        prospectus_index_ready=True,
        prospectus_index_service=FakeProspectusIndexService(index_ready=True),
    ).platform()

    assert platform["feature_flags"]["prospectus_evidence"] is False
    assert platform["knowledge_base"]["prospectus_evidence"]["ready"] is False
    assert platform["knowledge_base"]["prospectus_evidence"]["status"] == "unavailable"
    assert platform["knowledge_base"]["prospectus_evidence"]["diagnostics"] == [
        "hybrid search dependencies unavailable"
    ]


def test_service_uploads_txt_prospectus_saves_and_reports_not_indexed(tmp_path):
    upload_dir = tmp_path / "uploads"
    config = PlatformConfig(
        sql_db_path=None,
        sql_db_path_source=None,
        ready=False,
        diagnostics={"missing": ["sql_db_path"], "invalid": []},
        upload_dir=upload_dir,
    )
    index_service = FakeProspectusIndexService()
    service = LocalFinancialPlatformService(config, prospectus_index_service=index_service)

    response = service.upload_prospectus(
        "sample.txt",
        b"Fund overview\n<|TABLE_1|>\nRisk factors",
    )

    saved_path = upload_dir / "sample.txt"
    assert saved_path.read_text(encoding="utf-8") == "Fund overview\n<|TABLE_1|>\nRisk factors"
    assert response["status"] == "indexed_searchable"
    assert response["filename"] == "sample.txt"
    assert response["saved_path"] == str(saved_path)
    assert response["document_id"] == "doc_indexed"
    assert response["doc_type"] == "prospectus_txt"
    assert response["text_length"] == len("Fund overview\n<|TABLE_1|>\nRisk factors")
    assert response["table_placeholders"] == ["TABLE_1"]
    assert response["collection"] == "prospectus_uploads"
    assert response["chunk_count"] == 2
    assert response["vector_count"] == 2
    assert response["indexed"] is True
    assert response["searchable"] is True
    assert response["prospectus_enabled"] is False
    assert index_service.index_calls == [
        {
            "file_path": saved_path,
            "suffix": ".txt",
            "origin": "ui_upload",
            "force": False,
        }
    ]


def test_service_upload_reports_index_failure_without_losing_parse_metadata(tmp_path):
    upload_dir = tmp_path / "uploads"
    config = PlatformConfig(
        sql_db_path=None,
        sql_db_path_source=None,
        ready=False,
        diagnostics={"missing": ["sql_db_path"], "invalid": []},
        upload_dir=upload_dir,
    )
    index_service = FakeProspectusIndexService(
        upload_result={
            "status": "index_failed",
            "collection": "prospectus_uploads",
            "document_id": None,
            "doc_type": "txt",
            "chunk_count": 0,
            "vector_count": 0,
            "indexed": False,
            "searchable": False,
            "index_ready": False,
            "search_ready": False,
            "local_origin": "ui_upload",
            "diagnostics": ["embedding provider unavailable"],
            "error": "embedding provider unavailable",
        },
        index_ready=False,
    )
    service = LocalFinancialPlatformService(config, prospectus_index_service=index_service)

    response = service.upload_prospectus("sample.txt", b"Fund overview")

    assert response["status"] == "index_failed"
    assert response["filename"] == "sample.txt"
    assert response["document_id"].startswith("txt_")
    assert response["text_length"] == len("Fund overview")
    assert response["indexed"] is False
    assert response["searchable"] is False
    assert response["diagnostics"] == ["embedding provider unavailable"]


def test_service_upload_reports_already_indexed_duplicate_as_searchable(tmp_path):
    upload_dir = tmp_path / "uploads"
    config = PlatformConfig(
        sql_db_path=None,
        sql_db_path_source=None,
        ready=False,
        diagnostics={"missing": ["sql_db_path"], "invalid": []},
        upload_dir=upload_dir,
    )
    service = LocalFinancialPlatformService(
        config,
        prospectus_index_service=FakeProspectusIndexService(
            upload_result={
                "status": "already_indexed",
                "collection": "prospectus_uploads",
                "document_id": "doc_existing",
                "doc_type": "prospectus_txt",
                "chunk_count": 0,
                "vector_count": 0,
                "indexed": True,
                "searchable": True,
                "index_ready": True,
                "search_ready": True,
                "local_origin": "ui_upload",
                "diagnostics": [],
            }
        ),
    )

    response = service.upload_prospectus("sample.txt", b"Fund overview")

    assert response["status"] == "already_indexed"
    assert response["document_id"] == "doc_existing"
    assert response["indexed"] is True
    assert response["searchable"] is True


def test_service_returns_readable_answer_error_when_prospectus_retrieval_fails(tmp_path):
    db_path = tmp_path / "financial.db"
    sqlite3.connect(db_path).close()

    class BrokenOrchestrator:
        def answer(self, question):
            raise RuntimeError("prospectus retrieval failed")

    service = LocalFinancialPlatformService(
        _config(db_path, prospectus_enabled=True),
        orchestrator=BrokenOrchestrator(),
        prospectus_index_service=FakeProspectusIndexService(index_ready=True),
    )

    response = service.answer("prospectus question")

    assert response["answer"] == ""
    assert response["sources"] == []
    assert response["error"]["code"] == "answer_error"
    assert "prospectus retrieval failed" in response["error"]["message"]


def test_service_upload_rejects_unsupported_extension(tmp_path):
    service = LocalFinancialPlatformService(
        PlatformConfig(
            sql_db_path=None,
            sql_db_path_source=None,
            ready=False,
            diagnostics={"missing": ["sql_db_path"], "invalid": []},
            upload_dir=tmp_path / "uploads",
        )
    )

    try:
        service.upload_prospectus("sample.docx", b"content")
    except UnsupportedUploadError as exc:
        assert ".pdf" in str(exc)
        assert ".txt" in str(exc)
    else:
        raise AssertionError("Expected unsupported uploads to be rejected")


def test_service_upload_reports_readable_parse_failure(tmp_path, monkeypatch):
    service = LocalFinancialPlatformService(
        PlatformConfig(
            sql_db_path=None,
            sql_db_path_source=None,
            ready=False,
            diagnostics={"missing": ["sql_db_path"], "invalid": []},
            upload_dir=tmp_path / "uploads",
        )
    )

    class BrokenTxtLoader:
        def load(self, path):
            raise RuntimeError("parser dependency missing")

    monkeypatch.setattr("src.local_platform.service.ProspectusTxtLoader", BrokenTxtLoader)

    try:
        service.upload_prospectus("sample.txt", b"content")
    except UploadParseError as exc:
        assert "could not be parsed" in str(exc)
        assert "parser dependency missing" in str(exc)
    else:
        raise AssertionError("Expected parse failures to be readable")


def test_service_upload_reports_readable_storage_failure(tmp_path):
    upload_path = tmp_path / "not_a_directory"
    upload_path.write_text("already a file", encoding="utf-8")
    service = LocalFinancialPlatformService(
        PlatformConfig(
            sql_db_path=None,
            sql_db_path_source=None,
            ready=False,
            diagnostics={"missing": ["sql_db_path"], "invalid": []},
            upload_dir=upload_path,
        )
    )

    health = service.health()
    upload_health = health["dependencies"]["local_upload"]

    assert upload_health["enabled"] is True
    assert upload_health["ready"] is False
    assert upload_health["status"] == "unavailable"
    assert "not_a_directory" in upload_health["error"]

    try:
        service.upload_prospectus("sample.txt", b"content")
    except UploadStorageError as exc:
        assert "could not be saved" in str(exc)
    else:
        raise AssertionError("Expected storage failures to be readable")


def test_local_upload_metadata_is_ready_for_accepting_files_but_not_searchable(tmp_path):
    config = PlatformConfig(
        sql_db_path=None,
        sql_db_path_source=None,
        ready=False,
        diagnostics={"missing": ["sql_db_path"], "invalid": []},
        upload_dir=tmp_path / "uploads",
        prospectus_enabled=False,
    )

    service = LocalFinancialPlatformService(
        config,
        prospectus_index_service=FakeProspectusIndexService(index_ready=False, upload_ready=True),
    )
    health = service.health()
    platform = service.platform()

    upload_health = health["dependencies"]["local_upload"]
    assert upload_health["enabled"] is True
    assert upload_health["ready"] is True
    assert upload_health["indexed"] is False
    assert upload_health["searchable"] is False
    assert health["dependencies"]["prospectus_evidence"]["enabled"] is False
    assert health["dependencies"]["prospectus_evidence"]["ready"] is False
    assert platform["feature_flags"]["upload_pdf"] is True
    assert platform["knowledge_base"]["local_upload"]["searchable"] is False
    assert health["dependencies"]["prospectus_index"]["ready"] is False
    assert health["dependencies"]["local_upload_indexing"]["ready"] is True


def test_platform_reports_prospectus_index_ready_separately_from_upload_indexing(tmp_path):
    db_path = tmp_path / "financial.db"
    sqlite3.connect(db_path).close()
    service = LocalFinancialPlatformService(
        _config(db_path, prospectus_enabled=True),
        prospectus_index_service=FakeProspectusIndexService(index_ready=True, upload_ready=False),
    )

    health = service.health()

    assert health["ready"] is True
    assert health["dependencies"]["sql_database"]["ready"] is True
    assert health["dependencies"]["prospectus_evidence"]["ready"] is True
    assert health["dependencies"]["prospectus_index"]["ready"] is True
    assert health["dependencies"]["prospectus_index"]["collection"] == "prospectus_uploads"
    assert health["dependencies"]["local_upload_indexing"]["ready"] is False
    assert health["dependencies"]["local_upload_indexing"]["diagnostics"] == [
        "upload directory is not writable"
    ]
