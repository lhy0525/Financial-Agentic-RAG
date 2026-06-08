## Why

The project needs a finance-specific Agentic RAG system that can answer both prospectus disclosure questions and precise structured-data questions from the Bosera financial dataset. The existing RAG MCP server provides a strong document retrieval baseline, but the target workload also requires domain planning, safe SQL execution, hybrid evidence orchestration, and numeric verification.

## What Changes

- Add a finance question planning capability that classifies questions, extracts entities and time scopes, identifies formulas, and produces structured execution plans.
- Add a safe Text-to-SQL evidence path for the 10-table SQLite financial database, including schema linking, SQL safety checks, execution, result normalization, and SQL evidence packaging.
- Add a prospectus evidence path that can use the provided parsed TXT files as a baseline and later enhance PDF evidence with element-aware text/table/image/chart retrieval.
- Add hybrid financial answering that orchestrates `sql_first` and `doc_first` flows and merges evidence from DB and prospectus sources.
- Add verification and evaluation requirements for source priority, numeric consistency, evidence sufficiency, and regression metrics.
- Preserve the existing MCP RAG server boundary: document retrieval remains reusable, while routing and hybrid orchestration live in the agent layer.

## Capabilities

### New Capabilities

- `financial-question-planning`: Plans finance questions into route, entities, time scope, formula, evidence needs, and answer constraints.
- `financial-sql-evidence`: Produces safe, structured SQL evidence packages from the Bosera SQLite database.
- `prospectus-evidence`: Retrieves prospectus evidence from parsed TXT/PDF content with traceable source metadata and element-aware extension points.
- `financial-hybrid-answering`: Orchestrates PDF and SQL evidence paths, merges evidence, verifies results, and returns sourced final answers.
- `financial-evaluation`: Evaluates router, SQL, prospectus retrieval, hybrid reasoning, verifier behavior, and failure regressions.

### Modified Capabilities

- None.

## Impact

- Adds new agent-layer modules for planning, orchestration, evidence packaging, merging, and verification.
- Adds new financial SQL modules for schema registry, formula registry, SQL generation/compilation, safety checks, execution, and query logging.
- Adds prospectus ingestion/query extensions that should reuse existing loader, chunking, Chroma, BM25, image storage, and trace infrastructure where practical.
- Adds OpenSpec-driven test and evaluation assets for financial question categories and dataset-specific golden cases.
- Avoids breaking existing MCP tools such as `query_knowledge_hub`, `list_collections`, and `get_document_summary`.
