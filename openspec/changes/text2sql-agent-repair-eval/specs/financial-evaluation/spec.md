## ADDED Requirements

### Requirement: Evaluate Text2SQL candidate source quality
The evaluation system SHALL compare rule, LoRA, API, and repaired SQL candidate performance for financial Text2SQL questions.

#### Scenario: Candidate source metrics are reported
- **WHEN** SQL golden questions are evaluated
- **THEN** the evaluator SHALL report execution success, non-empty result rate, correctness, safety rejection rate, latency, and selected-source distribution for rule, LoRA, API, and repair candidates

#### Scenario: Fallback lift is measured
- **WHEN** fallback sources are enabled for evaluation
- **THEN** the evaluator SHALL report accuracy and execution lift over rule-only Text2SQL by task family

#### Scenario: Candidate source comparison is reproducible
- **WHEN** the same golden evaluation set is run with the same configuration
- **THEN** the evaluator SHALL record enough candidate metadata to reproduce which SQL source was selected for each case

### Requirement: Gate default fallback enablement with evaluation thresholds
The evaluation system SHALL provide explicit promotion gates before LoRA or API fallback is enabled by default outside controlled experiments.

#### Scenario: Rule-only baseline is preserved
- **WHEN** fallback source variants are evaluated
- **THEN** the evaluator SHALL produce a rule-only baseline run using the same golden set so fallback lift and regressions can be measured against a stable comparison point

#### Scenario: Promotion gate checks correctness, safety, latency, and metadata coverage
- **WHEN** a LoRA-enabled or API-enabled configuration is considered for broader enablement
- **THEN** the evaluator SHALL report whether the run satisfies the configured correctness delta threshold, unsafe rejection tolerance, latency budget, and complete-attempt-metadata requirement

#### Scenario: Failed promotion gate blocks default enablement
- **WHEN** fallback evaluation fails any configured promotion gate
- **THEN** the evaluator SHALL mark the fallback configuration as not ready for default enablement and SHALL preserve the failing gate reasons in the report

### Requirement: Evaluate SQL repair and re-execution behavior
The evaluation system SHALL measure whether SQL repair improves failed or empty Text2SQL executions without weakening safety.

#### Scenario: Repair success is measured
- **WHEN** a golden or regression case triggers SQL repair
- **THEN** the evaluator SHALL record whether the repaired SQL passed safety, executed successfully, returned expected rows, and improved final correctness

#### Scenario: Unsafe repair is measured
- **WHEN** a repair candidate produces unsafe SQL
- **THEN** the evaluator SHALL count the safety rejection and confirm the SQL was not executed

#### Scenario: Empty-result repair is measured
- **WHEN** SQL execution returns empty results and empty-result repair is enabled
- **THEN** the evaluator SHALL record whether repair produced correct non-empty evidence or correctly preserved an empty evidence outcome

### Requirement: Track Text2SQL Agent regressions
The evaluation system SHALL include regression cases for rule, LoRA, API, repair, re-execution, and logging failure modes.

#### Scenario: All-candidates-failed regression is tracked
- **WHEN** no SQL candidate can produce safe successful evidence
- **THEN** the evaluator SHALL confirm the system returns a failed evidence package with complete attempt metadata

#### Scenario: Repair-loop limit regression is tracked
- **WHEN** repair repeatedly fails or produces unsafe SQL
- **THEN** the evaluator SHALL confirm retry limits are enforced and reported

#### Scenario: Logging regression is tracked
- **WHEN** a Text2SQL Agent route runs during evaluation
- **THEN** the evaluator SHALL confirm attempt logs and evidence metadata contain source, repair, safety, execution, and selection fields

#### Scenario: Outcome taxonomy regression is tracked
- **WHEN** a regression case exercises compile failure, unsafe SQL, execution failure, accepted empty result, or repair exhaustion
- **THEN** the evaluator SHALL confirm the final report records the expected stable failure or accepted-result classification
