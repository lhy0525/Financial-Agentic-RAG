# Financial Agentic RAG

This directory contains the human-facing product documentation for the standalone Financial Agentic RAG repository.

## Start Here

- `../codebase-map.md`: repository source, test, configuration, and generated-file map.
- `financial-agentic-rag-design.md`: product and architecture design for financial hybrid answering.
- `local-platform.md`: no-login local FastAPI/React platform startup and behavior guide.
- `dataset-setup.md`: local dataset setup and readiness runbook.
- `domain-rules.md`: financial aliases, formulas, report periods, and source-priority rules.
- `implementation/2026-06-05-develop-financial-agentic-rag.md`: historical implementation plan.

## Formal Specs

The formal product specs now live at the repository root under `openspec/`.

- `../../openspec/specs/financial-question-planning/spec.md`
- `../../openspec/specs/financial-sql-evidence/spec.md`
- `../../openspec/specs/prospectus-evidence/spec.md`
- `../../openspec/specs/financial-hybrid-answering/spec.md`
- `../../openspec/specs/financial-evaluation/spec.md`
- `../../openspec/specs/financial-planner-boundary-coverage/spec.md`
- `../../openspec/specs/financial-sql-boundary-calculations/spec.md`
- `../../openspec/specs/prospectus-boundary-retrieval/spec.md`
- `../../openspec/specs/financial-evaluation-boundaries/spec.md`
- `../../openspec/specs/financial-readiness-documentation/spec.md`
- `../../openspec/specs/local-financial-platform/spec.md`
- `../../openspec/specs/uploaded-prospectus-chat-search/spec.md`

## Archived Change History

Archived OpenSpec changes now live under `../../openspec/changes/archive/`.

## ADRs

- `adr/0001-router-lives-in-agent-layer.md`
- `adr/0002-table-evidence-summary-retrieval-raw-generation.md`

## Runtime Entry Points

- SQL-first smoke CLI: `python scripts/financial_query.py --help`
- Local platform backend: `python scripts/start_local_platform.py`
- Local platform frontend: `cd frontend && npm run dev`
- Unit tests: `python -m pytest tests/unit`
- Frontend tests/build: `npm test` and `npm run build` from `frontend`

Local runtime data, uploaded files, vector/BM25 indexes, SQLite databases, and `config/settings.yaml` are intentionally local and should be preserved during routine cleanup.
