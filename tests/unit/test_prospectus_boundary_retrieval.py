from dataclasses import dataclass, field

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


def test_retrieval_records_source_page_section_and_disclosure_family_hits():
    search = FakeSearch(
        [
            Result(
                "chunk-business",
                "公司主营业务为药品研发、生产和销售，主要产品覆盖心血管领域。",
                0.92,
                {
                    "source_path": "深圳信立泰药业股份有限公司.txt",
                    "company_name": "深圳信立泰药业股份有限公司",
                    "page": 42,
                    "section": "主营业务",
                    "disclosure_family": "business",
                    "element_type": "text",
                },
            )
        ]
    )

    package = ProspectusEvidenceTool(search).query(
        "深圳信立泰药业股份有限公司主营业务是什么？",
        top_k=3,
        expected={
            "company_name": "深圳信立泰药业股份有限公司",
            "disclosure_family": "business",
            "source_path": "深圳信立泰药业股份有限公司.txt",
            "page": 42,
            "section": "主营业务",
        },
    )

    assert search.calls[0]["top_k"] == 3
    assert package.metadata["status"] == "success"
    assert package.metadata["top_k"] == 3
    assert package.metadata["top_k_hit"] is True
    assert package.metadata["hit_rank"] == 1
    assert package.metadata["source_hit"] is True
    assert package.metadata["page_hit"] is True
    assert package.metadata["section_hit"] is True
    assert package.metadata["disclosure_family_hit"] is True
    assert package.evidences[0].metadata["disclosure_family"] == "business"
    assert package.evidences[0].metadata["section"] == "主营业务"


def test_negative_retrieval_flags_wrong_company_and_neighboring_topic():
    search = FakeSearch(
        [
            Result(
                "chunk-risk",
                "发行人面临原材料价格波动风险。",
                0.88,
                {
                    "source_path": "其他公司.txt",
                    "company_name": "其他公司",
                    "page": 10,
                    "section": "风险因素",
                    "disclosure_family": "risk",
                },
            )
        ]
    )

    package = ProspectusEvidenceTool(search).query(
        "深圳信立泰药业股份有限公司主营业务是什么？",
        expected={
            "company_name": "深圳信立泰药业股份有限公司",
            "disclosure_family": "business",
            "source_path": "深圳信立泰药业股份有限公司.txt",
        },
    )

    assert package.metadata["status"] == "mismatch"
    assert package.metadata["source_hit"] is False
    assert package.metadata["disclosure_family_hit"] is False
    assert "wrong_company" in package.metadata["negative_reasons"]
    assert "neighboring_topic" in package.metadata["negative_reasons"]


def test_positive_boundary_disclosure_families_are_reported_as_hits():
    families = [
        "risk",
        "shareholder",
        "control",
        "patent",
        "supplier",
        "customer",
        "fundraising",
    ]
    search = FakeSearch(
        [
            Result(
                f"chunk-{family}",
                f"{family} disclosure",
                0.8,
                {
                    "source_path": f"{family}.txt",
                    "company_name": "target company",
                    "page": index,
                    "section": family,
                    "disclosure_family": family,
                },
            )
            for index, family in enumerate(families, start=1)
        ]
    )

    for family in families:
        package = ProspectusEvidenceTool(search).query(
            f"{family} question",
            expected={
                "company_name": "target company",
                "source_path": f"{family}.txt",
                "section": family,
                "disclosure_family": family,
            },
        )

        assert package.metadata["status"] == "success"
        assert package.metadata["source_hit"] is True
        assert package.metadata["section_hit"] is True
        assert package.metadata["disclosure_family_hit"] is True
        assert package.metadata["negative_reasons"] == []


def test_expected_match_can_appear_below_first_rank_with_top_k_boundary():
    search = FakeSearch(
        [
            Result(
                "chunk-neighbor",
                "neighboring disclosure",
                0.99,
                {
                    "source_path": "neighbor.txt",
                    "company_name": "target company",
                    "page": 4,
                    "section": "business",
                    "disclosure_family": "business",
                },
            ),
            Result(
                "chunk-risk",
                "risk disclosure",
                0.72,
                {
                    "source_path": "target.txt",
                    "company_name": "target company",
                    "page": 9,
                    "section": "risk",
                    "disclosure_family": "risk",
                },
            ),
        ]
    )

    package = ProspectusEvidenceTool(search).query(
        "risk question",
        top_k=2,
        expected={
            "source_path": "target.txt",
            "page": 9,
            "section": "risk",
            "disclosure_family": "risk",
        },
    )

    assert search.calls[-1]["top_k"] == 2
    assert package.metadata["status"] == "success"
    assert package.metadata["top_k_hit"] is True
    assert package.metadata["hit_rank"] == 2
    assert package.metadata["source_hit"] is True
    assert package.metadata["page_hit"] is True
    assert package.metadata["section_hit"] is True
    assert package.metadata["disclosure_family_hit"] is True


def test_ambiguous_alias_and_empty_disclosure_are_explicit_negative_reasons():
    ambiguous = ProspectusEvidenceTool(
        FakeSearch(
            [
                Result(
                    "chunk-ambiguous",
                    "ambiguous alias disclosure",
                    0.66,
                    {
                        "source_path": "alias.txt",
                        "company_name": "target company",
                        "disclosure_family": "risk",
                        "ambiguous_alias": True,
                    },
                )
            ]
        )
    ).query(
        "alias question",
        expected={
            "company_name": "target company",
            "disclosure_family": "risk",
            "ambiguous_alias": False,
        },
    )
    empty = ProspectusEvidenceTool(FakeSearch([])).query(
        "missing disclosure",
        expected={"company_name": "target company", "disclosure_family": "fundraising"},
    )

    assert ambiguous.metadata["status"] == "mismatch"
    assert "ambiguous_alias" in ambiguous.metadata["negative_reasons"]
    assert empty.metadata["status"] == "empty"
    assert "no_relevant_disclosure" in empty.metadata["negative_reasons"]


def test_query_knowledge_hub_compatibility_surface_is_stable():
    result = Result(
        "chunk-shareholder",
        "控股股东为测试集团。",
        0.77,
        {
            "source_path": "company.txt",
            "page": 8,
            "section": "股东情况",
            "score_fields": {"bm25": 0.3, "dense": 0.47},
        },
    )
    search = FakeSearch([result])

    package = ProspectusEvidenceTool(search).query_knowledge_hub(
        {"query": "控股股东是谁？", "top_k": 1, "filters": {"doc_type": "prospectus_txt"}}
    )

    assert search.calls[0]["query"] == "控股股东是谁？"
    assert search.calls[0]["top_k"] == 1
    assert search.calls[0]["filters"] == {"doc_type": "prospectus_txt"}
    assert package.metadata["status"] == "success"
    assert package.metadata["response_fields"] == [
        "path",
        "question",
        "evidences",
        "metadata",
    ]
    assert package.evidences[0].metadata["score_fields"] == {"bm25": 0.3, "dense": 0.47}
