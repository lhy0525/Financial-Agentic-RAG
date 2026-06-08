# Financial Agentic RAG

This directory collects the Financial Agentic RAG project context inside the main MCP server repository so the `develop-financial-agentic-rag` branch is self-contained.

## Start Here

- `../codebase-map.md`: current main repository source, test, configuration, and generated-file map.
- `financial-agentic-rag-design.md`: product and architecture design for financial hybrid answering.
- `local-platform.md`: no-login local FastAPI/React platform startup and roadmap.
- `dataset-setup.md`: local dataset setup and readiness runbook.
- `domain-rules.md`: financial aliases, formulas, report periods, and unsupported patterns.
- `implementation/2026-06-05-develop-financial-agentic-rag.md`: task-by-task implementation plan.
- `openspec/develop-financial-agentic-rag/proposal.md`: OpenSpec change proposal.
- `openspec/develop-financial-agentic-rag/tasks.md`: OpenSpec task checklist.

## Current Runtime Entry Points

- SQL-first smoke CLI: `python scripts/financial_query.py --help`
- Local platform backend: `python scripts/start_local_platform.py`
- Local platform frontend: `cd frontend && npm run dev`
- Unit tests: `python -m pytest tests/unit`
- Frontend tests/build: `npm test` and `npm run build` from `frontend`

Local runtime data, uploaded files, vector/BM25 indexes, SQLite databases, and `config/settings.yaml` are intentionally local and should be preserved during routine cleanup.

## Specs

- `openspec/develop-financial-agentic-rag/specs/financial-question-planning/spec.md`
- `openspec/develop-financial-agentic-rag/specs/financial-sql-evidence/spec.md`
- `openspec/develop-financial-agentic-rag/specs/prospectus-evidence/spec.md`
- `openspec/develop-financial-agentic-rag/specs/financial-hybrid-answering/spec.md`
- `openspec/develop-financial-agentic-rag/specs/financial-evaluation/spec.md`

## ADRs

- `adr/0001-router-lives-in-agent-layer.md`
- `adr/0002-table-evidence-summary-retrieval-raw-generation.md`

## Development Branch

Use this branch for implementation work:

```text
develop-financial-agentic-rag
```
