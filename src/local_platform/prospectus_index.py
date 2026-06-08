from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from src.core.settings import load_settings, resolve_path, Settings
from src.ingestion.chunking.document_chunker import DocumentChunker
from src.ingestion.embedding.batch_processor import BatchProcessor
from src.ingestion.embedding.dense_encoder import DenseEncoder
from src.ingestion.embedding.sparse_encoder import SparseEncoder
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.storage.bm25_indexer import BM25Indexer
from src.ingestion.storage.vector_upserter import VectorUpserter
from src.libs.embedding.embedding_factory import EmbeddingFactory
from src.libs.loader.file_integrity import SQLiteIntegrityChecker
from src.libs.vector_store.vector_store_factory import VectorStoreFactory
from src.prospectus_evidence.evidence_tool import ProspectusEvidenceTool
from src.prospectus_evidence.txt_loader import ProspectusTxtLoader


class ProspectusIndexService(Protocol):
    collection: str

    def index_file(
        self,
        file_path: Path,
        *,
        suffix: str,
        origin: str = "ui_upload",
        force: bool = False,
    ) -> dict[str, Any]:
        ...

    def prospectus_index_status(self) -> dict[str, Any]:
        ...

    def local_upload_indexing_status(self, upload_dir: Path) -> dict[str, Any]:
        ...

    def build_tool(self) -> ProspectusEvidenceTool:
        ...


class LocalProspectusIndexService:
    LOCAL_UPLOAD_EMBEDDING_BATCH_SIZE = 10

    def __init__(
        self,
        *,
        settings_path: str | Path | None = None,
        collection: str = "prospectus_uploads",
        indexing_enabled: bool = True,
    ) -> None:
        self.settings_path = Path(settings_path) if settings_path is not None else None
        self.collection = collection
        self.indexing_enabled = indexing_enabled
        self._settings: Settings | None = None

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = load_settings(self.settings_path)
        return self._settings

    def index_file(
        self,
        file_path: Path,
        *,
        suffix: str,
        origin: str = "ui_upload",
        force: bool = False,
    ) -> dict[str, Any]:
        if not self.indexing_enabled:
            return self._failed_result(file_path, suffix, "Prospectus upload indexing is disabled.", origin)

        try:
            if suffix == ".txt":
                return self._index_txt(file_path, origin=origin, force=force)
            return self._index_pdf(file_path, origin=origin, force=force)
        except Exception as exc:
            return self._failed_result(file_path, suffix, str(exc), origin)

    def prospectus_index_status(self) -> dict[str, Any]:
        diagnostics: list[str] = []
        vector_ready = False
        chunk_count = 0
        bm25_ready = False
        bm25_doc_count = 0

        try:
            vector_store = VectorStoreFactory.create(self.settings, collection_name=self.collection)
            stats = vector_store.get_collection_stats()
            chunk_count = int(stats.get("count") or 0)
            vector_ready = chunk_count > 0
        except Exception as exc:
            diagnostics.append(f"vector store unavailable: {exc}")

        try:
            bm25 = self._bm25_indexer()
            bm25_ready = bm25.load(self.collection)
            bm25_doc_count = int(bm25._metadata.get("num_docs") or 0) if bm25_ready else 0
        except Exception as exc:
            diagnostics.append(f"BM25 index unavailable: {exc}")

        search_ready = vector_ready and bm25_ready
        status = "ready" if search_ready else "not_ready"
        if not vector_ready and not bm25_ready and not diagnostics:
            diagnostics.append("No indexed prospectus chunks found in the configured collection.")

        return {
            "ready": search_ready,
            "enabled": True,
            "status": status,
            "collection": self.collection,
            "index_ready": vector_ready or bm25_ready,
            "search_ready": search_ready,
            "searchable": search_ready,
            "retrieval_paths": {
                "dense": {"ready": vector_ready, "chunk_count": chunk_count},
                "sparse": {"ready": bm25_ready, "document_count": bm25_doc_count},
                "hybrid": {"ready": search_ready},
            },
            "chunk_count": chunk_count,
            "document_count": bm25_doc_count,
            "diagnostics": diagnostics,
        }

    def local_upload_indexing_status(self, upload_dir: Path) -> dict[str, Any]:
        diagnostics: list[str] = []
        writable = False

        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
            probe = upload_dir / ".local_upload_indexing_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            writable = True
        except OSError as exc:
            diagnostics.append(str(exc))

        try:
            _ = self.settings
        except Exception as exc:
            diagnostics.append(f"settings unavailable: {exc}")

        ready = bool(self.indexing_enabled and writable and not diagnostics)
        return {
            "ready": ready,
            "enabled": self.indexing_enabled,
            "status": "ready" if ready else "unavailable",
            "collection": self.collection,
            "upload_dir": str(upload_dir),
            "writable": writable,
            "indexing_enabled": self.indexing_enabled,
            "diagnostics": diagnostics,
        }

    def build_tool(self) -> ProspectusEvidenceTool:
        status = self.prospectus_index_status()
        if not status["ready"]:
            raise RuntimeError("; ".join(status["diagnostics"]) or "Prospectus index is not ready.")
        return ProspectusEvidenceTool(self._build_hybrid_search())

    def _index_pdf(self, file_path: Path, *, origin: str, force: bool) -> dict[str, Any]:
        pipeline = IngestionPipeline(
            self.settings,
            collection=self.collection,
            force=force,
            extra_metadata={"local_origin": origin},
            embedding_batch_size=self.LOCAL_UPLOAD_EMBEDDING_BATCH_SIZE,
            run_transforms=False,
            extract_images=False,
        )
        try:
            result = pipeline.run(str(file_path))
        finally:
            pipeline.close()

        skipped = bool(result.stages.get("integrity", {}).get("skipped"))
        if not result.success:
            return self._failed_result(file_path, ".pdf", result.error or "PDF indexing failed.", origin)

        readiness = self.prospectus_index_status()
        return self._success_result(
            file_path,
            suffix=".pdf",
            document_id=result.doc_id,
            chunk_count=result.chunk_count,
            vector_count=len(result.vector_ids),
            origin=origin,
            status="already_indexed" if skipped else "indexed_searchable",
            readiness=readiness,
        )

    def _index_txt(self, file_path: Path, *, origin: str, force: bool) -> dict[str, Any]:
        checker = SQLiteIntegrityChecker(db_path=str(resolve_path("data/db/ingestion_history.db")))
        file_hash = checker.compute_sha256(str(file_path))
        document = ProspectusTxtLoader(collection=self.collection).load(file_path)
        if not force and checker.should_skip(file_hash, collection=self.collection):
            readiness = self.prospectus_index_status()
            return self._success_result(
                file_path,
                suffix=".txt",
                document_id=document.id,
                chunk_count=0,
                vector_count=0,
                origin=origin,
                status="already_indexed",
                readiness=readiness,
            )

        document.metadata.update(
            {
                "collection": self.collection,
                "local_origin": origin,
                "file_hash": file_hash,
            }
        )
        chunks = DocumentChunker(self.settings).split_document(document)
        embedding = EmbeddingFactory.create(self.settings)
        batch_size = self.LOCAL_UPLOAD_EMBEDDING_BATCH_SIZE
        batch_result = BatchProcessor(
            dense_encoder=DenseEncoder(embedding, batch_size=batch_size),
            sparse_encoder=SparseEncoder(),
            batch_size=batch_size,
            continue_on_batch_error=False,
        ).process(chunks)

        vector_ids = VectorUpserter(self.settings, collection_name=self.collection).upsert(
            chunks,
            batch_result.dense_vectors,
        )
        for stat, vector_id in zip(batch_result.sparse_stats, vector_ids):
            stat["chunk_id"] = vector_id
        self._bm25_indexer().add_documents(
            batch_result.sparse_stats,
            collection=self.collection,
            doc_id=document.id,
        )
        checker.mark_success(file_hash, str(file_path), self.collection)

        readiness = self.prospectus_index_status()
        return self._success_result(
            file_path,
            suffix=".txt",
            document_id=document.id,
            chunk_count=len(chunks),
            vector_count=len(vector_ids),
            origin=origin,
            status="indexed_searchable",
            readiness=readiness,
        )

    def _build_hybrid_search(self):
        from src.core.query_engine.dense_retriever import create_dense_retriever
        from src.core.query_engine.hybrid_search import create_hybrid_search
        from src.core.query_engine.query_processor import QueryProcessor
        from src.core.query_engine.sparse_retriever import create_sparse_retriever

        embedding = EmbeddingFactory.create(self.settings)
        vector_store = VectorStoreFactory.create(self.settings, collection_name=self.collection)
        dense_retriever = create_dense_retriever(
            settings=self.settings,
            embedding_client=embedding,
            vector_store=vector_store,
        )
        sparse_retriever = create_sparse_retriever(
            settings=self.settings,
            bm25_indexer=self._bm25_indexer(),
            vector_store=vector_store,
        )
        sparse_retriever.default_collection = self.collection
        return create_hybrid_search(
            settings=self.settings,
            query_processor=QueryProcessor(),
            dense_retriever=dense_retriever,
            sparse_retriever=sparse_retriever,
        )

    def _bm25_indexer(self) -> BM25Indexer:
        return BM25Indexer(index_dir=str(resolve_path(f"data/db/bm25/{self.collection}")))

    def _success_result(
        self,
        file_path: Path,
        *,
        suffix: str,
        document_id: str | None,
        chunk_count: int,
        vector_count: int,
        origin: str,
        status: str,
        readiness: dict[str, Any],
    ) -> dict[str, Any]:
        search_ready = bool(readiness.get("search_ready"))
        indexed = status == "already_indexed" or chunk_count > 0 or vector_count > 0
        return {
            "status": status,
            "collection": self.collection,
            "document_id": document_id,
            "doc_type": suffix.lstrip("."),
            "chunk_count": chunk_count,
            "vector_count": vector_count,
            "indexed": indexed,
            "searchable": search_ready,
            "index_ready": bool(readiness.get("index_ready")),
            "search_ready": search_ready,
            "local_origin": origin,
            "diagnostics": readiness.get("diagnostics", []),
        }

    def _failed_result(self, file_path: Path, suffix: str, error: str, origin: str = "ui_upload") -> dict[str, Any]:
        return {
            "status": "index_failed",
            "collection": self.collection,
            "document_id": None,
            "doc_type": suffix.lstrip("."),
            "chunk_count": 0,
            "vector_count": 0,
            "indexed": False,
            "searchable": False,
            "index_ready": False,
            "search_ready": False,
            "local_origin": origin,
            "diagnostics": [error],
            "error": error,
        }
