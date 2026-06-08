import pytest

from src.agentic.types import AnswerConstraints, QuestionPlan, TimeScope
from src.financial_dataset.paths import find_financial_dataset
from src.financial_sql.text_to_sql_tool import TextToSQLEvidenceTool


def test_dataset_latest_industry_classification_smoke():
    dataset = find_financial_dataset()
    if not dataset.available:
        pytest.skip(dataset.skip_reason)
    db_path = dataset.sqlite_db
    plan = QuestionPlan(
        route="text_to_sql",
        task_type="latest_record_lookup",
        entities={"stock_codes": ["000637"], "industry_standard": "申万"},
        time_scope=TimeScope(kind="latest", value=None),
        formula=None,
        evidence_need=["sql_result"],
        sub_questions=[],
        answer_constraints=AnswerConstraints(),
        reason="integration smoke",
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "000637 最新申万行业")

    assert package.metadata["status"] == "success"
    assert package.evidences[0].metadata["row_count"] == 1
    assert package.evidences[0].metadata["rows"][0]["二级行业名称"] == "石油化工"
