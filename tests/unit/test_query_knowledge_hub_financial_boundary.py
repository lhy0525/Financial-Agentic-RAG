import asyncio
import json
import sys
import types as module_types
from dataclasses import dataclass

import pytest

try:
    from mcp import types
except ModuleNotFoundError:
    mcp_stub = module_types.ModuleType("mcp")
    types = module_types.ModuleType("mcp.types")

    @dataclass
    class TextContent:
        type: str
        text: str

    @dataclass
    class ImageContent:
        type: str
        data: str | None = None
        mimeType: str | None = None

    @dataclass
    class CallToolResult:
        content: list
        isError: bool = False

    types.TextContent = TextContent
    types.ImageContent = ImageContent
    types.CallToolResult = CallToolResult
    mcp_stub.types = types
    sys.modules["mcp"] = mcp_stub
    sys.modules["mcp.types"] = types

from src.core.response.citation_generator import Citation  # noqa: E402
from src.core.response.response_builder import MCPToolResponse  # noqa: E402
from src.mcp_server.tools import query_knowledge_hub as module  # noqa: E402


def _extract_references_json(result: types.CallToolResult) -> dict:
    for block in result.content:
        if isinstance(block, types.TextContent) and "References (JSON)" in block.text:
            json_text = block.text.split("```json", 1)[1].split("```", 1)[0]
            return json.loads(json_text)
    raise AssertionError("missing structured references JSON block")


class FakeKnowledgeHubTool:
    def __init__(self, response: MCPToolResponse):
        self.response = response
        self.calls = []

    async def execute(self, query: str, top_k: int = 5, collection: str | None = None):
        self.calls.append({"query": query, "top_k": top_k, "collection": collection})
        return self.response


def test_query_knowledge_hub_schema_keeps_financial_collection_contract():
    schema = module.TOOL_INPUT_SCHEMA

    assert schema["required"] == ["query"]
    assert set(schema["properties"]).issuperset({"query", "top_k", "collection"})
    assert schema["properties"]["top_k"]["minimum"] == 1
    assert schema["properties"]["top_k"]["maximum"] == 20
    assert "collection" not in schema["required"]


def test_query_knowledge_hub_handler_returns_mcp_content_with_structured_metadata(monkeypatch):
    response = MCPToolResponse(
        content="## retrieval\n\n[1] target disclosure",
        citations=[
            Citation(
                index=1,
                chunk_id="chunk-risk",
                source="target.txt",
                page=11,
                score=0.83,
                text_snippet="target disclosure",
                metadata={"disclosure_family": "risk"},
            )
        ],
        metadata={
            "query": "risk disclosure",
            "collection": "prospectus_txt",
            "result_count": 1,
        },
        is_empty=False,
    )
    fake_tool = FakeKnowledgeHubTool(response)
    monkeypatch.setattr(module, "get_tool_instance", lambda: fake_tool)

    result = asyncio.run(
        module.query_knowledge_hub_handler(
            query="risk disclosure",
            top_k=3,
            collection="prospectus_txt",
        )
    )

    assert isinstance(result, types.CallToolResult)
    assert result.isError is False
    assert fake_tool.calls == [
        {"query": "risk disclosure", "top_k": 3, "collection": "prospectus_txt"}
    ]
    assert isinstance(result.content[0], types.TextContent)
    assert "target disclosure" in result.content[0].text
    structured = _extract_references_json(result)
    assert structured["metadata"]["collection"] == "prospectus_txt"
    assert structured["metadata"]["result_count"] == 1
    assert structured["citations"][0]["source"] == "target.txt"
    assert structured["citations"][0]["metadata"]["disclosure_family"] == "risk"


def test_query_knowledge_hub_handler_empty_response_is_not_error_without_error_metadata(
    monkeypatch,
):
    response = MCPToolResponse(
        content="## no results",
        citations=[],
        metadata={"query": "missing", "collection": "prospectus_txt", "result_count": 0},
        is_empty=True,
    )
    fake_tool = FakeKnowledgeHubTool(response)
    monkeypatch.setattr(module, "get_tool_instance", lambda: fake_tool)

    result = asyncio.run(
        module.query_knowledge_hub_handler(
            query="missing",
            collection="prospectus_txt",
        )
    )

    assert result.isError is False
    structured = _extract_references_json(result)
    assert structured["metadata"]["result_count"] == 0
