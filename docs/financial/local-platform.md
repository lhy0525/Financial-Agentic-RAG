# Local Financial Platform

The local financial platform is a no-login SQL-first browser demo for the Financial Agentic RAG pipeline. It adds a FastAPI backend under `src/local_platform` and a React/Vite frontend under `frontend` without changing the existing MCP server or script-oriented financial query flow.

## Configuration

The backend resolves the SQLite database path in this order:

1. `FINANCIAL_DEMO_DB_PATH`
2. `financial_platform.sql_db_path` in `config/settings.yaml`
3. Readiness failure reported by `GET /api/health` and `POST /api/chat`

Copy `config/settings.example.yaml` to `config/settings.yaml` when you want file-based configuration. Environment variables win over the YAML value.

```yaml
financial_platform:
  sql_db_path: "./data/financial_demo.sqlite"
  host: "127.0.0.1"
  port: 8010
  cors_origins:
    - "http://localhost:5173"
    - "http://127.0.0.1:5173"
  prospectus_enabled: false
  prospectus_indexing_enabled: true
  prospectus_collection: "prospectus_uploads"
  upload_dir: "./data/local_platform_uploads"
```

`prospectus_collection` is the shared local collection for browser uploads, bulk local PDF ingestion, readiness checks, and chat retrieval. Keep it stable unless you intentionally want a new local search corpus.

Prospectus evidence is disabled by default. Set `prospectus_enabled: true` only when the configured collection has indexed chunks and the embedding/vector/BM25 stack is available. The platform still checks real readiness before enabling prospectus chat retrieval.

Local upload readiness is reported separately from prospectus search readiness:

- `local_upload` reports whether the server can save uploaded files.
- `local_upload_indexing` reports whether a new browser upload can be indexed now.
- `prospectus_index` reports whether the configured collection is searchable.
- `prospectus_evidence` reports whether chat can build a real `ProspectusEvidenceTool`.

## Start The Backend

Install Python dependencies from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Start the local API:

```powershell
$env:FINANCIAL_DEMO_DB_PATH="D:\path\to\financial.sqlite"
.\.venv\Scripts\python.exe scripts\start_local_platform.py
```

The API listens on `http://127.0.0.1:8010` by default.

## Start The Frontend

Install and run the frontend from `frontend`:

```powershell
npm install
npm run dev
```

Vite serves the UI at `http://127.0.0.1:5173` and proxies `/api` to `http://127.0.0.1:8010`.

## Manual Smoke Path

1. Open `http://127.0.0.1:5173`.
2. Confirm the sidebar says the session is local/no-login.
3. Confirm Upload PDF/TXT is either enabled only when local upload readiness is true, or disabled/coming next when the upload directory is unavailable.
4. Submit a SQL-first question such as `Show the latest available SQL evidence for stock 000001.`
5. Confirm the answer area renders an answer or readable configuration error, sources/evidence when available, verification status, trace details, and latency.
6. Use Clear History and confirm the visible local chat session is reset.
7. Optionally upload a local `.txt` or `.pdf` file and confirm the response is `indexed_searchable`, `already_indexed`, or `index_failed` with readable diagnostics.

## Prospectus Upload Indexing

Browser upload is intended for one local PDF/TXT at a time. `POST /api/prospectus/upload` saves the file under `upload_dir`, parses it, indexes it into `financial_platform.prospectus_collection`, and returns an honest status:

- `indexed_searchable`: chunks and vectors were written and the collection is searchable.
- `already_indexed`: the same document is already indexed in the same collection.
- `index_failed`: the file was saved and parsed, but embedding/vector/BM25 indexing failed.

Failures in prospectus indexing do not make SQL-first chat unavailable.

## Bulk Local PDF Directories

For many existing PDFs, use the local CLI instead of repeated browser uploads:

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py `
  --path "D:\path\to\prospectus-pdfs" `
  --financial-prospectus `
  --config config\settings.yaml
```

`--financial-prospectus` reads `financial_platform.prospectus_collection`, defaulting to `prospectus_uploads`, and tags chunks with `local_origin=bulk_local_directory`. You can override the target collection explicitly:

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py --path "D:\path\to\pdfs" --collection prospectus_uploads
```

The summary reports successful files, skipped duplicates, failed files, chunk count, and image count. Duplicate checks are scoped to both file identity and collection, so a PDF seen in `default` can still be indexed into `prospectus_uploads`.

## Disable Or Roll Back Prospectus Indexing

To keep SQL-first chat while disabling new upload indexing:

```yaml
financial_platform:
  prospectus_enabled: false
  prospectus_indexing_enabled: false
```

Existing SQL chat remains available when the SQLite database is valid. Re-enable indexing by setting `prospectus_indexing_enabled: true`, then re-run browser upload or the bulk CLI workflow. Re-enable prospectus chat retrieval with `prospectus_enabled: true` only after `GET /api/health` reports `prospectus_index.ready: true`.

## Phase Roadmap

Phase 1 ships the SQL-first API, no-login React shell, local history, architecture docs entry, verification status, trace/evidence rendering, and honest local upload metadata.

Phase 2 now includes a narrow local-only upload/index workflow:

1. Accept local PDF/TXT files through `POST /api/prospectus/upload`.
2. Save files to the configured local upload directory.
3. Parse text with existing local loaders.
4. Index chunks into local vector/BM25 stores.
5. Report parse/index/search status and readable failures through platform metadata and the upload endpoint.
6. Wire a real `ProspectusEvidenceTool` only when local index readiness passes.

This platform should not add OAuth, JWT, cloud upload, multi-user isolation, Pinecone, MongoDB, Supabase, Redis, or reference-project-specific service claims.
