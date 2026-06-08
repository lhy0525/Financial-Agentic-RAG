## ADDED Requirements

### Requirement: Evaluate financial question planning
The evaluation system SHALL measure question planning quality for finance QA.

#### Scenario: Router accuracy is measured
- **WHEN** a golden question has an expected route and hybrid mode
- **THEN** the evaluator SHALL compare the generated plan against expected route and hybrid mode

#### Scenario: Entity extraction is measured
- **WHEN** a golden question defines expected stock, fund, company, date, report period, or industry entities
- **THEN** the evaluator SHALL measure whether the generated plan extracts those entities correctly

### Requirement: Evaluate SQL evidence
The evaluation system SHALL measure SQL evidence execution and correctness.

#### Scenario: SQL execution success is measured
- **WHEN** a golden SQL question is evaluated
- **THEN** the evaluator SHALL record whether generated SQL passed safety checks and executed successfully

#### Scenario: SQL result correctness is measured
- **WHEN** a golden SQL question has expected result values
- **THEN** the evaluator SHALL compare normalized SQL evidence results against expected values with configured tolerance

### Requirement: Evaluate prospectus evidence
The evaluation system SHALL measure prospectus retrieval quality.

#### Scenario: Source hit is measured
- **WHEN** a golden prospectus question defines expected source files or pages
- **THEN** the evaluator SHALL measure whether retrieval hit the expected source metadata

#### Scenario: Evidence type hit is measured
- **WHEN** a golden prospectus question expects text, table, image, or chart evidence
- **THEN** the evaluator SHALL measure whether retrieved evidence includes the expected evidence type

### Requirement: Evaluate hybrid and verifier behavior
The evaluation system SHALL measure hybrid workflow and verification quality.

#### Scenario: Hybrid sequence is measured
- **WHEN** a golden hybrid question defines expected `sql_first` or `doc_first` sequence
- **THEN** the evaluator SHALL compare executed tool sequence against the expected sequence

#### Scenario: Verification status is measured
- **WHEN** a golden case expects pass, partial, conflict, or insufficient verification status
- **THEN** the evaluator SHALL compare verifier output against the expected status

### Requirement: Track failure regressions
The evaluation system SHALL include regression cases for known financial QA failure modes.

#### Scenario: SQL failure regression is tracked
- **WHEN** a regression case contains invalid SQL generation, schema-linking ambiguity, or empty results
- **THEN** the evaluator SHALL confirm the system returns a safe failed or empty evidence package without fabricated answers

#### Scenario: Prospectus evidence regression is tracked
- **WHEN** a regression case contains missing raw table evidence or low-confidence chart evidence
- **THEN** the evaluator SHALL confirm the system reports limitations and avoids unsupported precise numeric claims

### Requirement: Evaluate dataset task families
The evaluation system SHALL group golden questions by recurring Bosera dataset task families and report metrics per family.

#### Scenario: SQL task families are reported
- **WHEN** SQL golden questions are evaluated
- **THEN** the evaluator SHALL report metrics for point lookup, latest-record lookup, industry aggregation, quote formula, holding rank, fund scale, holder structure, bond holding, and convertible-bond industry tasks

#### Scenario: Prospectus task families are reported
- **WHEN** prospectus golden questions are evaluated
- **THEN** the evaluator SHALL report metrics for business description, shareholder/control facts, financial table facts, patent/qualification facts, supplier/customer facts, and fundraising-project facts

#### Scenario: Answer formatting is evaluated
- **WHEN** golden answers specify rounding, percentage, monetary unit, identifier, ordering, or top-N constraints
- **THEN** the evaluator SHALL verify that the final answer formatting satisfies those constraints
