## ADDED Requirements

### Requirement: Ingest parsed prospectus text baseline
The system SHALL support ingesting provided parsed prospectus TXT files as a baseline source for prospectus evidence retrieval.

#### Scenario: TXT prospectus is loaded
- **WHEN** a parsed prospectus TXT file is ingested
- **THEN** the system SHALL create retrievable chunks with source path, document identifier, document type, and collection metadata

#### Scenario: Table placeholders are preserved
- **WHEN** parsed TXT content contains table placeholders such as `<|TABLE_0001_0000.xlsx|>`
- **THEN** the system SHALL preserve the placeholder text and surrounding context in retrievable content

### Requirement: Handle parsed table placeholder limitations
The prospectus evidence path SHALL distinguish between retrievable table placeholders and actually recovered raw table payloads.

#### Scenario: Table placeholder lacks raw payload
- **WHEN** retrieved TXT evidence contains a table placeholder but no corresponding raw table payload is available
- **THEN** the evidence package SHALL mark the evidence as `raw_table_unavailable` and include the surrounding text context

#### Scenario: Precise table value requires raw evidence
- **WHEN** the user asks for precise prospectus table values such as annual expense, inventory, turnover ratio, gross margin, or percentage by year
- **THEN** the system SHALL prefer raw table evidence when available and SHALL mark the answer as partial or insufficient when only a placeholder is available

#### Scenario: Placeholder is not treated as parsed table
- **WHEN** a table placeholder is retrieved without recovered rows or columns
- **THEN** the system SHALL NOT claim that the table contents have been parsed

### Requirement: Retrieve prospectus evidence
The prospectus evidence path SHALL retrieve evidence from prospectus content and return a structured evidence package.

#### Scenario: Disclosure fact is retrieved
- **WHEN** the evidence path receives a question about company business, risk factors, controlling shareholders, legal representatives, patents, suppliers, customers, or fundraising projects
- **THEN** it SHALL retrieve relevant prospectus chunks and return PDF/TXT evidence with source metadata

#### Scenario: Evidence package is returned
- **WHEN** prospectus retrieval completes
- **THEN** the system SHALL return an evidence package containing evidence IDs, evidence type, source type, content, source path, score, and available page or location metadata

#### Scenario: No evidence is explicit
- **WHEN** prospectus retrieval finds no relevant content
- **THEN** the system SHALL return an empty evidence package and SHALL NOT fabricate prospectus evidence

### Requirement: Support element-aware prospectus extension
The prospectus path SHALL provide extension points for native PDF elements including text, table, image, and chart evidence.

#### Scenario: Element metadata is available
- **WHEN** native PDF element extraction is enabled
- **THEN** indexed chunks SHALL include scalar metadata such as document ID, source path, element ID, element type, page, and raw-payload availability

#### Scenario: Raw table evidence can be recovered
- **WHEN** a retrieved evidence item references a table element with raw payload availability
- **THEN** the system SHALL be able to fetch raw table markdown or JSON by element ID from the element docstore

#### Scenario: Chart numeric confidence is constrained
- **WHEN** a chart or image evidence item lacks explicit OCR/VLM numeric labels
- **THEN** the system SHALL mark it as explanatory evidence only and SHALL NOT use it as a precise numeric source

### Requirement: Preserve existing RAG server compatibility
The prospectus evidence path SHALL reuse existing RAG pipeline components where practical and SHALL NOT break existing MCP retrieval tools.

#### Scenario: Existing query tool still works
- **WHEN** prospectus evidence support is added
- **THEN** existing `query_knowledge_hub` behavior and input schema SHALL remain compatible
