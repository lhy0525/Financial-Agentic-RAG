from __future__ import annotations

from pathlib import Path

from src.local_platform.prospectus_index import LocalProspectusIndexService


class FakePipelineResult:
    success = False
    error = "simulated stop before embedding"
    doc_id = "doc_fake"
    chunk_count = 0
    vector_ids = []
    stages = {}


def test_pdf_upload_indexing_uses_small_embedding_batches(monkeypatch, tmp_path):
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
    assert captured["run_transforms"] is False
    assert captured["extract_images"] is False
    assert captured["closed"] is True
    assert result["status"] == "index_failed"
