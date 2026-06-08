## 1. Shared Contracts and Module Structure

- [x] 1.1 Create additive module folders for `src/agentic`, `src/financial_sql`, and prospectus evidence extensions without changing existing MCP tool contracts
- [x] 1.2 Define shared dataclasses for `QuestionPlan`, `Evidence`, `EvidencePackage`, and `VerificationReport`
- [x] 1.3 Add serialization helpers for planner, evidence, and verifier outputs
- [x] 1.4 Add unit tests for shared type validation and serialization

## 2. Financial Question Planning

- [x] 2.1 Implement a rule-first question planner that classifies `pdf_rag`, `text_to_sql`, and `hybrid` routes
- [x] 2.2 Add entity extraction for stock codes, fund codes, fund names, company names, dates, report periods, and industry standards
- [ ] 2.3 Add time-scope normalization for latest records, annual ranges, quarter-end dates, report types, and per-entity latest reports
- [ ] 2.4 Add entity-alias planning for fund name to code, stock name to code, and SQL result to prospectus company mapping
- [ ] 2.5 Add task subtype detection for point lookup, aggregate statistics, ranking, formula calculation, report-period query, latest-record lookup, and disclosure fact retrieval
- [ ] 2.6 Add formula and answer-constraint detection for daily return, percent return, limit-up days, price range, open-above-previous-close days, low-volume days, annualized return, top-N, count, sum, average, and rounding precision
- [ ] 2.7 Add planner tests using representative questions from `bs_challenge_financial_14b_dataset/question.json`

## 3. Financial SQL Evidence Path

- [ ] 3.1 Implement a schema registry for the 10-table SQLite database with table metadata, column metadata, aliases, date fields, and common joins
- [x] 3.2 Implement a formula registry that maps known finance formulas to SQL expressions or post-query computation plans
- [ ] 3.3 Implement schema linking from `QuestionPlan` to candidate tables, columns, filters, joins, and order/aggregate operations
- [ ] 3.4 Implement SQL generation or compilation for common point lookup, aggregate, ranking, holding, industry, and quote queries
- [ ] 3.5 Implement entity alias resolution for fund names, stock names, fund codes, and stock codes
- [ ] 3.6 Implement latest-record and report-period selection for maximum date, per-fund latest report, annual report, semiannual report, and quarterly report scopes
- [ ] 3.7 Implement calculation patterns for price range, open-above-previous-close days, low-volume days, annualized return, fund share movement, bond holdings, and convertible-bond industry aggregation
- [x] 3.8 Implement SQL safety checks for SELECT-only, single-statement, no write/DDL operations, and safe row limits
- [x] 3.9 Implement SQL execution against the local Bosera SQLite database with timeout, row cap, and empty-result handling
- [ ] 3.10 Implement SQL repair with at most two retry attempts for generation or schema-linking failures
- [ ] 3.11 Implement SQL evidence packaging with SQL, database path, table names, columns, row count, formula metadata, time scope, entity resolution metadata, and elapsed time
- [ ] 3.12 Implement SQL query logging to a local SQLite log store
- [ ] 3.13 Add unit and integration tests for safe SQL, formula execution, row limiting, empty results, latest-record selection, report-period selection, entity alias resolution, and failed SQL behavior

## 4. Prospectus Evidence Path

- [x] 4.1 Add support for ingesting provided parsed prospectus TXT files as baseline prospectus documents
- [x] 4.2 Preserve table placeholder tokens and nearby text context during TXT ingestion
- [x] 4.3 Mark retrieved table placeholders as `raw_table_unavailable` when no raw rows or columns can be recovered
- [x] 4.4 Wrap existing hybrid retrieval results into prospectus `EvidencePackage` objects with source metadata
- [ ] 4.5 Add retrieval tests for company business, risk, shareholder, patent, supplier, customer, fundraising-project, and financial-table questions
- [ ] 4.6 Add element-aware metadata extension points for `element_id`, `element_type`, `page`, and raw payload availability
- [x] 4.7 Implement an `ElementDocstore` design stub or interface for future raw table/image/chart retrieval
- [ ] 4.8 Add tests that precise table-value answers become partial or insufficient when only placeholders are available
- [ ] 4.9 Add tests that existing `query_knowledge_hub` behavior remains compatible

## 5. Hybrid Orchestration and Verification

- [x] 5.1 Implement the financial orchestrator for single-path `text_to_sql` and `pdf_rag` execution
- [ ] 5.2 Implement `sql_first` hybrid orchestration with entity normalization from SQL results to prospectus sub-questions
- [ ] 5.3 Implement `doc_first` hybrid orchestration with entity or disclosure-term extraction from prospectus results to SQL sub-questions
- [x] 5.4 Implement evidence merging with evidence ID preservation, source metadata preservation, and duplicate grouping
- [ ] 5.5 Implement verifier source-priority rules for user-specified prospectus or database sources
- [x] 5.6 Implement verifier sufficiency rules for missing SQL or prospectus evidence
- [ ] 5.7 Implement verifier numeric checks for formulas, units, dates, report periods, and rounding constraints
- [ ] 5.8 Implement final answer formatting for percentages, monetary units, leading-zero identifiers, multi-year values, ranked results, and top-N lists
- [ ] 5.9 Implement final answer generation from selected evidence, question plan, and verification report
- [ ] 5.10 Add trace stages for planning, SQL evidence, prospectus evidence, merge, verification, and answer generation
- [ ] 5.11 Add tests for SQL-only, prospectus-only, `sql_first`, `doc_first`, partial, insufficient, conflict, and answer-formatting cases

## 6. Financial Evaluation

- [ ] 6.1 Create an initial golden evaluation set from representative dataset questions across SQL, prospectus, and hybrid categories
- [ ] 6.2 Implement planner evaluation metrics for route accuracy, hybrid mode accuracy, entity extraction, and formula detection
- [ ] 6.3 Implement SQL evaluation metrics for safety pass, execution success, result correctness, row count, and normalized value tolerance
- [ ] 6.4 Implement prospectus evaluation metrics for source hit, page/location hit where available, evidence type hit, and context precision
- [ ] 6.5 Implement hybrid evaluation metrics for tool sequence, cross-source entity match, final answer correctness, and source coverage
- [ ] 6.6 Implement verifier evaluation metrics for source priority, conflict detection, abstention, partial, and insufficient statuses
- [x] 6.7 Implement per-family reporting for point lookup, latest-record lookup, industry aggregation, quote formula, holding rank, fund scale, holder structure, bond holding, convertible-bond industry, and prospectus table facts
- [ ] 6.8 Add answer-formatting checks for rounding, percentage signs, monetary units, leading-zero identifiers, ordering, and top-N constraints
- [ ] 6.9 Add regression cases for unsafe SQL, empty SQL results, schema ambiguity, missing raw table evidence, low-confidence chart evidence, and token overflow
- [ ] 6.10 Expose evaluation results through the existing CLI or dashboard evaluation surface

## 7. Documentation and Readiness

- [x] 7.1 Update project documentation with the financial agent architecture and module responsibilities
- [ ] 7.2 Document supported formulas, table aliases, report-period mappings, and source-priority rules
- [ ] 7.3 Document how to ingest the prospectus TXT baseline and how to point SQL evidence to the local dataset database
- [x] 7.4 Run OpenSpec validation for this change and fix any spec formatting issues
- [x] 7.5 Run the focused test suite and record known gaps before broader implementation
