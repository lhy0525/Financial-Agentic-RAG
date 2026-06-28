# Prospectus Multimodal Upload And Evidence Design

Date: 2026-06-28

## Goal

Enable local platform PDF uploads to participate in the existing full ingestion pipeline and make prospectus retrieval return multimodal-aware evidence packages for the Agent layer.

This change keeps the implementation scoped to existing pipeline capabilities. It does not introduce a native `DocumentElement` model, raw table docstore, chart-specific extraction, async indexing jobs, or in-chat image rendering. Those remain later element-native extensions.

## Decisions

- Use a two-stage roadmap: first full existing pipeline plus multimodal-aware evidence metadata, later element-native evidence.
- UI PDF upload remains synchronous.
- UI PDF upload uses the full existing `IngestionPipeline` with `run_transforms=True` and `extract_images=True`.
- LLM refinement, metadata enrichment, and image captions continue to respect `settings.yaml`; the upload path does not force external model calls.
- Prospectus evidence is enabled by default in committed config/docs, while runtime readiness checks continue to gate actual use.
- One retrieval hit maps to one `Evidence`. A hit with multiple modalities becomes a multimodal-aware evidence item rather than multiple duplicated evidence rows.
- Image evidence is returned as structured metadata first. This round does not add FastAPI image serving or frontend thumbnail rendering.

## Configuration

`financial_platform.prospectus_enabled` becomes `true` in:

- `config/settings.yaml` for the local workspace.
- `config/settings.example.yaml` so copied local configs opt into prospectus evidence by default.
- README and local platform docs.

Readiness remains truthful:

- `prospectus_index.ready` must be true before search is considered ready.
- `prospectus_evidence.ready` must be true before `LocalFinancialPlatformService` injects `ProspectusEvidenceTool` into `FinancialOrchestrator`.
- SQL chat remains available when the SQL database is ready even if prospectus search is not ready.

## Upload Pipeline

For PDF uploads through `POST /api/prospectus/upload`, `LocalProspectusIndexService._index_pdf` will construct:

```python
IngestionPipeline(
    settings,
    collection=prospectus_collection,
    force=force,
    extra_metadata={"local_origin": "ui_upload"},
    embedding_batch_size=LOCAL_UPLOAD_EMBEDDING_BATCH_SIZE,
    run_transforms=True,
    extract_images=True,
)
```

The path therefore uses the existing stages:

1. File integrity check.
2. PDF loading and image extraction.
3. Chunking with image references mapped into chunk metadata.
4. Transform stage using configured refiner, metadata enricher, and image captioner.
5. Dense and sparse encoding.
6. Chroma, BM25, and image storage registration.

For TXT uploads, the existing narrow text indexing path remains unchanged because it has no image extraction requirement.

Upload responses should expose enough summary fields to prove which path ran:

- `chunk_count`
- `vector_count`
- `image_count`
- `transform_enabled`
- `image_extraction_enabled`
- existing readiness fields

## Prospectus Evidence

`ProspectusEvidenceTool` will continue to query the configured hybrid search stack. It will enhance `Evidence` construction for each retrieval result:

- `evidence_type="text"` for text-only chunks.
- `evidence_type="table"` for chunks with table placeholders or table metadata.
- `evidence_type="image"` for image-only chunks.
- `evidence_type="multimodal"` for chunks combining text with images and/or tables.

Metadata should include:

- `modalities`
- `chunk_id`
- `chunk_index`
- `source_path`
- `page` or `page_num`
- `element_id`
- `element_type`
- `table_placeholders`
- `raw_payload_available`
- `raw_table_unavailable`
- `image_refs`
- `images`
- `image_captions`
- existing domain metadata such as company, section, and disclosure family

The tool should preserve retrieval ranking and score by keeping one `Evidence` per retrieval hit.

## Error Handling

- If full PDF ingestion fails, upload returns `index_failed` with diagnostics.
- If image extraction fails inside `PdfLoader`, existing graceful degradation keeps text ingestion alive.
- If image captioning is disabled or unavailable, evidence still returns image refs and image metadata when images were extracted.
- If prospectus readiness fails after indexing, the upload response reports indexed/searchable fields honestly.

## Testing

Add focused unit coverage for:

- `prospectus_enabled` default resolution.
- PDF upload path passes `run_transforms=True` and `extract_images=True` to `IngestionPipeline`.
- Upload success responses include `image_count`, `transform_enabled`, and `image_extraction_enabled`.
- `ProspectusEvidenceTool` maps text/table/image/mixed retrieval metadata into expected `Evidence.evidence_type` and metadata.

Existing integration tests for local platform health, upload, and prospectus indexing should continue to pass.

## Non-Goals

- No background indexing jobs or polling API.
- No image thumbnail rendering in chat UI.
- No static image serving endpoint.
- No native `DocumentElement` pipeline.
- No raw table SQLite docstore.
- No chart classifier or chart-specific evidence type beyond metadata carried by existing chunks.
- No forced external LLM or VLM calls beyond configured settings.

## Future Extension

The next step after this design can add an element-native layer:

- `DocumentElement`
- `ElementDocstore`
- raw table payload retrieval by `element_id`
- dedicated chart/image evidence records
- optional frontend rendering for local image evidence
