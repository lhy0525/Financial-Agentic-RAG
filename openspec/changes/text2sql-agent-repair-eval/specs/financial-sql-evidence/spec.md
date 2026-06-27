## ADDED Requirements

### Requirement: Generate SQL candidates from rule, LoRA, and API sources
The SQL evidence path SHALL support a candidate-based Text2SQL Agent that can produce SQL candidates from deterministic rule compilation, optional SQL-LoRA generation, and optional API-backed generation.

#### Scenario: Rule candidate is attempted first
- **WHEN** the SQL evidence path receives a text-to-SQL question plan
- **THEN** it SHALL attempt deterministic rule compilation before LoRA or API-backed SQL generation

#### Scenario: LoRA fallback is attempted after rule failure
- **WHEN** rule compilation fails, rule SQL execution fails, or rule SQL returns an empty result that requires fallback
- **THEN** the SQL evidence path SHALL attempt SQL-LoRA generation when LoRA fallback is enabled

#### Scenario: API fallback is attempted after LoRA failure
- **WHEN** rule and LoRA candidates cannot produce acceptable SQL evidence and API fallback is enabled
- **THEN** the SQL evidence path SHALL attempt API-backed SQL generation as the final SQL candidate source

#### Scenario: Candidate source is recorded
- **WHEN** a SQL candidate is generated
- **THEN** the system SHALL record the candidate source as `rule`, `lora`, `api`, `repair`, or a source-specific repair variant in SQL evidence metadata

### Requirement: Apply deterministic fallback eligibility and candidate selection
The SQL evidence path SHALL apply explicit eligibility and stopping rules before moving from rule compilation to LoRA, API, or repair attempts.

#### Scenario: Fallback eligibility is classified from the prior outcome
- **WHEN** a candidate family finishes with compile failure, safety rejection, execution failure, or an empty result
- **THEN** the SQL evidence path SHALL classify that outcome as terminal, repairable, or eligible for fallback according to configuration plus question-plan or task-family policy

#### Scenario: Candidate families follow fixed source order
- **WHEN** multiple SQL sources are enabled
- **THEN** the SQL evidence path SHALL evaluate candidate families in the fixed order `rule`, then `lora`, then `api`, and SHALL NOT skip to a later source while an earlier source still has an eligible repair attempt remaining

#### Scenario: First acceptable evidence wins
- **WHEN** a candidate or repaired candidate produces acceptable evidence
- **THEN** the SQL evidence path SHALL select that evidence immediately, record the selected reason, and SHALL NOT replace it with a later source family

#### Scenario: Accepted empty results are explicit
- **WHEN** a safe SQL execution returns no rows and policy marks the empty result as terminal
- **THEN** the SQL evidence path SHALL return an explicit empty evidence package with `accepted_result_kind=empty` and SHALL NOT continue fallback

### Requirement: Repair SQL candidates after safety or execution failures
The SQL evidence path SHALL provide bounded SQL repair for generated candidates that fail safety validation, fail execution, or produce empty results where repair is permitted.

#### Scenario: Execution error triggers repair
- **WHEN** a safe SQL candidate fails during SQLite execution
- **THEN** the SQL evidence path SHALL provide the question, plan, prior SQL, execution error, schema hints, and available examples to the repair step

#### Scenario: Repaired SQL is safety checked before execution
- **WHEN** SQL repair produces a new SQL candidate
- **THEN** the repaired SQL SHALL pass the same SQL safety checker before it is executed

#### Scenario: Repair attempts are bounded
- **WHEN** SQL repair fails to produce successful evidence
- **THEN** the SQL evidence path SHALL stop after the configured maximum repair attempts and return a failed evidence package with all repair errors recorded

#### Scenario: Empty result repair is explicit
- **WHEN** SQL execution succeeds but returns no rows and empty-result repair is enabled for the task family
- **THEN** the repair step SHALL receive the empty-result status and SHALL preserve the original question plan constraints in any repaired candidate

#### Scenario: Safety rejection can enter bounded repair
- **WHEN** a generated candidate is rejected by the SQL safety checker and repair is enabled for that source family
- **THEN** the repair step SHALL receive the rejected SQL plus the safety rejection reason before the route advances to the next candidate family

### Requirement: Re-execute repaired SQL and select evidence deterministically
The SQL evidence path SHALL re-run safety and execution for repaired candidates and select the first acceptable evidence according to deterministic selection rules.

#### Scenario: Repaired SQL succeeds
- **WHEN** repaired SQL passes safety and execution returns rows
- **THEN** the SQL evidence path SHALL return a successful evidence package with the repaired SQL, selected source, row count, and selected reason

#### Scenario: Unsafe repaired SQL is rejected
- **WHEN** repaired SQL contains unsafe operations, multiple statements, comments, or other safety violations
- **THEN** the SQL evidence path SHALL reject it without execution and continue to the next allowed candidate or return failure

#### Scenario: All candidates fail
- **WHEN** rule, LoRA, API, and repair attempts all fail or are disabled
- **THEN** the SQL evidence path SHALL return a failed evidence package that includes each attempted candidate status, a stable `final_failure_code`, and SHALL NOT fabricate results

### Requirement: Classify Text2SQL Agent outcomes with stable failure codes
The SQL evidence path SHALL emit stable outcome and failure classifications for candidate attempts and final evidence packages.

#### Scenario: Attempt failure codes are normalized
- **WHEN** a candidate attempt fails before selection
- **THEN** the system SHALL classify the outcome using stable codes including `compile_failed`, `unsafe_sql`, `execution_error`, `empty_result`, `repair_exhausted`, `source_disabled`, or `source_unavailable`

#### Scenario: Final route outcome is recorded
- **WHEN** the SQL evidence path returns success, explicit empty evidence, or failure
- **THEN** the evidence metadata SHALL include `accepted_result_kind`, `final_failure_code` when applicable, and the reason the route stopped

### Requirement: Log Text2SQL Agent attempts
The system SHALL log Text2SQL Agent attempts across generation, repair, safety checking, execution, and candidate selection.

#### Scenario: Attempt log captures candidate lifecycle
- **WHEN** a SQL candidate is generated, repaired, safety checked, executed, or selected
- **THEN** the system SHALL log source, SQL text or hash, safety status, execution status, error, row count, elapsed time, repair reason, and created timestamp

#### Scenario: Evidence metadata includes fallback attempts
- **WHEN** the SQL evidence path returns success, empty, or failure
- **THEN** the evidence metadata SHALL include structured `fallback_attempts` and `repair_attempts` sufficient to reconstruct the Text2SQL Agent route
