from dataclasses import dataclass, field

from src.prospectus_evidence.element_docstore import ElementDocstore, RawElementPayload
from src.prospectus_evidence.evidence_tool import ProspectusEvidenceTool


@dataclass
class Result:
    chunk_id: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


class FakeSearch:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


def test_evidence_tool_marks_placeholder_raw_table_unavailable():
    search = FakeSearch(
        [
            Result(
                "chunk-1",
                "募集资金用途 <|TABLE_0001_0000.xlsx|> 详见上表",
                0.91,
                {"source_path": "a.txt", "page": 12, "element_id": "el-1", "element_type": "table"},
            )
        ]
    )

    package = ProspectusEvidenceTool(search).query("募集资金用途", top_k=3)

    assert search.calls[0]["top_k"] == 3
    evidence = package.evidences[0]
    assert evidence.evidence_type == "table"
    assert evidence.page == 12
    assert evidence.metadata["element_id"] == "el-1"
    assert evidence.metadata["element_type"] == "table"
    assert evidence.metadata["table_placeholders"] == ["TABLE_0001_0000.xlsx"]
    assert evidence.metadata["raw_table_unavailable"] is True
    assert evidence.metadata["raw_payload_available"] is False


def test_evidence_tool_returns_empty_package_when_no_results():
    package = ProspectusEvidenceTool(FakeSearch([])).query("无结果")

    assert package.path == "pdf_rag"
    assert package.evidences == []
    assert package.metadata["status"] == "empty"


def test_element_docstore_stub_returns_none_and_subclasses_can_fetch_payload():
    assert ElementDocstore().get("missing") is None

    class InMemoryDocstore(ElementDocstore):
        def get(self, element_id):
            return RawElementPayload(element_id, "|a|b|", "markdown", {"page": 1})

    payload = InMemoryDocstore().get("table-1")

    assert payload.raw_format == "markdown"
    assert payload.metadata["page"] == 1


def test_evidence_tool_preserves_uploaded_index_metadata():
    search = FakeSearch(
        [
            Result(
                "chunk-uploaded",
                "The uploaded prospectus describes liquidity risk.",
                0.89,
                {
                    "source_path": "uploads/prospectus.pdf",
                    "collection": "prospectus_uploads",
                    "local_origin": "ui_upload",
                    "document_id": "doc_uploaded",
                },
            )
        ]
    )

    package = ProspectusEvidenceTool(search).query("liquidity risk", top_k=1)

    evidence = package.evidences[0]
    assert evidence.source == "uploads/prospectus.pdf"
    assert evidence.metadata["chunk_id"] == "chunk-uploaded"
    assert evidence.metadata["collection"] == "prospectus_uploads"
    assert evidence.metadata["local_origin"] == "ui_upload"
    assert evidence.metadata["document_id"] == "doc_uploaded"
