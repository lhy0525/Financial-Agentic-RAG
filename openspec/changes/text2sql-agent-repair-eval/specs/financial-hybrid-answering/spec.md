## ADDED Requirements

### Requirement: Trace Text2SQL Agent stages in financial answers
The financial agent SHALL preserve Text2SQL Agent route details in trace metadata when SQL evidence is collected for SQL-only or hybrid questions.

#### Scenario: SQL-only trace includes candidate route
- **WHEN** a SQL-only question uses rule, LoRA, API, or repair stages
- **THEN** the final response trace SHALL include SQL candidate generation, repair, safety, execution, re-execution, and selection stages

#### Scenario: Hybrid trace includes SQL fallback context
- **WHEN** a hybrid question invokes the SQL evidence path and SQL fallback or repair occurs
- **THEN** the hybrid trace SHALL preserve the selected SQL source and fallback attempts before merge and verification

#### Scenario: Selected SQL source remains explainable
- **WHEN** final answer generation uses SQL evidence produced by fallback or repair
- **THEN** the selected evidence metadata SHALL identify the selected SQL source, selected reason, repair attempts, and any failed prior candidates

#### Scenario: Hybrid route preserves SQL failure classification
- **WHEN** the SQL sub-path ends in explicit empty evidence or failure before hybrid merge
- **THEN** the hybrid trace SHALL preserve the SQL `accepted_result_kind` or `final_failure_code` so verification can distinguish empty evidence from failed SQL execution
