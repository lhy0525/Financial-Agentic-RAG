## Context

The current codebase contains a Modular RAG MCP Server with a local-first ingestion and query pipeline:

```text
PDF -> PdfLoader -> Document -> DocumentChunker -> Transform -> Dense/Sparse Encode
    -> Chroma + BM25 + ImageStorage

query_knowledge_hub -> QueryProcessor -> Dense/Sparse Retrieval -> RRF -> Reranker
    -> ResponseBuilder -> MCP response
```

The financial dataset adds two distinct evidence sources:

- 80 prospectus PDFs plus provided parsed TXT files.
- A 10-table SQLite database with fund, stock, holding, industry, daily quote, scale, and holder-structure data.

The existing design and ADRs establish two constraints:

- The router lives in the agent layer, not inside the existing RAG MCP server.
- Table evidence uses compact retrieval summaries and raw payloads for answer generation.

The important extension is therefore not "more retrieval" alone. The system must translate finance questions into executable plans, run safe SQL or prospectus retrieval, merge evidence, and verify numeric/source correctness.

## Goals / Non-Goals

**Goals:**

- Add finance-specific question planning for routes, entities, dates, report periods, formulas, and answer constraints.
- Add a safe Text-to-SQL evidence path for the provided SQLite database.
- Add a prospectus evidence path that starts from provided TXT/PDF content and can evolve toward element-aware table/image/chart retrieval.
- Add hybrid orchestration for `sql_first` and `doc_first` workflows.
- Add verification for source priority, evidence sufficiency, numeric formulas, units, dates, and conflict handling.
- Add evaluation assets that allow iterative improvement by category.

**Non-Goals:**

- Do not rewrite the existing MCP RAG server or break current MCP tool contracts.
- Do not require a remote database service; SQLite remains the first supported structured store.
- Do not rely on image/chart VLM output for precise financial numbers unless explicit numeric labels are available.
- Do not expose `financial_qa` as an MCP server tool in the first implementation unless the agent layer is already stable.
- Do not assume parsed table XLSX files exist for the provided prospectus TXT placeholders.

## Decisions

### Decision 1: Use an agent-layer planner before routing

The first agent step will produce a `QuestionPlan` rather than only a simple route label.

```python
@dataclass
class QuestionPlan:
    route: Literal["pdf_rag", "text_to_sql", "hybrid"]
    task_type: str
    entities: dict[str, Any]
    time_scope: dict[str, Any]
    formula: Optional[str]
    evidence_need: list[str]
    sub_questions: list[dict[str, str]]
    answer_constraints: dict[str, Any]
    reason: str
```

Rationale: dataset questions often encode formulas and report-period semantics, such as limit-up days, daily returns, annualized returns, Q2 holdings, annual reports including semiannual reports, and decimal formatting. A route-only decision loses too much information.

Alternatives considered:

- Keyword-only router: simple, but brittle for formula and hybrid questions.
- Direct LLM-to-SQL: faster to prototype, but weak on safety, formulas, and repeatability.

### Decision 2: Treat formulas as domain plans, not prompt text

Common finance formulas will live in a formula registry and compile into SQL expressions or post-query computations:

- Daily return: `(close - prev_close) / prev_close`.
- Percent return: `(close / prev_close - 1) * 100`.
- Limit-up day: `(close / prev_close - 1) >= 0.098`.
- Net subscription: ending shares greater than beginning shares or purchase/redemption fields.
- Holding period return for top-N holdings.
- Aggregations such as count, sum, average, max, ranking, and top-k.

Rationale: exact-answer questions need reproducibility. Formula identifiers make verification and tests straightforward.

Alternatives considered:

- Ask the LLM to infer every formula in SQL: flexible, but hard to audit.
- Hard-code only final SQL templates: accurate for known questions, but too rigid for variations.

### Decision 3: Keep Text-to-SQL as an evidence path

The SQL path returns `EvidencePackage` instead of final natural language:

```python
@dataclass
class Evidence:
    evidence_id: str
    evidence_type: Literal["text", "table", "image", "chart", "sql_result"]
    source_type: Literal["pdf", "db"]
    content: str
    source: str
    score: Optional[float] = None
    page: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

SQL metadata includes generated SQL, database path, table names, columns, row count, formula, time scope, and elapsed time.

Rationale: final answering and verification must compare DB evidence with prospectus evidence in one format.

Alternatives considered:

- Return final answer from SQL tool: simpler for DB-only questions, but poor for hybrid composition.
- Expose only raw rows: precise, but forces every downstream step to rediscover source and formula context.

### Decision 4: Use provided prospectus TXT as baseline, then enhance PDF elements

The first prospectus path should support the provided parsed TXT files as stable ingestion inputs. Native PDF extraction and `DocumentElement` docstore support can be added after the baseline works.

Rationale: the dataset includes `pdf_txt_file` content with table placeholders, but no matching table XLSX files were found in the repository. TXT ingestion gives immediate retrieval coverage while PDF/table extraction improves later precision.

Alternatives considered:

- Start with native PDF table extraction: better long-term, but slower and more failure-prone.
- Ignore TXT files: wastes a useful dataset-provided baseline.

### Decision 5: Verification runs before final answer generation

Verifier checks operate on selected evidence packages:

- Source priority: user-specified source, then task type.
- Numeric consistency: formula, unit, date, report type, and rounding.
- Evidence sufficiency: do not fabricate missing PDF or DB evidence.
- Conflict behavior: report source disagreement rather than forcing a merge.

Rationale: finance QA correctness depends as much on the evidence path and calculation route as on retrieved text.

Alternatives considered:

- Verify after answer generation: catches some hallucinations, but loses structured calculation context.
- Trust reranker scores: useful for retrieval, not enough for numeric correctness.

### Decision 6: Make time and entity resolution explicit

Question planning and SQL execution will treat time-scope and entity-alias resolution as explicit stages. The planner identifies whether a question uses a trading date, calendar year, report period, per-fund latest report, or latest available record. The SQL path then resolves those instructions against the correct date column and entity scope.

Entity resolution covers fund name to fund code, stock name to stock code, stock code to stock name, and SQL result entities to prospectus company names for hybrid flows.

Rationale: the dataset frequently uses natural language names and subtle time expressions such as `最新的数据`, `年报(含半年报)`, `2021年12月季报`, and `使用每只基金当年最晚的定期报告数据计算`. If these remain implicit prompt details, SQL correctness becomes fragile.

Alternatives considered:

- Let SQL generation infer time and entity resolution directly from the question: concise, but difficult to verify.
- Require users to always provide codes and exact dates: simpler technically, but does not match the dataset workload.

## Risks / Trade-offs

- SQL generation errors -> Mitigation: compile common formula plans, enforce SELECT-only SQL, disallow multi-statements, repair at most twice, and log failed SQL.
- Large SQLite tables may be slow -> Mitigation: add schema registry indexes guidance, push filters into SQL, cap result rows, and summarize oversized results.
- Chinese table/column names complicate schema linking -> Mitigation: maintain aliases for table names, columns, report types, industry standards, and date fields.
- Latest-record and report-period ambiguity -> Mitigation: encode latest/per-period selection in `QuestionPlan` and verify the chosen date column in SQL evidence metadata.
- Prospectus table values may be missing from TXT placeholders -> Mitigation: first retrieve surrounding text; later add PDF table extraction and element docstore raw payload lookup.
- Hybrid entity mismatch between DB stock names and prospectus company names -> Mitigation: add entity normalization rules for stock code, stock name, company full name, and fund name.
- Numeric formula ambiguity -> Mitigation: store formula identifier and explanation in evidence metadata; ask for clarification only when required inputs are missing.
- Token overflow from raw tables or many rows -> Mitigation: evidence selection, table slicing, row limits, and trace records for truncated evidence.

## Migration Plan

1. Add new agent-layer and financial SQL modules without changing existing MCP tools.
2. Add schema/formula registries and unit tests against the local SQLite dataset.
3. Add prospectus TXT ingestion/query support using existing RAG stores.
4. Add hybrid orchestration and verifier components.
5. Add evaluation fixtures and regression cases before broad implementation.
6. Optionally expose a one-shot `financial_qa` tool only after the agent layer is stable.

Rollback is simple for early phases because new modules are additive. Existing MCP tools and stores remain usable if financial agent modules are disabled.

## Open Questions

- Should the first implementation call an LLM for `QuestionPlan`, use rules first, or use a hybrid rules-plus-LLM planner?
- Should `financial_qa` be a CLI/agent entrypoint first, or should it become an MCP tool after the evidence paths stabilize?
- Which subset of `question.json` should become the initial golden evaluation set?
- Should native PDF table extraction use `pdfplumber` only at first, or include optional Camelot/Tabula fallbacks behind configuration?
