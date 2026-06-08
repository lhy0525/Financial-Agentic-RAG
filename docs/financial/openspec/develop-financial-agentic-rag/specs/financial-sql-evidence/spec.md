## ADDED Requirements

### Requirement: Register financial database schema
The system SHALL provide a schema registry for the 10-table SQLite financial database with table names, column names, semantic aliases, date fields, and common joins.

#### Scenario: Schema registry exposes table metadata
- **WHEN** the SQL evidence path receives a question plan
- **THEN** it SHALL be able to retrieve relevant table and column metadata for schema linking

#### Scenario: Chinese aliases are resolved
- **WHEN** a question refers to holdings, daily quotes, industry classification, fund scale, or holder structure using natural Chinese phrasing
- **THEN** the schema registry SHALL map the phrase to the corresponding SQLite table and columns

### Requirement: Generate safe SQL
The SQL evidence path SHALL generate or compile SQL that is safe to execute against the local SQLite database.

#### Scenario: Read-only SQL passes safety
- **WHEN** generated SQL contains exactly one `SELECT` statement and no write or DDL operation
- **THEN** the safety checker SHALL allow execution

#### Scenario: Unsafe SQL is rejected
- **WHEN** generated SQL contains `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, multiple statements, or statement separators
- **THEN** the safety checker SHALL reject execution and return a failed SQL evidence package without running it

#### Scenario: Row limits are enforced
- **WHEN** generated SQL is not an aggregate-only query and has no explicit safe limit
- **THEN** the SQL evidence path SHALL apply a configurable row limit before returning results

### Requirement: Execute SQL and package evidence
The SQL evidence path SHALL execute safe SQL and return a structured evidence package rather than a final answer.

#### Scenario: Successful SQL execution returns evidence
- **WHEN** SQL execution succeeds
- **THEN** the system SHALL return an evidence package containing result rows, column names, generated SQL, database path, table names, row count, formula metadata, and elapsed time

#### Scenario: Empty SQL result is explicit
- **WHEN** SQL execution succeeds but returns no rows
- **THEN** the system SHALL return an empty SQL evidence package and SHALL NOT fabricate results

#### Scenario: SQL failure is repairable
- **WHEN** SQL execution fails because of a generation or schema-linking error
- **THEN** the system SHALL attempt repair no more than two times before returning a failed evidence package with the error message

### Requirement: Support finance formula execution
The SQL evidence path SHALL support common finance formulas through registry-backed SQL expressions or post-query computations.

#### Scenario: Daily return formula is executed
- **WHEN** the question plan asks for daily return using close and previous close
- **THEN** the SQL evidence path SHALL compute the formula from the applicable quote table fields and include the formula identifier in evidence metadata

#### Scenario: Ranking formula is executed
- **WHEN** the question plan asks for the maximum, top-N, or count above threshold
- **THEN** the SQL evidence path SHALL produce SQL or post-processing that returns the requested ranking or aggregate result

#### Scenario: Report-period holdings are queried
- **WHEN** the question plan asks for fund holdings in a specific annual, semiannual, quarterly, or date-based report period
- **THEN** the SQL evidence path SHALL filter by holding date and report type consistently with the normalized time scope

### Requirement: Support dataset calculation patterns
The SQL evidence path SHALL support recurring calculation patterns from the Bosera question set through compiled SQL or deterministic post-processing.

#### Scenario: Intraday price range is computed
- **WHEN** the plan asks for the stock with the largest difference between highest price and lowest price on a date
- **THEN** the SQL evidence path SHALL compute the range from quote table fields and return the requested ranked stock evidence

#### Scenario: Open-above-previous-close days are counted
- **WHEN** the plan asks how many days a stock opened above the previous close during a year
- **THEN** the SQL evidence path SHALL count trading records where the open price is greater than the previous close

#### Scenario: Low-volume days are counted against annual average
- **WHEN** the plan asks how many trading days have volume below the stock's annual average volume
- **THEN** the SQL evidence path SHALL compute the annual average in the stock scope and count records below that average

#### Scenario: Annualized return is computed
- **WHEN** the plan asks for annualized return using first available opening price and final available closing price in a year
- **THEN** the SQL evidence path SHALL select the applicable first and last trading records and compute the requested percent return

#### Scenario: Fund share movement is computed
- **WHEN** the plan asks whether report-period beginning shares are lower or higher than ending shares
- **THEN** the SQL evidence path SHALL compare the corresponding fund scale fields for each fund in scope

#### Scenario: Bond and convertible-bond holdings are aggregated
- **WHEN** the plan asks for maximum bond type, convertible-bond industry, or bond holding rank
- **THEN** the SQL evidence path SHALL query the appropriate bond or convertible-bond holding table and join to industry data when stock-code industry classification is required

### Requirement: Resolve entity aliases for SQL execution
The SQL evidence path SHALL resolve fund and stock aliases before executing queries that require database identifiers.

#### Scenario: Fund name is resolved
- **WHEN** the question plan contains a fund name without a fund code
- **THEN** the SQL evidence path SHALL resolve it through the fund basic information table or return an ambiguous-entity evidence failure if multiple incompatible matches remain

#### Scenario: Stock name is resolved
- **WHEN** the question plan contains a stock name without a stock code
- **THEN** the SQL evidence path SHALL resolve it through available holding, quote, or industry records before executing code-based queries

### Requirement: Apply latest-record and report-period selection
The SQL evidence path SHALL implement deterministic latest-record and report-period filtering rules from the question plan.

#### Scenario: Latest industry classification is selected
- **WHEN** the question asks for the latest industry classification of a stock
- **THEN** the SQL evidence path SHALL select the record with the maximum trading date for that stock and industry standard

#### Scenario: Per-fund latest report is selected
- **WHEN** the question asks to use each fund's latest regular report within a year
- **THEN** the SQL evidence path SHALL select the maximum applicable report cutoff date per fund before applying aggregation or comparison logic

#### Scenario: Annual report including semiannual report is filtered
- **WHEN** the question plan specifies annual report including semiannual report
- **THEN** the SQL evidence path SHALL include only the report types represented by that normalized report-type constraint

### Requirement: Log SQL query attempts
The system SHALL log SQL query attempts for traceability and evaluation.

#### Scenario: SQL query log is written
- **WHEN** the SQL evidence path attempts SQL execution
- **THEN** the system SHALL log the user question, generated SQL, status, error if any, row count, elapsed time, and created timestamp
