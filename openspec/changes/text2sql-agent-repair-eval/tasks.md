## 1. Candidate Pipeline Foundations

- [x] 1.1 Define `SQLCandidate` and `SQLAttempt` data structures with source, SQL, metadata, parent attempt, safety result, execution result, repair reason, elapsed time, and selected reason fields
- [x] 1.2 Add a generator interface for rule, LoRA, API, and repair-backed SQL candidate sources
- [x] 1.3 Refactor `TextToSQLEvidenceTool` so rule compilation emits a rule candidate while preserving the existing public `query(plan, question)` contract
- [x] 1.4 Add configuration flags for enabling LoRA fallback, API fallback, empty-result repair, and maximum repair attempts with rule-only behavior as the default
- [x] 1.5 Define stable failure codes and accepted-result kinds for attempt metadata, evidence metadata, traces, and evaluation outputs

## 2. Rule, LoRA, and API Generation

- [x] 2.1 Implement deterministic candidate ordering: rule first, SQL-LoRA second when enabled, API SQL generation last when enabled
- [x] 2.2 Implement SQL-LoRA generator integration through a local HTTP endpoint with timeout, unavailable-service handling, and SQL-only response extraction
- [x] 2.3 Implement API SQL generator integration behind optional configuration with explicit disabled-by-default behavior
- [x] 2.4 Add BM25 SQL example retrieval support for LoRA/API prompts using existing SQL examples when configured
- [x] 2.5 Add unit tests proving LoRA/API generators are skipped when disabled and invoked only after eligible rule failures or empty results
- [x] 2.6 Define fallback eligibility policy for compile failure, unsafe SQL, execution failure, and repairable empty results, including how question-plan or task-family policy marks empty results as terminal versus fallback-worthy

## 3. Safety, Execution, Repair, and Re-execution

- [x] 3.1 Route every rule, LoRA, API, and repaired SQL candidate through `SQLSafetyChecker` before execution
- [x] 3.2 Implement execution failure handling that captures SQLite error, prior SQL, plan metadata, schema hints, and example context for repair
- [x] 3.3 Implement bounded repair candidate generation for safety rejection, execution failure, and permitted empty-result repair
- [x] 3.4 Re-run safety and execution for repaired candidates and stop after the first successful acceptable evidence result
- [x] 3.5 Return a failed evidence package with complete attempt metadata when all candidates and repairs fail
- [x] 3.6 Add unit tests for unsafe generated SQL, unsafe repaired SQL, execution-error repair, empty-result repair, repair retry limits, and all-candidates-failed behavior
- [x] 3.7 Define deterministic selection rules for accepted empty results versus continued fallback so later sources cannot replace an earlier acceptable outcome

## 4. Logging and Evidence Metadata

- [x] 4.1 Extend SQL query logging to capture source, attempt id, parent attempt id, repair reason, safety status, execution status, selected flag, row count, error, and elapsed time
- [x] 4.2 Add `sql_source`, `fallback_attempts`, `repair_attempts`, `candidate_count`, and `selected_reason` to SQL evidence metadata
- [x] 4.3 Add `final_failure_code`, `accepted_result_kind`, and `fallback_eligibility_reason` to terminal evidence metadata
- [x] 4.3 Ensure success, empty, and failed evidence packages all include enough attempt metadata to reconstruct the Text2SQL Agent route
- [x] 4.4 Add tests for log rows and metadata shape across rule success, accepted empty result, LoRA fallback success, API fallback success, repair success, and failure outcomes

## 5. Agent Trace Integration

- [x] 5.1 Extend SQL evidence trace stages to include candidate generation, safety check, execution, repair, re-execution, and selection events
- [x] 5.2 Preserve selected SQL source and fallback attempts in SQL-only final answer traces
- [x] 5.3 Preserve selected SQL source and fallback attempts in hybrid traces before merge and verification
- [x] 5.4 Add orchestrator tests proving SQL-only and hybrid answers expose candidate route metadata without changing final answer shape

## 6. Evaluation and Regression Coverage

- [x] 6.1 Extend evaluation result schemas to report metrics by SQL source: rule, LoRA, API, and repair
- [x] 6.2 Add fallback lift metrics comparing rule-only, rule-plus-LoRA, and rule-plus-LoRA-plus-API runs by SQL task family
- [x] 6.3 Add repair metrics for safety pass, execution success, non-empty result rate, correctness, retry exhaustion, and latency
- [x] 6.4 Add regression fixtures for unsafe fallback SQL, execution error repair, empty-result repair, all-candidates-failed, and logging metadata completeness
- [x] 6.5 Add tests proving evaluation reports candidate source metrics, fallback lift, repair success, unsafe repair rejection, and complete attempt metadata
- [x] 6.6 Define evaluation promotion gates for enabling LoRA or API fallback by default, including correctness delta, unsafe rejection, latency budget, and metadata completeness checks

## 7. Validation and Documentation

- [x] 7.1 Document configuration for SQL-LoRA endpoint, API fallback, empty-result repair, and repair retry limits
- [x] 7.2 Document the Text2SQL Agent route `rule/lora/api -> execute error -> repair -> re-execute -> log/eval`
- [x] 7.3 Run focused SQL evidence, orchestrator trace, and evaluation tests
- [x] 7.4 Run `openspec validate text2sql-agent-repair-eval --no-interactive` and fix any spec formatting issues
