## Context

The current release Text2SQL path is rule-first: a `QuestionPlan` is compiled into SQL, checked by `SQLSafetyChecker`, executed by `SQLiteQueryExecutor`, and returned as SQL evidence. The older `7_不会ML` project contributes a useful complementary pattern: when prompt-generated SQL fails or returns empty results, a SQL-LoRA model can generate a domain-specific replacement SQL candidate. The target design combines these ideas without weakening the release project's safety, evidence, verifier, or evaluation boundaries.

The fourth-stage route is: `rule/lora/api -> execute error -> repair -> re-execute -> log/eval`. Rule compilation remains preferred. SQL-LoRA becomes the first domain fallback. API SQL generation becomes a final long-tail fallback. All generated and repaired SQL remains read-only, single-statement, safety-checked, executed through the same executor, and recorded as evidence metadata.

## Goals / Non-Goals

**Goals:**

- Introduce a candidate-based Text2SQL Agent that tries rule, LoRA, and API SQL sources in a deterministic order.
- Add bounded repair after safety rejection, execution failure, or empty results, then re-run safety and execution.
- Preserve the existing `TextToSQLEvidenceTool` contract: return `EvidencePackage`, never a final answer.
- Record per-attempt metadata for SQL source, SQL text, safety status, execution status, error, row count, repair reason, and selected reason.
- Extend evaluation so rule, LoRA, API, repair, and re-execution quality can be measured separately.

**Non-Goals:**

- Do not bypass `SQLSafetyChecker` for any rule, LoRA, API, or repaired SQL.
- Do not make external API SQL generation mandatory for local/offline deployments.
- Do not replace deterministic rule compilers that already handle supported task families.
- Do not train a LoRA model in this change; only define integration points and evaluation requirements.

## Decisions

1. Keep rule compilation as the primary SQL source.

Rule SQL is most explainable and easiest to test. LoRA and API SQL generation are fallback sources used when rule compilation fails, rule SQL execution fails, or rule SQL produces an empty result where the plan expects data. Alternative considered: make LoRA the primary source. Rejected because it would reduce determinism and increase safety pressure.

2. Model SQL generation as candidates with common validation.

Each source returns a `SQLCandidate` with `source`, `sql`, `metadata`, and optional `parent_attempt_id`. The SQL tool handles all candidates through the same safety, execution, repair, and logging pipeline. Alternative considered: separate code paths for rule, LoRA, and API. Rejected because divergent paths make logging and evaluation harder.

3. Repair is bounded and evidence-aware.

Repair receives question, plan, schema hints, previous SQL, safety or execution error, empty-result context, and optional BM25 examples. Repaired SQL is treated as a new candidate and must pass safety before execution. Retry limits are source-aware but default to at most two repair attempts per selected candidate family. Alternative considered: unbounded repair loop. Rejected because it risks latency spikes and opaque behavior.

4. SQL-LoRA is the first fallback, API is the final fallback.

SQL-LoRA should capture local schema and competition-style patterns with lower latency and no data egress. API generation is useful for long-tail reasoning and complex questions outside the LoRA training distribution. Both are optional configuration-backed integrations.

5. Evaluation owns promotion decisions.

The runtime should not assume LoRA or API is better. Evaluation reports compare rule-only, rule-plus-LoRA, and rule-plus-LoRA-plus-API behavior by task family, execution success, correctness, safety rejection, repair lift, and latency.

6. Fallback eligibility is explicit and deterministic.

The SQL route classifies each failure before moving to the next source. Rule, LoRA, and API each become eligible only after the previous source family fails by compile failure, safety rejection, execution failure, or a policy-marked repairable empty result. Empty results are not universally repairable: the runtime must consult question-plan metadata or task-family policy to decide whether an empty result is a valid terminal outcome or should enter repair/fallback. Alternative considered: treat every empty result as fallback-worthy. Rejected because some finance questions legitimately return zero rows and should remain explicit empty evidence.

7. Candidate selection uses first acceptable evidence by source order.

The runtime evaluates candidate families in fixed order: `rule -> lora -> api`. Within a family, the original candidate is tried before repaired candidates. The first candidate that produces acceptable evidence is selected and terminates the route. "Acceptable evidence" means a safe execution outcome that either returns rows or is an explicit empty result that policy allows as terminal. Later families cannot replace an earlier acceptable result. Alternative considered: scoring all successful candidates and picking the "best". Rejected because it complicates traceability and weakens deterministic evaluation.

8. Failure taxonomy is part of the contract.

Every terminal or intermediate attempt is classified with stable failure semantics such as `compile_failed`, `unsafe_sql`, `execution_error`, `empty_result`, `repair_exhausted`, `source_disabled`, `source_unavailable`, or `all_candidates_failed`. This taxonomy feeds logs, evidence metadata, hybrid traces, and evaluation. Alternative considered: free-form error text only. Rejected because evaluation and acceptance review need consistent categories.

9. Evaluation gates are defined before enabling fallback by default.

Evaluation must report baseline-versus-fallback comparisons using the same golden set and configuration snapshot. LoRA or API fallback is not eligible for default enablement unless evaluation shows non-negative correctness delta, no increase in unsafe execution, bounded latency within configured budget, and complete attempt metadata coverage. Alternative considered: enable fallback after qualitative spot checks. Rejected because the route introduces new external dependencies and retry behavior that require measurable acceptance gates.

## Risks / Trade-offs

- More candidates can increase latency. Mitigation: use deterministic ordering, stop after first successful non-empty result when allowed, and cap repairs.
- Empty-result handling can become inconsistent across task families. Mitigation: require a plan or task-family policy to classify whether empty is terminal, repairable, or fallback-eligible.
- API fallback can leak sensitive prompts if enabled carelessly. Mitigation: make API fallback disabled by default and document configuration clearly.
- Repair can mask planner or schema bugs. Mitigation: log original failure and repaired SQL separately, and include repair reason in evaluation.
- Empty-result repair can generate overly broad SQL. Mitigation: preserve row caps, safety checks, plan constraints, and selected reason metadata.
- Multiple SQL sources can make answers harder to explain. Mitigation: return `sql_source`, `fallback_attempts`, `repair_attempts`, and trace stages in metadata.

## Migration Plan

1. Add candidate and generator interfaces behind optional configuration with rule-only behavior as the default.
2. Add SQL-LoRA fallback and repair support while preserving existing `TextToSQLEvidenceTool.query()` output shape.
3. Add API fallback as an optional final source.
4. Extend logs and evaluation fixtures before enabling fallbacks broadly.
5. Roll back by disabling LoRA/API fallback configuration; rule compilation and existing safety/executor paths remain available.

## Open Questions

- Which SQL-LoRA endpoint and prompt format should become the default local development contract?
- Which question-plan field or task-family policy will classify whether empty SQL evidence is terminal, repairable, or eligible for source fallback?
- What exact latency budget and correctness delta threshold should gate default enablement of LoRA or API fallback in release environments?
