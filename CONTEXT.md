# Modular RAG Financial QA

This context defines the language for a financial question-answering system that combines document retrieval and structured database querying through an agent orchestrator.

## Language

**Agent Router**:
The question-understanding component in the agent layer that decides which evidence path should answer a user question. It selects among document retrieval, SQL querying, or a hybrid combination.
_Avoid_: MCP router, RAG router

**Routing Decision**:
A structured decision produced by the Agent Router. It records the selected route, hybrid mode when applicable, extracted entities, evidence needs, sub-questions, and the reason for routing.
_Avoid_: route label, routing note

**PDF RAG Path**:
The evidence path for prospectus and document understanding. It primarily handles PDF files and may use parsed TXT or Markdown as intermediate representations of those PDFs.
_Avoid_: pure text path, PDF-only path

**Document Evidence Type**:
A category of evidence produced inside the PDF RAG Path, such as text, table, image, or chart. Document evidence types are not top-level routing paths.
_Avoid_: document route, sub-router path

**Table Evidence**:
A document evidence type for tables extracted from PDF pages. It uses a compact table summary for retrieval and preserves the raw table for answer generation.
_Avoid_: table chunk only

**Text-to-SQL Path**:
The evidence path for structured financial database queries. It generates, validates, executes SQL over the curated database, and returns tabular evidence.
_Avoid_: DB RAG, SQL RAG

**SQL Evidence Package**:
An evidence package returned by the Text-to-SQL Path. It includes executed SQL, table names, columns, rows, and database provenance.
_Avoid_: SQL answer, generated SQL only

**Hybrid Path**:
The agent orchestration strategy that combines document evidence and database evidence for one answer. It is not a separate retriever.
_Avoid_: mixed retriever

**doc_first Hybrid**:
A hybrid strategy that starts from document evidence to identify entities, disclosures, or business context, then queries the database for structured facts.
_Avoid_: document-led query

**sql_first Hybrid**:
A hybrid strategy that starts from database results to identify entities, rankings, dates, or anomalies, then retrieves document evidence for explanation or context.
_Avoid_: database-led query

**Evidence Package**:
A structured result returned by an evidence path before final answer generation. It contains source facts, metadata, and provenance rather than a final natural-language answer.
_Avoid_: path answer, partial answer

**Evidence Merger**:
The final synthesis component that combines evidence packages from one or more paths into a user-facing answer with sources.
_Avoid_: RAG answerer, SQL answerer

**Verifier**:
The final checking component that compares evidence packages before answer generation. When sources conflict, it follows source-specific user intent first, task type second, and preserves unresolved conflicts with provenance.
_Avoid_: hallucination checker, answer judge
