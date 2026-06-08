## ADDED Requirements

### Requirement: Orchestrate single-path questions
The financial agent SHALL execute the planned single evidence path for non-hybrid questions.

#### Scenario: SQL-only question is answered
- **WHEN** the question plan route is `text_to_sql`
- **THEN** the agent SHALL execute the SQL evidence path, verify the evidence, and generate a sourced final answer from SQL evidence

#### Scenario: Prospectus-only question is answered
- **WHEN** the question plan route is `pdf_rag`
- **THEN** the agent SHALL execute the prospectus evidence path, verify the evidence, and generate a sourced final answer from prospectus evidence

### Requirement: Orchestrate hybrid questions
The financial agent SHALL support both `sql_first` and `doc_first` hybrid workflows.

#### Scenario: SQL-first hybrid is executed
- **WHEN** the question plan hybrid mode is `sql_first`
- **THEN** the agent SHALL execute the SQL sub-question first, normalize resulting entities, execute the prospectus sub-question, and merge both evidence packages

#### Scenario: Doc-first hybrid is executed
- **WHEN** the question plan hybrid mode is `doc_first`
- **THEN** the agent SHALL execute the prospectus sub-question first, normalize resulting entities or disclosure terms, execute the SQL sub-question, and merge both evidence packages

#### Scenario: Hybrid dependency failure is explicit
- **WHEN** the first hybrid path cannot produce the entity or fact required by the second path
- **THEN** the agent SHALL return a partial or insufficient verification status rather than inventing the missing dependency

### Requirement: Merge evidence packages
The financial agent SHALL merge evidence from SQL and prospectus paths into a unified evidence set before answer generation.

#### Scenario: Evidence IDs remain traceable
- **WHEN** evidence packages are merged
- **THEN** all selected evidence IDs, source types, source paths, SQL metadata, and prospectus metadata SHALL remain traceable in the final response metadata

#### Scenario: Duplicate evidence is deduplicated
- **WHEN** multiple evidence items represent the same source fact
- **THEN** the merger SHALL deduplicate or group them while preserving the strongest source references

### Requirement: Verify source priority and sufficiency
The verifier SHALL decide whether evidence is sufficient and which sources have priority.

#### Scenario: User specifies prospectus source
- **WHEN** the user explicitly asks according to the prospectus or PDF disclosure
- **THEN** prospectus evidence SHALL have priority over database evidence for conflicting disclosure facts

#### Scenario: User specifies database source
- **WHEN** the user explicitly asks according to the database, daily quote table, holding table, or industry table
- **THEN** SQL evidence SHALL have priority over prospectus evidence for conflicting structured facts

#### Scenario: Evidence is insufficient
- **WHEN** required SQL or prospectus evidence is missing
- **THEN** the verifier SHALL mark the answer as `insufficient` or `partial` and identify the missing evidence type

### Requirement: Verify numeric consistency
The verifier SHALL check formulas, units, dates, report periods, and rounding constraints before final answer generation.

#### Scenario: Formula result is verified
- **WHEN** SQL evidence includes a known formula identifier and result value
- **THEN** the verifier SHALL confirm the formula inputs and output are consistent with the plan before answer generation

#### Scenario: Rounding is applied consistently
- **WHEN** the plan requests a percentage or decimal precision
- **THEN** the final answer SHALL apply the requested precision and preserve the unit

#### Scenario: Source conflict is reported
- **WHEN** SQL and prospectus evidence conflict and cannot be reconciled by unit conversion or source priority
- **THEN** the final answer SHALL report the conflict with both sources instead of forcing a single value

### Requirement: Normalize final answer formatting
The financial agent SHALL format final answers according to the question plan's answer constraints and financial identifier conventions.

#### Scenario: Percentage formatting is normalized
- **WHEN** the plan requests a percentage answer with a specified precision
- **THEN** the final answer SHALL use that precision and include a percent sign unless the question explicitly requests a decimal

#### Scenario: Monetary unit is preserved
- **WHEN** selected evidence contains an amount with a unit such as yuan, ten-thousand yuan, hundred-million yuan, shares, or percent
- **THEN** the final answer SHALL preserve or explicitly convert the unit and state the converted unit

#### Scenario: Stock and fund codes preserve leading zeroes
- **WHEN** the answer contains stock or fund codes
- **THEN** the final answer SHALL preserve leading zeroes and SHALL NOT coerce identifiers into numeric values

#### Scenario: Multi-value answer order is explicit
- **WHEN** the question asks for values across years, quarters, ranks, or top-N results
- **THEN** the final answer SHALL preserve the requested chronological, report-period, or ranking order

### Requirement: Return structured final answer
The financial agent SHALL return final answers with structured traceability data.

#### Scenario: Final answer includes sources
- **WHEN** final answer generation succeeds
- **THEN** the response SHALL include answer text, selected sources, routing decision or question plan, and verification report

#### Scenario: Trace metadata is recorded
- **WHEN** a financial agent query runs
- **THEN** the system SHALL record trace stages for planning, SQL evidence, prospectus evidence, merge, verification, and answer generation
