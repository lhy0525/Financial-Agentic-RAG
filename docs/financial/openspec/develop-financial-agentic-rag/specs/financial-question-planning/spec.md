## ADDED Requirements

### Requirement: Plan financial questions
The system SHALL convert each user question into a structured financial question plan before executing any evidence path.

#### Scenario: DB calculation question is planned
- **WHEN** the user asks for the stock with maximum percentage change on a given trading date within an industry classification
- **THEN** the plan route SHALL be `text_to_sql`, include the trading date, industry standard, industry name, formula identifier, ranking intent, and requested rounding precision

#### Scenario: Prospectus disclosure question is planned
- **WHEN** the user asks what business a prospectus company primarily conducts
- **THEN** the plan route SHALL be `pdf_rag`, include the company name, prospectus evidence need, and disclosure task type

#### Scenario: Hybrid question is planned
- **WHEN** the user asks for a fund holding from the database and then asks for the held company's prospectus disclosure
- **THEN** the plan route SHALL be `hybrid`, the hybrid mode SHALL be `sql_first`, and the plan SHALL include SQL and prospectus sub-questions

### Requirement: Extract finance entities and time scopes
The planner SHALL extract finance entities and time scopes into normalized fields for downstream tools.

#### Scenario: Fund report period is normalized
- **WHEN** the question mentions `2021 Q2`, `2021年半年度报告`, or `20210630`
- **THEN** the plan SHALL represent the applicable date or report period in a normalized time scope that downstream SQL and retrieval paths can consume

#### Scenario: Industry classification standard is normalized
- **WHEN** the question mentions CITIC or Shenwan industry classification in Chinese
- **THEN** the plan SHALL include the corresponding industry standard value used by the SQLite industry table

#### Scenario: Stock and fund identifiers are preserved
- **WHEN** the question contains a stock code, fund code, fund short name, fund full name, stock name, or company full name
- **THEN** the plan SHALL preserve the raw mention and provide normalized entity fields where available

### Requirement: Resolve dataset-specific time scopes
The planner SHALL normalize dataset-specific date, year, quarter, report-period, and latest-record expressions into explicit time-scope instructions.

#### Scenario: Latest data request is planned
- **WHEN** the question asks for the latest industry classification, latest quote, or latest available record
- **THEN** the plan SHALL mark the time scope as `latest` and identify the date column that downstream SQL must maximize within the relevant entity scope

#### Scenario: Annual range is planned
- **WHEN** the question asks for a calendar year such as `2021年度` or `2020年`
- **THEN** the plan SHALL represent the inclusive start and end dates for that year and preserve whether the question requires trading days, report dates, or report periods

#### Scenario: Report type is planned
- **WHEN** the question mentions annual report, semiannual report, quarterly report, `年报(含半年报)`, or `季报`
- **THEN** the plan SHALL include normalized report-type constraints compatible with the SQLite report-type values

#### Scenario: Most recent report in year is planned
- **WHEN** the question asks to use each fund's latest regular report within a year
- **THEN** the plan SHALL include a per-entity latest-report selection instruction instead of a single global date

### Requirement: Resolve financial entity aliases
The planner SHALL identify when downstream execution requires alias resolution between natural-language names and database or prospectus identifiers.

#### Scenario: Fund name requires fund code lookup
- **WHEN** the question refers to a fund by short name, full name, or partial name
- **THEN** the plan SHALL mark the fund entity as requiring lookup against fund basic information before SQL execution

#### Scenario: Stock name requires stock code lookup
- **WHEN** the question refers to a stock by name rather than code
- **THEN** the plan SHALL mark the stock entity as requiring lookup against holding, quote, or industry data before SQL execution

#### Scenario: SQL result requires prospectus entity mapping
- **WHEN** a hybrid plan needs to query prospectus content using a stock returned from SQL evidence
- **THEN** the plan SHALL include an entity-mapping step from stock code or stock name to prospectus company name

### Requirement: Identify formulas and answer constraints
The planner SHALL identify known finance formulas and requested output constraints.

#### Scenario: Limit-up formula is identified
- **WHEN** the question defines limit-up as close divided by previous close minus one greater than or equal to 9.8 percent
- **THEN** the plan SHALL include a `limit_up_days` formula identifier and the threshold value

#### Scenario: Rounding constraint is identified
- **WHEN** the question requests a percentage with two decimals or a value rounded to an integer
- **THEN** the plan SHALL include the requested output type and precision in answer constraints

#### Scenario: Unknown formula is explicit
- **WHEN** the question requires a calculation that is not in the formula registry
- **THEN** the plan SHALL mark the formula as unknown and include the raw formula text for SQL generation or clarification
