from __future__ import annotations

from pathlib import Path

from src.local_platform.prospectus_index import LocalProspectusIndexService


class FakePipelineResult:
    success = False
    error = "simulated stop before embedding"
    doc_id = "doc_fake"
    chunk_count = 0
    image_count = 0
    vector_ids = []
    stages = {}


class FakeSuccessfulPipelineResult:
    success = True
    error = None
    doc_id = "doc_success"
    chunk_count = 3
    image_count = 2
    vector_ids = ["vec-1", "vec-2", "vec-3"]
    stages = {"integrity": {"skipped": False}}


def test_pdf_upload_indexing_uses_full_pipeline_with_small_embedding_batches(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class FakePipeline:
        def __init__(self, settings, **kwargs):
            captured.update(kwargs)

        def run(self, file_path):
            return FakePipelineResult()

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr("src.local_platform.prospectus_index.IngestionPipeline", FakePipeline)

    service = LocalProspectusIndexService(collection="prospectus_uploads")
    pdf_path = tmp_path / "large.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    result = service._index_pdf(pdf_path, origin="ui_upload", force=False)

    assert captured["embedding_batch_size"] == service.LOCAL_UPLOAD_EMBEDDING_BATCH_SIZE
    assert captured["extra_metadata"] == {"local_origin": "ui_upload"}
    assert captured["run_transforms"] is True
    assert captured["extract_images"] is True
    assert captured["closed"] is True
    assert result["status"] == "index_failed"


def test_pdf_upload_success_reports_full_pipeline_summary(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class FakePipeline:
        def __init__(self, settings, **kwargs):
            captured.update(kwargs)

        def run(self, file_path):
            return FakeSuccessfulPipelineResult()

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr("src.local_platform.prospectus_index.IngestionPipeline", FakePipeline)
    monkeypatch.setattr(
        LocalProspectusIndexService,
        "prospectus_index_status",
        lambda self: {
            "index_ready": True,
            "search_ready": True,
            "diagnostics": [],
        },
    )

    service = LocalProspectusIndexService(collection="prospectus_uploads")
    pdf_path = tmp_path / "with-images.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    result = service._index_pdf(pdf_path, origin="ui_upload", force=False)

    assert captured["run_transforms"] is True
    assert captured["extract_images"] is True
    assert result["status"] == "indexed_searchable"
    assert result["image_count"] == 2
    assert result["transform_enabled"] is True
    assert result["image_extraction_enabled"] is True
    assert result["chunk_count"] == 3
    assert result["vector_count"] == 3
