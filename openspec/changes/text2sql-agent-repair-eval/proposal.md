## Why

The financial Text2SQL path needs to move beyond single-shot rule compilation so it can recover from schema-linking gaps, model SQL errors, and empty executions without fabricating answers. This change defines the fourth-stage Text2SQL Agent route: `rule/lora/api -> execute error -> repair -> re-execute -> log/eval`, making candidate generation, repair, retry, logging, and evaluation explicit.

## What Changes

- Extend the SQL evidence path from rule-only compilation into a candidate-based Text2SQL Agent with rule, SQL-LoRA, and API-backed SQL generation stages.
- Define deterministic fallback eligibility and candidate selection rules so the runtime can decide when to stop on rule success, when to enter LoRA/API fallback, and when an empty SQL result is acceptable versus repairable.
- Add bounded SQL repair after safety or execution failures, using error context, prior SQL, plan metadata, schema hints, and retrieved SQL examples.
- Require every generated or repaired SQL candidate to pass the existing SQL safety checker before execution.
- Add re-execution after repair with explicit retry limits and structured attempt metadata.
- Persist detailed attempt logs for rule, LoRA, API, repair, safety, execution, and selection outcomes.
- Extend evaluation to measure candidate source quality, repair success, re-execution success, unsafe rejection, empty-result handling, and per-family fallback lift.
- Add explicit acceptance and promotion gates so LoRA/API fallback can be evaluated against rule-only baselines before broader enablement.
- Add agent trace requirements so the final response can explain which SQL source was selected and why.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `financial-sql-evidence`: Add rule/LoRA/API SQL candidate generation, bounded repair, re-execution, candidate selection, and detailed attempt metadata.
- `financial-evaluation`: Add evaluation requirements for fallback lift, repair success, re-execution behavior, candidate-source comparison, and SQL-agent regression cases.
- `financial-hybrid-answering`: Add trace requirements for SQL candidate attempts, selected SQL source, repair stages, and final evidence provenance.

## Impact

- Affects `src/financial_sql/text_to_sql_tool.py`, SQL generator abstractions, SQL safety and executor integration, and SQL query logging.
- Adds local SQL-LoRA and API SQL generator integration points, preferably behind optional configuration flags.
- Adds or extends evaluation fixtures for rule success, LoRA fallback, API fallback, execution error repair, empty-result repair, unsafe SQL rejection, and all-candidates-failed behavior.
- Adds metadata fields such as `sql_source`, `fallback_attempts`, `repair_attempts`, `selected_reason`, `candidate_count`, and per-attempt safety/execution status.
- Adds final route outcome fields such as `final_failure_code`, `accepted_result_kind`, `fallback_eligibility_reason`, and evaluation gate inputs needed for strict acceptance reviews.
- Does not bypass existing SQL safety checks or change the SQLite database contract.
