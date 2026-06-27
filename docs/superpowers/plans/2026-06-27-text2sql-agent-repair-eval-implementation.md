# Text2SQL Agent Repair Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `rule/lora/api -> execute error -> repair -> re-execute -> log/eval` Text2SQL agent route in the release financial project while preserving rule-only behavior as the default and keeping acceptance criteria measurable.

**Architecture:** Keep `TextToSQLEvidenceTool` as the orchestration boundary, but move the new candidate route mechanics into focused `src/financial_sql/` helper modules for candidate types, generator adapters, and fallback policy. Thread the resulting route metadata into executor logs, orchestrator traces, and `FinancialEvalRunner`, with configuration owned by `financial_platform` settings so fallback can be enabled incrementally.

**Tech Stack:** Python 3, SQLite, existing `QuestionPlan` / `EvidencePackage` types, YAML config, pytest, local HTTP for LoRA integration, optional API-backed SQL generation.

---

## Scope Split

This spec spans three implementation surfaces that should ship in order:

1. **SQL route foundation**: candidate types, config, fallback policy, and rule-only compatibility.
2. **Runtime route behavior**: LoRA/API/repair execution path, logging, and orchestrator trace propagation.
3. **Acceptance layer**: evaluation source metrics, promotion gates, docs, and validation.

Do not try to land all three in one commit. Each task below is intended to produce a working, testable increment.

## File Structure

**Create:**
- `src/financial_sql/agent_types.py` - dataclasses / literals for `SQLCandidate`, `SQLAttempt`, route outcomes, and stable failure codes.
- `src/financial_sql/fallback_policy.py` - deterministic source ordering, empty-result classification, and route stop/continue decisions.
- `src/financial_sql/generators.py` - generator interfaces and adapters for rule, LoRA, API, and repair-backed SQL candidates.
- `tests/unit/test_financial_sql_agent_policy.py` - focused tests for failure taxonomy, fallback eligibility, and accepted empty-result policy.
- `tests/fixtures/financial_sql_agent_eval_cases.json` - optional focused evaluation fixture set for source, repair, and promotion-gate checks.

**Modify:**
- `src/financial_sql/text_to_sql_tool.py` - refactor from single SQL compile/execute path to candidate route orchestration.
- `src/financial_sql/sql_executor.py` - extend SQL log schema and insert path for per-attempt metadata.
- `src/agentic/orchestrator.py` - propagate SQL route metadata into SQL-only and hybrid traces.
- `src/local_platform/config.py` - parse Text2SQL agent feature flags and endpoint settings from `financial_platform`.
- `src/local_platform/service.py` - construct `TextToSQLEvidenceTool` with parsed agent configuration.
- `src/observability/evaluation/financial_eval_runner.py` - add source metrics, repair metrics, and fallback promotion gates.
- `scripts/evaluate.py` - ensure financial evaluation can exercise fallback-enabled agents and report new thresholds.
- `scripts/financial_query.py` - optionally load fallback config so smoke queries use the same runtime path.
- `config/settings.example.yaml` - document disabled-by-default LoRA/API/repair configuration.
- `docs/financial/local-platform.md` - explain local SQL-LoRA endpoint and fallback knobs.
- `docs/financial/financial-agentic-rag-design.md` - document the new Text2SQL route and acceptance gates.

**Test:**
- `tests/unit/test_text_to_sql_tool.py`
- `tests/unit/test_sql_executor.py`
- `tests/unit/test_financial_orchestrator.py`
- `tests/unit/test_local_platform_config.py`
- `tests/unit/test_financial_eval_runner.py`
- `tests/unit/test_financial_eval_thresholds.py`
- `tests/integration/test_financial_sql_dataset.py`

## Task 1: Add Candidate Types, Failure Taxonomy, and Config Surface

**Files:**
- Create: `src/financial_sql/agent_types.py`
- Create: `src/financial_sql/fallback_policy.py`
- Create: `tests/unit/test_financial_sql_agent_policy.py`
- Modify: `src/local_platform/config.py`
- Modify: `src/local_platform/service.py`
- Modify: `config/settings.example.yaml`
- Test: `tests/unit/test_financial_sql_agent_policy.py`
- Test: `tests/unit/test_local_platform_config.py`

- [ ] **Step 1: Write the failing policy and config tests**

```python
from src.financial_sql.fallback_policy import classify_terminal_outcome
from src.local_platform.config import resolve_platform_config


def test_empty_result_can_be_terminal_when_task_family_disallows_fallback():
    outcome = classify_terminal_outcome(
        status="empty",
        task_family="latest-record lookup",
        empty_result_policy="terminal",
    )
    assert outcome.accepted_result_kind == "empty"
    assert outcome.should_fallback is False


def test_platform_config_reads_text2sql_agent_flags(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text(
        "financial_platform:\n"
        "  text2sql_agent:\n"
        "    enable_lora_fallback: true\n"
        "    lora_endpoint: http://127.0.0.1:8888/SQL\n"
        "    max_repair_attempts: 2\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("FINANCIAL_DEMO_DB_PATH", raising=False)

    config = resolve_platform_config(settings_path=settings_file)

    assert config.text2sql_agent.enable_lora_fallback is True
    assert config.text2sql_agent.lora_endpoint == "http://127.0.0.1:8888/SQL"
    assert config.text2sql_agent.max_repair_attempts == 2
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
pytest tests/unit/test_financial_sql_agent_policy.py tests/unit/test_local_platform_config.py -q
```

Expected: failures for missing `fallback_policy` module and missing `text2sql_agent` config fields.

- [ ] **Step 3: Implement stable agent types and parsed config**

```python
@dataclass(frozen=True)
class TextToSQLAgentConfig:
    enable_lora_fallback: bool = False
    lora_endpoint: str | None = None
    enable_api_fallback: bool = False
    api_model: str | None = None
    enable_empty_result_repair: bool = False
    max_repair_attempts: int = 2


FAILURE_CODES = {
    "compile_failed",
    "unsafe_sql",
    "execution_error",
    "empty_result",
    "repair_exhausted",
    "source_disabled",
    "source_unavailable",
    "all_candidates_failed",
}
```

Implementation notes:
- Add `TextToSQLAgentConfig` as a field on `PlatformConfig`.
- Parse `financial_platform.text2sql_agent` in `resolve_platform_config()`.
- Keep all fallback features disabled by default.
- In `LocalFinancialPlatformService._get_orchestrator()`, pass the parsed config into `TextToSQLEvidenceTool(...)`.

- [ ] **Step 4: Re-run the config and policy tests**

Run:

```bash
pytest tests/unit/test_financial_sql_agent_policy.py tests/unit/test_local_platform_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the foundation-only config change**

```bash
git add src/financial_sql/agent_types.py src/financial_sql/fallback_policy.py src/local_platform/config.py src/local_platform/service.py config/settings.example.yaml tests/unit/test_financial_sql_agent_policy.py tests/unit/test_local_platform_config.py
git commit -m "feat: add text2sql agent config and failure taxonomy"
```

## Task 2: Refactor `TextToSQLEvidenceTool` into a Deterministic Candidate Route

**Files:**
- Create: `src/financial_sql/generators.py`
- Modify: `src/financial_sql/text_to_sql_tool.py`
- Modify: `tests/unit/test_text_to_sql_tool.py`
- Modify: `tests/integration/test_financial_sql_dataset.py`
- Modify: `scripts/financial_query.py`

- [ ] **Step 1: Add failing tests for source order, accepted empty results, and final failure codes**

```python
def test_rule_success_stops_before_lora_and_api(tmp_path):
    tool = build_tool_with_stub_generators(tmp_path, rule_sql='SELECT 1 AS value', lora_sql='SELECT 2', api_sql='SELECT 3')
    package = tool.query(plan_for_point_lookup(), "question")
    assert package.metadata["sql_source"] == "rule"
    assert package.metadata["candidate_count"] == 1


def test_terminal_empty_result_does_not_trigger_fallback(tmp_path):
    tool = build_tool_with_stub_generators(
        tmp_path,
        rule_sql='SELECT * FROM "A股票日行情表" WHERE 1 = 0',
        empty_result_policy="terminal",
    )
    package = tool.query(plan_for_point_lookup(), "question")
    assert package.metadata["accepted_result_kind"] == "empty"
    assert package.metadata["fallback_attempts"] == []


def test_all_candidates_failed_returns_stable_failure_code(tmp_path):
    tool = build_tool_with_failing_generators(tmp_path)
    package = tool.query(plan_for_point_lookup(), "question")
    assert package.metadata["status"] == "failed"
    assert package.metadata["final_failure_code"] == "all_candidates_failed"
```

- [ ] **Step 2: Run the focused SQL tool tests**

Run:

```bash
pytest tests/unit/test_text_to_sql_tool.py -q
```

Expected: failures because `TextToSQLEvidenceTool` still short-circuits through `_compile_with_repair()`.

- [ ] **Step 3: Add generator adapters and route orchestration**

```python
class SQLGenerator(Protocol):
    def generate(self, plan: Any, question: str, context: dict[str, Any]) -> SQLCandidate | None: ...


class RuleSQLGenerator:
    def generate(self, plan: Any, question: str, context: dict[str, Any]) -> SQLCandidate | None:
        sql, metadata = compile_rule_sql(plan)
        return SQLCandidate(source="rule", sql=sql, metadata=metadata)
```

Implementation notes:
- Keep the existing rule compiler logic inside `text_to_sql_tool.py`, but wrap its output as the rule candidate.
- Use `fallback_policy` to decide whether empty results are terminal, repairable, or eligible for source fallback.
- Preserve the existing public `query(plan, question)` signature and `EvidencePackage` return shape.
- Update `scripts/financial_query.py` so smoke queries can opt into the configured agent path instead of constructing a bare default tool.

- [ ] **Step 4: Re-run the focused SQL tool tests and the dataset smoke**

Run:

```bash
pytest tests/unit/test_text_to_sql_tool.py tests/integration/test_financial_sql_dataset.py -q
```

Expected: PASS with rule-only behavior still working when fallback is disabled.

- [ ] **Step 5: Commit the deterministic route refactor**

```bash
git add src/financial_sql/generators.py src/financial_sql/text_to_sql_tool.py scripts/financial_query.py tests/unit/test_text_to_sql_tool.py tests/integration/test_financial_sql_dataset.py
git commit -m "feat: refactor text-to-sql into deterministic candidate route"
```

## Task 3: Add LoRA/API Fallback, Repair, Attempt Logging, and Trace Propagation

**Files:**
- Modify: `src/financial_sql/text_to_sql_tool.py`
- Modify: `src/financial_sql/sql_executor.py`
- Modify: `src/agentic/orchestrator.py`
- Modify: `tests/unit/test_sql_executor.py`
- Modify: `tests/unit/test_financial_orchestrator.py`

- [ ] **Step 1: Add failing tests for retry flow, log metadata, and hybrid trace preservation**

```python
def test_execution_error_triggers_repair_then_reexecution(tmp_path):
    tool = build_tool_with_stub_generators(
        tmp_path,
        rule_sql='SELECT missing_column FROM "A股票日行情表"',
        repair_sql='SELECT "股票代码" FROM "A股票日行情表" LIMIT 1',
        enable_empty_result_repair=False,
    )
    package = tool.query(plan_for_point_lookup(), "question")
    assert package.metadata["sql_source"] == "repair"
    assert package.metadata["repair_attempts"][0]["failure_code"] == "execution_error"


def test_sql_query_log_records_attempt_context(tmp_path):
    result = run_logged_query(tmp_path)
    row = load_single_log_row(result.log_db_path)
    assert row["source"] == "rule"
    assert row["attempt_id"] == "attempt-1"
    assert row["selected"] == 1


def test_hybrid_trace_preserves_sql_final_failure_code():
    result = orchestrator.answer("hybrid question")
    sql_stage = next(stage for stage in result["trace"]["stages"] if stage["stage"] == "sql_evidence")
    assert sql_stage["final_failure_code"] == "all_candidates_failed"
```

- [ ] **Step 2: Run the logging and trace tests to verify the new gaps**

Run:

```bash
pytest tests/unit/test_sql_executor.py tests/unit/test_financial_orchestrator.py -q
```

Expected: FAIL because the executor log schema only knows `question/sql/status/error/row_count/elapsed_ms`, and orchestrator stages only record `question` and `evidence_count`.

- [ ] **Step 3: Implement fallback generators, bounded repair, and additive log schema migration**

```python
def _ensure_log_schema(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS sql_query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            sql TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            row_count INTEGER NOT NULL,
            elapsed_ms REAL NOT NULL,
            source TEXT,
            attempt_id TEXT,
            parent_attempt_id TEXT,
            failure_code TEXT,
            selected INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
```

Implementation notes:
- Add a local HTTP LoRA generator with timeout and "service unavailable" normalization to `source_unavailable`.
- Keep API fallback behind config and disabled by default.
- For repair, pass prior SQL, safety reason or execution error, plan metadata, and optional BM25 examples into a repair generator.
- Extend orchestrator `sql_evidence` stages with `sql_source`, `accepted_result_kind`, `final_failure_code`, `repair_attempts`, and `fallback_attempts`.
- Do not change the final answer shape; only extend trace and source metadata.

- [ ] **Step 4: Re-run SQL, logging, and orchestrator tests**

Run:

```bash
pytest tests/unit/test_text_to_sql_tool.py tests/unit/test_sql_executor.py tests/unit/test_financial_orchestrator.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit runtime fallback, repair, and trace support**

```bash
git add src/financial_sql/text_to_sql_tool.py src/financial_sql/sql_executor.py src/agentic/orchestrator.py tests/unit/test_sql_executor.py tests/unit/test_financial_orchestrator.py tests/unit/test_text_to_sql_tool.py
git commit -m "feat: add sql fallback repair logging and trace metadata"
```

## Task 4: Extend Financial Evaluation with Source Metrics and Promotion Gates

**Files:**
- Modify: `src/observability/evaluation/financial_eval_runner.py`
- Modify: `scripts/evaluate.py`
- Modify: `tests/unit/test_financial_eval_runner.py`
- Modify: `tests/unit/test_financial_eval_thresholds.py`
- Create or Modify: `tests/fixtures/financial_sql_agent_eval_cases.json`

- [ ] **Step 1: Add failing evaluation tests for source metrics and gate failures**

```python
def test_eval_runner_reports_source_breakdown_and_selected_distribution():
    result = FinancialEvalRunner(agent=FallbackAgent()).run(load_cases("financial_sql_agent_eval_cases.json"))
    assert result["sql_sources"]["rule"]["count"] == 1
    assert result["sql_sources"]["lora"]["count"] == 1
    assert result["sql_sources"]["repair"]["execution_success_rate"] == 1.0


def test_failed_promotion_gate_reports_reason_and_case_ids():
    result = FinancialEvalRunner(
        agent=SlowFallbackAgent(),
        thresholds={"fallback_latency_budget_ms": 800.0},
    ).run(load_cases("financial_sql_agent_eval_cases.json"))
    assert result["passed"] is False
    assert result["failed_thresholds"][0]["metric"] == "fallback_latency_budget_ms"
```

- [ ] **Step 2: Run the focused evaluation tests**

Run:

```bash
pytest tests/unit/test_financial_eval_runner.py tests/unit/test_financial_eval_thresholds.py -q
```

Expected: FAIL because the current runner only reports route / SQL / hybrid / formatting aggregates.

- [ ] **Step 3: Implement source-aware evaluation and CLI support**

```python
output["sql_sources"] = {
    "rule": source_totals["rule"].to_report(),
    "lora": source_totals["lora"].to_report(),
    "api": source_totals["api"].to_report(),
    "repair": source_totals["repair"].to_report(),
}
output["promotion_gates"] = {
    "correctness_delta_ok": correctness_delta >= configured_delta,
    "unsafe_rejection_ok": unsafe_rate <= configured_unsafe_tolerance,
    "latency_budget_ok": fallback_latency_ms <= configured_budget_ms,
    "metadata_complete_ok": metadata_completeness == 1.0,
}
```

Implementation notes:
- Add case diagnostics for `selected_sql_source`, `final_failure_code`, and `accepted_result_kind`.
- In `scripts/evaluate.py`, let financial evaluation load a fallback-enabled agent configuration instead of always constructing a rule-only `TextToSQLEvidenceTool(dataset.sqlite_db)`.
- Keep the old top-level metrics intact so existing tests and dashboards do not break.

- [ ] **Step 4: Re-run evaluation tests and one end-to-end financial evaluation smoke**

Run:

```bash
pytest tests/unit/test_financial_eval_runner.py tests/unit/test_financial_eval_thresholds.py -q
python scripts/evaluate.py --financial --no-search --test-set tests/fixtures/financial_boundary_eval_cases.json --json
```

Expected: unit tests PASS; CLI prints JSON with `sql_sources`, `promotion_gates`, and unchanged legacy metrics.

- [ ] **Step 5: Commit evaluation and promotion-gate support**

```bash
git add src/observability/evaluation/financial_eval_runner.py scripts/evaluate.py tests/unit/test_financial_eval_runner.py tests/unit/test_financial_eval_thresholds.py tests/fixtures/financial_sql_agent_eval_cases.json
git commit -m "feat: add text2sql source metrics and promotion gates"
```

## Task 5: Update Docs, Validate OpenSpec, and Run Final Focused Checks

**Files:**
- Modify: `docs/financial/local-platform.md`
- Modify: `docs/financial/financial-agentic-rag-design.md`
- Modify: `config/settings.example.yaml`
- Modify: `openspec/changes/text2sql-agent-repair-eval/tasks.md` (check off completed items during implementation)

- [ ] **Step 1: Document the runtime knobs and acceptance rules**

```md
## Text2SQL Agent Route

- Source order: `rule -> lora -> api`
- Repair triggers: `unsafe_sql`, `execution_error`, selected `empty_result`
- Stop rule: first acceptable evidence wins
- Default mode: rule-only unless `financial_platform.text2sql_agent.*` flags are enabled
```

- [ ] **Step 2: Run the focused validation matrix**

Run:

```bash
pytest tests/unit/test_financial_sql_agent_policy.py tests/unit/test_text_to_sql_tool.py tests/unit/test_sql_executor.py tests/unit/test_financial_orchestrator.py tests/unit/test_financial_eval_runner.py tests/unit/test_financial_eval_thresholds.py tests/unit/test_local_platform_config.py -q
pytest tests/integration/test_financial_sql_dataset.py -q
openspec validate text2sql-agent-repair-eval --no-interactive
```

Expected: all tests PASS and OpenSpec validates cleanly.

- [ ] **Step 3: Commit the docs and validation sweep**

```bash
git add docs/financial/local-platform.md docs/financial/financial-agentic-rag-design.md config/settings.example.yaml openspec/changes/text2sql-agent-repair-eval/tasks.md
git commit -m "docs: describe text2sql agent route and rollout rules"
```

## Self-Review

- **Spec coverage:** Tasks 1-2 cover `financial-sql-evidence`; Task 3 covers `financial-hybrid-answering`; Task 4 covers `financial-evaluation`; Task 5 covers documentation and OpenSpec validation.
- **Placeholder scan:** No `TODO` or `TBD` markers remain in this plan; every task names exact files and commands.
- **Type consistency:** `TextToSQLAgentConfig`, `SQLCandidate`, `SQLAttempt`, `accepted_result_kind`, and `final_failure_code` are named consistently across the tasks above.

## Recommended Execution Order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5

The critical sequencing rule is: **do not implement evaluation gates before the SQL route emits stable attempt metadata**.
