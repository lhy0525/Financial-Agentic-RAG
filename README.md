# Financial Agentic RAG

Financial Agentic RAG is a local-first financial question-answering project built on a modular RAG/MCP foundation. It combines SQL evidence, prospectus document evidence, a financial planner, answer verification, and a no-login FastAPI + React demo platform.

This repository is packaged as the standalone Financial Agentic RAG development version maintained by `lhy0525`.

## What It Includes

- SQL-first financial answering over a local SQLite database
- Financial question planning and evidence routing
- Prospectus PDF/TXT upload, local indexing, and hybrid retrieval
- Verification reports, trace details, and structured source evidence
- FastAPI backend for local platform APIs
- React/Vite frontend for the no-login browser demo
- MCP server and modular RAG components retained from the original foundation
- Unit and integration tests for the financial pipeline and local platform

## Repository Layout

```text
config/                  Configuration examples and prompts
docs/financial/          Financial Agentic RAG documentation
openspec/                Formal product specs and archived changes
frontend/                React/Vite local demo platform
scripts/                 CLI helpers, ingestion, local startup, and LoRA utilities
src/                     Backend, RAG, MCP, and financial pipeline code
data/                    Repo-local datasets, SQLite files, LoRA assets, and retrieval stores
logs/                    Runtime traces and local logs
tests/                   Unit and integration tests
DEV_SPEC.md              Original development specification
CONTEXT.md               Project context and handoff notes
```

## Configuration

Copy the example settings file before running the local platform:

```powershell
copy config\settings.example.yaml config\settings.yaml
```

The local financial platform resolves the SQLite database path in this order:

1. `FINANCIAL_DEMO_DB_PATH`
2. `financial_platform.sql_db_path` in `config/settings.yaml`
3. A readable readiness failure from `GET /api/health` and `POST /api/chat`

Example:

```yaml
financial_platform:
  sql_db_path: "../data/sqlite/financial_demo.sqlite"
  host: "127.0.0.1"
  port: 8010
  prospectus_enabled: false
  prospectus_indexing_enabled: true
  prospectus_collection: "prospectus_uploads"
  upload_dir: "../data/local_platform_uploads"
```

Local runtime files such as `config/settings.yaml`, uploaded files, SQLite databases, vector stores, logs, and `data/` are intentionally ignored by Git.

The repo-local data layout used by the consolidated setup is:

- `data/sqlite/financial_demo.sqlite`
- `data/datasets/bs_challenge_financial_14b_dataset/`
- `data/lora/train/`, `data/lora/eval/`, and `data/lora/sql_examples/`
- `data/db/chroma/` and `data/db/bm25/`
- `logs/traces.jsonl`

## Backend Setup

Create and activate a Python environment, then install the project:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Start the local API:

```powershell
$env:FINANCIAL_DEMO_DB_PATH="D:\path\to\financial.sqlite"
.\.venv\Scripts\python.exe scripts\start_local_platform.py
```

The API listens on `http://127.0.0.1:8010` by default.

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

The UI runs at `http://127.0.0.1:5173` and proxies `/api` to the local FastAPI backend.

## Useful Commands

```powershell
.\.venv\Scripts\python.exe scripts\financial_query.py --help
.\.venv\Scripts\python.exe -m pytest tests/unit
.\.venv\Scripts\python.exe -m pytest tests/integration
cd frontend
npm test
npm run build
```

## Prospectus Upload And Indexing

The local platform supports one-file-at-a-time browser upload for PDF/TXT prospectus evidence. Uploaded files are saved locally, parsed, indexed into the configured collection, and reported with honest statuses such as `indexed_searchable`, `already_indexed`, or `index_failed`.

For many PDFs, use the local bulk ingestion workflow instead of repeated browser uploads:

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py `
  --path "D:\path\to\prospectus-pdfs" `
  --financial-prospectus `
  --config config\settings.yaml
```

Prospectus evidence remains local-only. This project does not add OAuth, JWT, cloud upload, hosted vector databases, or multi-user isolation.

## Documentation

Start here:

- `docs/financial/README.md`
- `openspec/specs/`
- `docs/financial/local-platform.md`
- `docs/financial/financial-agentic-rag-design.md`
- `docs/codebase-map.md`

## Suggested GitHub Description

```text
Local-first Financial Agentic RAG with SQL evidence, prospectus retrieval, verification, and a FastAPI/React demo.
```

## Maintainer

Maintained by `lhy0525`.
