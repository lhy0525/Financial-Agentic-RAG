from dataclasses import dataclass, field

import pytest

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


@pytest.mark.parametrize(
    ("text", "metadata", "expected_type", "expected_modalities"),
    [
        (
            "Plain text disclosure.",
            {"source_path": "a.pdf", "page": 1},
            "text",
            ["text"],
        ),
        (
            "[IMAGE: img-1]",
            {
                "source_path": "a.pdf",
                "page_num": 2,
                "image_refs": ["img-1"],
                "images": [{"id": "img-1", "path": "data/images/prospectus_uploads/img-1.png", "page": 2}],
                "image_captions": [{"id": "img-1", "caption": "Revenue chart"}],
            },
            "image",
            ["image"],
        ),
        (
            "募集资金用途 <|TABLE_0001_0000.xlsx|> 详见上表",
            {"source_path": "a.pdf", "page": 3, "element_type": "table"},
            "table",
            ["text", "table"],
        ),
        (
            "See [IMAGE: img-2] and <|TABLE_0002_0000.xlsx|>",
            {
                "source_path": "a.pdf",
                "page": 4,
                "image_refs": ["img-2"],
                "images": [{"id": "img-2", "path": "data/images/prospectus_uploads/img-2.png", "page": 4}],
                "element_type": "table",
            },
            "multimodal",
            ["text", "table", "image"],
        ),
    ],
)
def test_evidence_tool_maps_modalities_without_splitting_hits(
    text,
    metadata,
    expected_type,
    expected_modalities,
):
    search = FakeSearch([Result("chunk-mm", text, 0.8, metadata)])

    package = ProspectusEvidenceTool(search).query("multi-modal question", top_k=1)

    assert len(package.evidences) == 1
    evidence = package.evidences[0]
    assert evidence.evidence_type == expected_type
    assert evidence.metadata["modalities"] == expected_modalities
    assert evidence.metadata["page_num"] == metadata.get("page_num")
    assert evidence.metadata["source_path"] == "a.pdf"
