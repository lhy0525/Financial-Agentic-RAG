# Router Lives in the Agent Layer

The financial QA system combines PDF evidence retrieval, structured database querying, and hybrid reasoning. We decided that the Agent Router lives in the agent orchestration layer rather than inside the existing MCP RAG server, because routing is an orchestration concern across multiple tools while the MCP server should remain a reusable document retrieval capability.

**Considered Options**

- Put routing inside a new MCP tool such as `financial_qa`.
- Keep routing in the agent layer and call the existing RAG MCP plus a separate Text-to-SQL tool.

**Consequences**

The RAG MCP can stay focused on document evidence retrieval, Text-to-SQL can evolve independently, and Hybrid Path behavior can be changed without rewriting the MCP server protocol.
