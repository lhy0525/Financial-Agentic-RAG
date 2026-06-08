# Hosting Readiness Report

Date: 2026-06-08

Repository: `MODULAR-RAG-MCP-SERVER`

Branch: `develop-financial-agentic-rag`

Remote: `https://github.com/lhy0525/MODULAR-RAG-MCP-SERVER.git`

## Executive Conclusion

This repository is ready for hosting as a controlled handoff snapshot.

It is not yet a fully release-green delivery because the full Python unit suite is not passing. Frontend tests, frontend production build, CLI smoke, whitespace checks, ignore rules, and high-confidence secret scanning are acceptable for hosting the code snapshot.

## Hosting Boundary

Host this repository as the product boundary.

The parent workspace contains OpenSpec history, workspace cleanup notes, local agent workflow assets, and adjacent datasets/projects. Those workspace-level files are intentionally outside this product repository unless explicitly copied here.

## Must Stage For Product Hosting

The controlled snapshot should include:

- Updated handoff docs: `README.md`, `docs/codebase-map.md`, `docs/financial/README.md`, `docs/financial/local-platform.md`, `docs/cleanup/2026-06-08-hosting-readiness-report.md`
- Config template: `config/settings.example.yaml`
- Frontend source: `frontend/index.html`, `frontend/package*.json`, `frontend/src/*`, `frontend/vite.config.js`
- CLI and launch scripts: `scripts/financial_query.py`, `scripts/start_local_platform.py`, `scripts/ingest.py`
- Agentic orchestration modules: `src/agentic/*`
- Local platform modules: `src/local_platform/*`
- Financial SQL and ingestion changes: `src/financial_sql/*`, `src/ingestion/*`, `src/libs/loader/file_integrity.py`
- Unit tests for the new and changed behavior under `tests/unit/`

## Must Not Stage

The following local/runtime assets must remain untracked and ignored:

- `config/settings.yaml`
- `config/test_credentials.yaml`
- `data/`
- `logs/`
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `.local-platform-backend.*.log`
- `frontend/node_modules/`
- `frontend/dist/`
- local datasets outside this repository

## Verification Evidence

Commands were run from this repository unless noted otherwise.

### Whitespace / Diff Hygiene

```powershell
git diff --check
```

Result: passed with exit code 0. Git printed Windows line-ending warnings for several LF working-tree files because `core.autocrlf=true`, but no whitespace errors were reported.

### Secret Scan

High-confidence secret regex scan excluded `.git`, `.venv`, `frontend/node_modules`, `data`, `logs`, Python caches, pytest caches, lockfiles, and external datasets.

Result: no high-confidence secret regex matches outside excluded local/generated areas.

### CLI Smoke

```powershell
python scripts/financial_query.py --help
```

Result: passed. The command printed the expected usage for SQL-backed financial Agentic RAG smoke queries.

### Frontend Tests

```powershell
npm test
```

Result: passed.

Summary:

- 1 test file passed
- 10 tests passed

### Frontend Build

```powershell
npm run build
```

Result: passed. Vite built successfully.

Generated output under `frontend/dist/` is ignored and should not be committed.

### Python Unit Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit --tb=short --disable-warnings
```

Result: failed.

Summary:

- 1365 collected
- 1175 passed
- 1 skipped
- 16 failed
- 173 errors

Notable failure categories include provider initialization tests, BM25/index persistence tests, settings/config loading, duplicate MCP tool registration, sparse tokenization expectations, and tests that touch local filesystem state.

## Hosting Risks

1. Python unit tests are not green. This is the main release-readiness blocker.
2. The product repo already tracks assistant/workflow files under `.claude`, `.codex`, `.github`, and `.gstack-codex`. Treat them as included workflow assets unless a later cleanup removes them.
3. Git prints line-ending warnings because `core.autocrlf=true`. This is not currently a failing gate, but a repo-level `.gitattributes` could reduce future Windows diff noise.

## Snapshot Policy

This handoff is suitable for:

- remote backup
- collaboration
- managed review
- further release hardening

It should not be presented as a fully green production release until the Python test gate is fixed or a smaller reliable release-gate suite is defined and passing.
