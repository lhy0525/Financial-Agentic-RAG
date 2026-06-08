# Financial Dataset Setup

This runbook describes the local dataset expectations and smoke checks for the
financial Agentic RAG boundary work.

## SQLite Database Path

The local challenge dataset is expected at:

```text
../bs_challenge_financial_14b_dataset
```

relative to `MODULAR-RAG-MCP-SERVER`, or at a parent/sibling path discoverable by
`src.financial_dataset.paths.find_financial_dataset()`.

The SQLite DB is discovered from:

```text
../bs_challenge_financial_14b_dataset/dataset/*.db
```

You can also pass a DB explicitly to the SQL smoke CLI:

```powershell
python scripts/financial_query.py "000637 latest industry" --db "../bs_challenge_financial_14b_dataset/dataset/<db-file>.db" --json
```

If the dataset is unavailable, dataset-aware tests should skip with an explicit
reason rather than failing with an opaque file-not-found error.

## Prospectus TXT Ingestion Smoke

Use `ProspectusTxtLoader` to verify TXT files can be read from:

```text
../bs_challenge_financial_14b_dataset/pdf_txt_file
```

The loader preserves table placeholders such as `<|TABLE_0001_0000.xlsx|>` in
the document text and records them in document metadata. A focused local smoke is:

```powershell
pytest tests/unit/test_prospectus_txt_loader.py tests/unit/test_prospectus_evidence_tool.py -v --basetemp .pytest-tmp-prospectus
```

For retrieval fixtures, `ProspectusEvidenceTool` expects the existing search
surface to keep the call shape:

```text
search(query=..., top_k=..., filters=..., trace=None, return_details=False)
```

Boundary tests verify source, page, section, disclosure-family, top-k hit, table
placeholder, score metadata, empty-result, and negative-retrieval behavior.

## SQL Evidence Smoke

Run the SQL boundary suite first:

```powershell
pytest tests/unit/test_schema_registry.py tests/unit/test_text_to_sql_tool.py tests/unit/test_financial_sql_boundary_cases.py -v --basetemp .pytest-tmp-sql
```

When the real dataset is available, run the integration smoke:

```powershell
pytest tests/integration/test_financial_sql_dataset.py -v --basetemp .pytest-tmp-sql-integration
```

For a manual query smoke, pass the discovered DB to:

```powershell
python scripts/financial_query.py "000637 latest industry" --db "../bs_challenge_financial_14b_dataset/dataset/<db-file>.db" --json
```

A healthy SQL evidence response includes a `question_plan`, one or more SQL
evidence sources, safety metadata, executed SQL, row count, rows, and a
verification report. Empty or unsupported boundaries should return structured
failure or empty metadata, not unsafe SQL.

## Evaluation Smoke

Run the focused financial evaluation tests:

```powershell
pytest tests/unit/test_financial_eval_runner.py tests/unit/test_financial_eval_thresholds.py -v --basetemp .pytest-tmp-financial-eval
```

Run the CLI fixture smoke without requiring the real dataset:

```powershell
python scripts/evaluate.py --financial --test-set tests/fixtures/financial_boundary_eval_cases.json --json --no-search
```

The JSON output is printed to stdout. Stable top-level fields include `passed`,
`thresholds`, `failed_thresholds`, `case_results`, `families`, `regressions`,
`skipped_cases`, and `run_metadata`.

## Common Failures

- Missing dataset directory: place `bs_challenge_financial_14b_dataset` beside or
  above the repo, or pass explicit fixture paths where supported.
- Missing SQLite DB: verify `dataset/*.db` exists and the process has read
  permission.
- Wrong collection: for MCP retrieval, pass the collection containing indexed
  prospectus TXT chunks; otherwise `query_knowledge_hub` may return empty
  results.
- Missing TXT files: verify `pdf_txt_file` exists and contains text files with
  preserved placeholders.
- Missing embedding or LLM credentials: use `--no-search` evaluation smoke for
  fixture-only checks, or configure the provider before live retrieval.
- Global temp permission errors on Windows: add `--basetemp .pytest-tmp-<name>`
  to pytest commands so temporary files are created inside the repository.
- Unsupported formulas or ambiguous joins: inspect SQL evidence metadata for
  `error_type`, `join_scope`, `selection_rules`, and safety metadata, then add a
  fixture only if the behavior is intentionally supported.
