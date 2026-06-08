# Financial Agent Domain Rules

This document records the shipped boundary rules for the financial Agentic RAG
work. It is intentionally implementation-facing: when the code and this file
disagree, update the code or update this file before treating a smoke run as
ready.

## Supported Formulas

The formula registry currently exposes deterministic quote formulas:

- `daily_percent_change`: requires close and previous-close quote fields. Output
  is percent. Invalid or zero denominators are handled through safe division
  metadata and should not be reported as a confident numeric answer.
- `daily_return`: requires close and previous-close quote fields. Output is a
  ratio.
- `limit_up_days`: requires close and previous-close quote fields. The default
  threshold is `0.098`; output is a count.
- `price_range` and `intraday_price_range`: require high and low quote fields.
  Output is a currency difference.
- `open_above_previous_close_days` and `open_above_previous_close`: require open
  and previous-close quote fields. Output is a count or boolean-style count.
- `low_volume_days`: requires volume and compares against an annual average.
  Output is a count.
- `annualized_return`: requires first open and final close over the selected
  period. Output is percent.

The SQL evidence compiler also supports task-family calculations that are not
simple registry expressions:

- `fund_share_movement`: computes subscription, redemption, beginning share, and
  ending share movement from the fund scale table.
- `bond_holding_ranking`: ranks bond holdings by report period and holding
  metadata.
- `convertible_bond_industry_aggregation`: joins convertible-bond holdings to
  stock industry classification and aggregates by industry.

All SQL answers use `SQLSafetyChecker` before execution. Unsupported formulas,
ambiguous joins, missing entities, and unsafe SQL return failed or empty
evidence packages instead of fabricating values.

## Table And Column Aliases

`FinancialSchemaRegistry` models the 10 Bosera SQLite tables used by the local
dataset. The implementation keeps the real table and column names in UTF-8
Chinese identifiers. The practical alias groups are:

- Fund master data: fund code, full fund name, short fund name, manager,
  custodian, fund type, inception date, maturity date, management fee, custody
  fee.
- Fund stock holdings: fund code/name, holding date, stock code/name, quantity,
  market value, market-value ratio, holding rank, securities market, country or
  region, report type.
- Fund bond holdings: fund code/name, holding date, bond type/name, quantity,
  market value, market-value ratio, holding rank, market, country or region,
  report type.
- Fund convertible-bond holdings: fund code/name, holding date, underlying stock
  code, bond name, quantity, market value, market-value ratio, holding rank,
  market, country or region, report type.
- Fund daily quotes: fund code, trading date, unit NAV, adjusted unit NAV,
  accumulated unit NAV, asset NAV.
- A-share daily quotes: stock code, trading date, previous close, open, high,
  low, close, volume, turnover.
- Hong Kong daily quotes: stock code, trading date, previous close, open, high,
  low, close, volume, turnover.
- A-share industry classification: stock code, trading date, industry standard,
  level-1 industry, level-2 industry.
- Fund scale changes: fund code/name, announcement date, cutoff date, beginning
  total shares, subscription shares, redemption shares, ending total shares,
  report year, report type.
- Fund holder structure: fund code/name, announcement date, cutoff date,
  institutional shares and ratio, individual shares and ratio, report year,
  report type.

Important column alias groups are stock code, fund code, trading date, report
type, industry standard, quote prices, holding rank, fund scale, bond, and
convertible bond. Industry-standard aliases normalize common Shenwan and CITIC
phrases to the dataset values before SQL is compiled.

## Report Periods

Report-period semantics are deterministic:

- `latest` means the maximum available date for the entity and source table, not
  the maximum global date across unrelated entities.
- Per-fund latest report selection is scoped by fund code and report type when
  those fields are available.
- Annual, semiannual, quarterly, and annual-including-semiannual questions map
  to the report type and report year fields used by holdings, fund scale, and
  holder-structure tables.
- Quote and industry questions use trading-date columns.
- Holding, bond, and convertible-bond questions use holding-date columns.
- Fund scale and holder-structure questions use announcement date and cutoff
  date metadata, with report year/report type used when the question asks for a
  periodic report.

The SQL evidence metadata records time scope, selected tables, selection rules,
unit assumptions, price-field semantics, conversion rules, and join scope where
the compiler can determine them.

## Source Priority

Verifier behavior is deterministic and evidence-first:

- SQL evidence wins for structured database facts such as quotes, holdings,
  fund scale, industry classification, and compiler-supported formulas.
- Prospectus TXT evidence wins for company disclosure facts such as business,
  risk, shareholder, control, patent, supplier, customer, and fundraising
  disclosures when the plan or source preference requests prospectus evidence.
- Explicit source preferences can resolve conflicting facts by selecting the
  preferred evidence source.
- `pass` means required evidence is present and no conflict remains.
- `partial` means some evidence exists but an expected table, raw table payload,
  prospectus evidence, SQL evidence, or dependency is missing.
- `conflict` means evidence values disagree and no source-priority rule safely
  resolves the disagreement.
- `insufficient` means no usable evidence was returned for the planned route.

Prospectus retrieval boundary metrics are evaluation-time metrics. Wrong
company, neighboring-topic, ambiguous-alias, and no-relevant-disclosure reasons
are emitted when expected fixture metadata is supplied.

## Known Unsupported Patterns

The current boundary implementation intentionally does not claim support for:

- Precise values inside prospectus tables when TXT extraction only contains
  `<|TABLE_...|>` placeholders and no raw element payload is available.
- Chart-only numeric answers without explicit text labels.
- Unsupported formulas outside the registry and compiler task families listed
  above.
- Ambiguous or lossy joins across holdings, industry, quote, fund scale, and
  report-period tables.
- Dataset-dependent runs when `bs_challenge_financial_14b_dataset` is missing,
  the SQLite DB is absent, or prospectus TXT files are unavailable.
- A dedicated production `financial_qa` MCP tool. Current MCP compatibility is
  pinned for the existing `query_knowledge_hub` retrieval surface.
