# Codebase Map

This repository is the main runnable product for the `financial-agentic-rag` workspace. Runtime secrets and local credentials should live in ignored local files, while committed files should be source code, tests, prompts, examples, and documentation.

## Runtime Entry Points

- `main.py`: MCP server entry point.
- `scripts/ingest.py`: document ingestion CLI, including local financial prospectus ingestion modes.
- `scripts/query.py`: generic RAG query CLI.
- `scripts/financial_query.py`: SQL-backed financial Agentic RAG smoke query CLI.
- `scripts/evaluate.py`: generic and financial evaluation CLI entry point.
- `scripts/start_dashboard.py`: Streamlit dashboard launcher.
- `scripts/start_local_platform.py`: local FastAPI platform launcher.
- `frontend`: React/Vite local financial platform UI.

## Source Layout

- `src/core`: shared contracts, settings, query engine, response assembly, and tracing.
- `src/ingestion`: document loading, chunking, transforms, embedding batches, and storage upserts.
- `src/libs`: provider adapters for LLMs, embeddings, rerankers, vector stores, loaders, splitters, and evaluators.
- `src/mcp_server`: MCP protocol wrapper and registered tools.
- `src/observability`: logging, dashboard pages/services, and evaluation runners.
- `src/agentic`: financial question planning, orchestration, evidence merging, verification, and shared agent contracts.
- `src/financial_sql`: financial SQLite schema registry, entity resolution, formula handling, SQL safety, SQL execution, and text-to-SQL evidence packaging.
- `src/prospectus_evidence`: parsed prospectus TXT loading, element docstore support, and prospectus evidence packaging.
- `src/financial_dataset`: local Bosera challenge dataset path, question, and fixture helpers.
- `src/local_platform`: no-login local FastAPI demo backend, configuration, upload mapping, prospectus indexing, and chat service.
- `frontend/src`: React local platform UI, API client, styles, and frontend tests.

## Tests

- `tests/unit`: fast unit coverage for individual modules, financial agent behavior, local platform services, ingestion, retrieval, SQL, and evidence packaging.
- `tests/integration`: cross-component behavior, provider integration, dataset-backed SQL checks, ingestion, tracing, and MCP server behavior.
- `tests/e2e`: smoke and end-to-end workflows.
- `tests/fixtures`: generated sample documents, golden test data, and financial boundary fixtures.
- `frontend/src/*.test.jsx`: frontend unit tests run with Vitest.

## Configuration

- `config/settings.example.yaml`: committed safe template.
- `config/settings.yaml`: ignored local runtime configuration.
- `config/test_credentials.yaml.example`: committed safe QA credential template.
- `config/test_credentials.yaml`: ignored local QA credentials.
- `config/prompts`: committed prompt templates used by transforms and reranking.
- `frontend/package.json`: local platform frontend scripts and dependencies.

## Documentation

- `README.md`: main product overview and current handoff entry.
- `CONTEXT.md`: financial Agentic RAG terminology and boundary language.
- `DEV_SPEC.md`: original modular RAG MCP server development specification.
- `docs/financial/README.md`: financial Agentic RAG documentation index.
- `docs/financial/local-platform.md`: local platform configuration, startup, upload/indexing, and smoke path.
- `docs/financial/domain-rules.md`: financial domain rules, aliases, periods, and unsupported patterns.
- `docs/financial/dataset-setup.md`: dataset setup and readiness runbook.
- `docs/financial/adr`: financial architecture decisions.

## Local And Generated Files

The following should not be committed:

- local credentials and settings
- virtual environments
- Python caches, test caches, coverage output, and temporary pytest directories
- local server logs and traces
- frontend build output and frontend caches
- local data stores, SQLite databases, Chroma/vector-store data, BM25 indexes, uploads, and other runtime state
- editor, browser QA, and agent-local settings

Protected local assets are preserved during routine cleanup:

- `config/settings.yaml`
- `data/`, uploaded files, SQLite databases, Chroma/BM25 stores, and indexed local platform content
- datasets and test fixtures
- untracked source modules, scripts, docs, tests, and frontend source
- `frontend/node_modules` until frontend verification has passed, dependencies can be restored, or deletion is explicitly approved
