# Table Evidence Uses Summary Retrieval and Raw Generation

PDF tables are often too long and structurally dense to embed as whole raw tables. We decided that Table Evidence uses compact summaries for retrieval and preserves the raw table in a docstore for answer generation, so retrieval remains semantically robust while final answers can still use the complete table content.

**Considered Options**

- Store full raw tables directly in vector chunks.
- Store only table summaries and discard raw tables.
- Store table summaries for retrieval and raw Markdown or JSON tables for generation.

**Consequences**

Table retrieval depends on concise semantic summaries, while precise answers can recover the original table by `element_id`. This adds a docstore lookup step, but avoids losing table structure or overloading the vector index with large raw tables.
