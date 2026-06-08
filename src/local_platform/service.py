from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.agentic.orchestrator import FinancialOrchestrator
from src.agentic.planner import FinancialQuestionPlanner
from src.financial_sql.text_to_sql_tool import TextToSQLEvidenceTool
from src.libs.loader.pdf_loader import PdfLoader
from src.local_platform.config import PlatformConfig
from src.local_platform.mapping import map_chat_response
from src.local_platform.prospectus_index import LocalProspectusIndexService
from src.prospectus_evidence.txt_loader import ProspectusTxtLoader


class PlatformConfigurationError(RuntimeError):
    pass


class UnsupportedUploadError(ValueError):
    pass


class UploadParseError(RuntimeError):
    pass


class UploadStorageError(RuntimeError):
    pass


class LocalFinancialPlatformService:
    def __init__(
        self,
        config: PlatformConfig,
        orchestrator: FinancialOrchestrator | None = None,
        prospectus_tool_factory: Any | None = None,
        prospectus_index_ready: bool = False,
        prospectus_index_service: Any | None = None,
        docs_root: Path | None = None,
    ) -> None:
        self.config = config
        self._orchestrator = orchestrator
        self._prospectus_index_service = prospectus_index_service or LocalProspectusIndexService(
            settings_path=config.settings_path,
            collection=config.prospectus_collection,
            indexing_enabled=config.prospectus_indexing_enabled,
        )
        self._prospectus_tool_factory = prospectus_tool_factory or self._prospectus_index_service.build_tool
        self._manual_prospectus_index_ready = prospectus_index_ready
        self._cached_prospectus_tool: Any | None = None
        self._prospectus_tool_error: str | None = None
        self._orchestrator_has_prospectus_tool = orchestrator is not None
        self.docs_root = docs_root or Path(__file__).resolve().parents[2] / "docs" / "financial"

    def health(self) -> dict[str, Any]:
        sql_ready = self.config.ready
        prospectus_index = self._prospectus_index_status()
        local_upload_indexing = self._local_upload_indexing_status()
        return {
            "status": "ready" if sql_ready else "not_ready",
            "ready": sql_ready,
            "dependencies": {
                "sql_database": {
                    "ready": sql_ready,
                    "path": str(self.config.sql_db_path) if self.config.sql_db_path else None,
                    "source": self.config.sql_db_path_source,
                    "missing": "sql_db_path" in self.config.diagnostics.get("missing", []),
                    "invalid": self.config.diagnostics.get("invalid", []),
                },
                "prospectus_evidence": {
                    "ready": self._prospectus_ready,
                    "enabled": self.config.prospectus_enabled,
                    "status": self._prospectus_status,
                    "diagnostics": [self._prospectus_tool_error] if self._prospectus_tool_error else [],
                },
                "local_upload": self._local_upload_status(),
                "prospectus_index": prospectus_index,
                "local_upload_indexing": local_upload_indexing,
            },
            "configuration": {
                "sql_db_path": str(self.config.sql_db_path) if self.config.sql_db_path else None,
                "sql_db_path_source": self.config.sql_db_path_source,
                "diagnostics": self.config.diagnostics,
                "host": self.config.host,
                "cors_origins": self.config.cors_origins,
                "upload_dir": str(self._upload_dir),
                "prospectus_collection": self.config.prospectus_collection,
                "prospectus_indexing_enabled": self.config.prospectus_indexing_enabled,
            },
        }

    def platform(self) -> dict[str, Any]:
        health = self.health()
        return {
            "session": {
                "label": "Local demo session",
                "mode": "no-login",
                "user": "Local Financial Analyst",
            },
            "system_status": {
                "label": "SQL-first local financial Agentic RAG",
                "ready": health["ready"],
                "status": health["status"],
            },
            "feature_flags": {
                "auth": False,
                "jwt": False,
                "upload_pdf": True,
                "prospectus_evidence": self._prospectus_ready,
                "numeric_confidence": False,
            },
            "knowledge_base": health["dependencies"],
            "architecture_docs": self._architecture_docs(),
        }

    def upload_prospectus(self, filename: str, content: bytes) -> dict[str, Any]:
        clean_name = Path(filename or "").name
        suffix = Path(clean_name).suffix.lower()
        if not clean_name or suffix not in {".pdf", ".txt"}:
            raise UnsupportedUploadError("Unsupported file type. Upload a .pdf or .txt file.")

        upload_dir = self._upload_dir
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
            saved_path = upload_dir / clean_name
            saved_path.write_bytes(content)
        except OSError as exc:
            raise UploadStorageError(f"{clean_name} could not be saved: {exc}") from exc

        try:
            if suffix == ".txt":
                document = ProspectusTxtLoader().load(saved_path)
            else:
                document = PdfLoader().load(saved_path)
        except Exception as exc:
            raise UploadParseError(f"{clean_name} could not be parsed: {exc}") from exc

        table_placeholders = document.metadata.get("table_placeholders", [])
        if not isinstance(table_placeholders, list):
            table_placeholders = []

        index_result = self._prospectus_index_service.index_file(
            saved_path,
            suffix=suffix,
            origin="ui_upload",
        )

        return {
            "status": "uploaded_parsed_not_indexed",
            "filename": clean_name,
            "saved_path": str(saved_path),
            "document_id": document.metadata.get("document_id") or document.id,
            "doc_type": document.metadata.get("doc_type") or suffix.lstrip("."),
            "text_length": len(document.text),
            "table_placeholders": [str(item) for item in table_placeholders],
            "indexed": False,
            "searchable": False,
            "index_ready": False,
            "search_ready": False,
            "prospectus_enabled": self._prospectus_ready,
            **index_result,
            "filename": clean_name,
            "saved_path": str(saved_path),
            "document_id": index_result.get("document_id")
            or document.metadata.get("document_id")
            or document.id,
            "doc_type": document.metadata.get("doc_type") or index_result.get("doc_type") or suffix.lstrip("."),
            "text_length": len(document.text),
            "table_placeholders": [str(item) for item in table_placeholders],
            "prospectus_enabled": self._prospectus_ready,
        }

    def answer(self, question: str) -> dict[str, Any]:
        start = time.perf_counter()
        message_id = f"chat-{uuid4().hex}"
        try:
            orchestrator = self._get_orchestrator()
            result = orchestrator.answer(question)
            latency_ms = int((time.perf_counter() - start) * 1000)
            return map_chat_response(question, result, latency_ms, message_id=message_id)
        except PlatformConfigurationError as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return map_chat_response(
                question,
                None,
                latency_ms,
                message_id=message_id,
                error={"code": "configuration_error", "message": str(exc)},
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return map_chat_response(
                question,
                None,
                latency_ms,
                message_id=message_id,
                error={"code": "answer_error", "message": str(exc)},
            )

    def _get_orchestrator(self) -> FinancialOrchestrator:
        if self._orchestrator is not None:
            if self._prospectus_ready and not self._orchestrator_has_prospectus_tool:
                self._orchestrator = None
            else:
                return self._orchestrator
        if self._orchestrator is not None:
            return self._orchestrator
        if not self.config.ready or self.config.sql_db_path is None:
            raise PlatformConfigurationError(
                "SQL database path is not configured or is invalid. Set FINANCIAL_DEMO_DB_PATH "
                "or financial_platform.sql_db_path in config/settings.yaml."
            )
        prospectus_tool = self._build_prospectus_tool()
        self._orchestrator = FinancialOrchestrator(
            planner=FinancialQuestionPlanner(),
            sql_tool=TextToSQLEvidenceTool(self.config.sql_db_path),
            prospectus_tool=prospectus_tool,
        )
        self._orchestrator_has_prospectus_tool = prospectus_tool is not None
        return self._orchestrator

    def _build_prospectus_tool(self) -> Any | None:
        if not self._prospectus_ready:
            return None
        return self._ensure_prospectus_tool()

    @property
    def _prospectus_ready(self) -> bool:
        return bool(
            self.config.prospectus_enabled
            and self._prospectus_tool_factory is not None
            and self._prospectus_index_ready
            and self._ensure_prospectus_tool() is not None
        )

    @property
    def _prospectus_index_ready(self) -> bool:
        if self._manual_prospectus_index_ready:
            return True
        return bool(self._prospectus_index_status().get("ready"))

    @property
    def _prospectus_status(self) -> str:
        if self._prospectus_ready:
            return "ready"
        if self.config.prospectus_enabled:
            if self._prospectus_tool_factory is None:
                return "unavailable"
            if self._prospectus_tool_error:
                return "unavailable"
            return "index_not_ready"
        return "disabled"

    def _ensure_prospectus_tool(self) -> Any | None:
        if self._cached_prospectus_tool is not None:
            return self._cached_prospectus_tool
        if self._prospectus_tool_factory is None:
            self._prospectus_tool_error = "Prospectus tool factory is unavailable."
            return None
        try:
            self._cached_prospectus_tool = self._prospectus_tool_factory()
            self._prospectus_tool_error = None
            return self._cached_prospectus_tool
        except Exception as exc:
            self._prospectus_tool_error = str(exc)
            return None

    @property
    def _upload_dir(self) -> Path:
        return self.config.upload_dir or Path(__file__).resolve().parents[2] / "data" / "local_platform_uploads"

    def _local_upload_status(self) -> dict[str, Any]:
        ready = True
        error = None
        try:
            self._upload_dir.mkdir(parents=True, exist_ok=True)
            probe = self._upload_dir / ".local_platform_upload_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            ready = False
            error = str(exc)

        return {
            "ready": ready,
            "enabled": True,
            "status": "accepting_files_not_indexed" if ready else "unavailable",
            "upload_dir": str(self._upload_dir),
            "indexed": False,
            "searchable": False,
            "index_ready": False,
            "search_ready": False,
            "error": error,
        }

    def _prospectus_index_status(self) -> dict[str, Any]:
        try:
            return self._prospectus_index_service.prospectus_index_status()
        except Exception as exc:
            return {
                "ready": False,
                "enabled": True,
                "status": "unavailable",
                "collection": self.config.prospectus_collection,
                "index_ready": False,
                "search_ready": False,
                "searchable": False,
                "retrieval_paths": {
                    "dense": {"ready": False},
                    "sparse": {"ready": False},
                    "hybrid": {"ready": False},
                },
                "chunk_count": 0,
                "document_count": 0,
                "diagnostics": [str(exc)],
            }

    def _local_upload_indexing_status(self) -> dict[str, Any]:
        try:
            return self._prospectus_index_service.local_upload_indexing_status(self._upload_dir)
        except Exception as exc:
            return {
                "ready": False,
                "enabled": self.config.prospectus_indexing_enabled,
                "status": "unavailable",
                "collection": self.config.prospectus_collection,
                "upload_dir": str(self._upload_dir),
                "writable": False,
                "indexing_enabled": self.config.prospectus_indexing_enabled,
                "diagnostics": [str(exc)],
            }

    def _architecture_docs(self) -> dict[str, Any]:
        links = [
            {
                "label": "Financial Platform README",
                "path": "docs/financial/README.md",
                "available": (self.docs_root / "README.md").exists(),
            },
            {
                "label": "Financial Agentic RAG design",
                "path": "docs/financial/financial-agentic-rag-design.md",
                "available": (self.docs_root / "financial-agentic-rag-design.md").exists(),
            },
        ]
        adr_dir = self.docs_root / "adr"
        if adr_dir.exists():
            for adr in sorted(adr_dir.glob("*.md")):
                links.append(
                    {
                        "label": adr.stem,
                        "path": f"docs/financial/adr/{adr.name}",
                        "available": True,
                    }
                )
        return {"available": any(link["available"] for link in links), "links": links}
