import sqlite3
from dataclasses import dataclass, field

from src.agentic.types import AnswerConstraints, QuestionPlan, TimeScope
from src.financial_sql.text_to_sql_tool import TextToSQLEvidenceTool


@dataclass
class SimplePlan:
    task_type: str
    entities: dict
    time_scope: dict = field(default_factory=dict)
    formula: str | None = None


def _seed_financial_db(path):
    con = sqlite3.connect(path)
    con.execute(
        'CREATE TABLE "基金基本信息" ("基金代码" TEXT, "基金全称" TEXT, "基金简称" TEXT, "管理人" TEXT, "托管人" TEXT, "基金类型" TEXT, "成立日期" TEXT, "到期日期" TEXT, "管理费率" TEXT, "托管费率" TEXT)'
    )
    con.execute(
        'CREATE TABLE "A股公司行业划分表" ("股票代码" TEXT, "交易日期" TEXT, "行业划分标准" TEXT, "一级行业名称" TEXT, "二级行业名称" TEXT)'
    )
    con.execute(
        'CREATE TABLE "A股票日行情表" ("股票代码" TEXT, "交易日" TEXT, "昨收盘(元)" REAL, "今开盘(元)" REAL, "最高价(元)" REAL, "最低价(元)" REAL, "收盘价(元)" REAL, "成交量(股)" REAL, "成交金额(元)" REAL)'
    )
    con.execute(
        'CREATE TABLE "基金股票持仓明细" ("基金代码" TEXT, "基金简称" TEXT, "持仓日期" TEXT, "股票代码" TEXT, "股票名称" TEXT, "数量" REAL, "市值" REAL, "市值占基金资产净值比" REAL, "第N大重仓股" INTEGER, "所在证券市场" TEXT, "所属国家(地区)" TEXT, "报告类型" TEXT)'
    )
    con.executemany(
        'INSERT INTO "A股公司行业划分表" VALUES (?, ?, ?, ?, ?)',
        [
            ("000637", "20211230", "申万行业分类", "化工", "石油化工"),
            ("000637", "20211231", "申万行业分类", "化工", "石油化工"),
            ("000637", "20211231", "中信行业分类", "石油石化", "石油化工"),
        ],
    )
    con.execute(
        'INSERT INTO "A股票日行情表" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        ("000001", "20210105", 10.0, 10.2, 11.0, 9.8, 10.5, 1000, 10500),
    )
    con.executemany(
        'INSERT INTO "A股票日行情表" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("000001", "20210106", 10.5, 10.0, 12.0, 10.0, 11.6, 500, 5800),
            ("000001", "20210107", 11.6, 12.0, 12.2, 11.5, 11.7, 1500, 17550),
            ("000637", "20211231", 10.0, 10.1, 10.8, 9.9, 10.5, 100, 1050),
        ],
    )
    con.executemany(
        'INSERT INTO "基金基本信息" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("007484", "信澳核心科技混合型证券投资基金A类", "信澳核心科技混合A", "信澳基金", "银行", "混合型", "20200101", "30001231", "1.2%", "0.2%"),
            ("007485", "信澳核心科技混合型证券投资基金C类", "信澳核心科技混合C", "信澳基金", "银行", "混合型", "20200101", "30001231", "1.2%", "0.2%"),
        ],
    )
    con.executemany(
        'INSERT INTO "基金股票持仓明细" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("007484", "信澳核心科技混合A", "20201231", "600563", "法拉电子", 10, 200, 0.1, 1, "上海证券交易所", "中华人民共和国", "季报"),
            ("007484", "信澳核心科技混合A", "20201231", "000001", "平安银行", 5, 100, 0.05, 2, "深圳证券交易所", "中华人民共和国", "季报"),
        ],
    )
    con.commit()
    con.close()


def _question_plan(
    task_type,
    entities,
    time_scope,
    formula=None,
    constraints=None,
    formula_params=None,
):
    return QuestionPlan(
        route="text_to_sql",
        task_type=task_type,
        entities=entities,
        time_scope=time_scope,
        formula=formula,
        evidence_need=["sql_result"],
        sub_questions=[],
        answer_constraints=constraints or AnswerConstraints(),
        reason="unit test",
        formula_params=formula_params or {},
    )


def test_latest_industry_classification_package_contains_sql_metadata(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = SimplePlan(
        task_type="latest_industry_classification",
        entities={"stock_codes": ["000637"], "industry_standard": "申万"},
        time_scope={"kind": "latest"},
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "latest industry?")

    assert package.path == "text_to_sql"
    assert len(package.evidences) == 1
    evidence = package.evidences[0]
    assert evidence.evidence_type == "sql_result"
    assert evidence.metadata["row_count"] == 1
    assert evidence.metadata["tables"] == ["A股公司行业划分表"]
    assert evidence.metadata["columns"] == ["股票代码", "交易日期", "行业划分标准", "一级行业名称", "二级行业名称"]
    assert evidence.metadata["safety"]["allowed"] is True
    assert evidence.metadata["entity_resolution"][0]["code"] == "000637"
    assert "石油化工" in evidence.content


def test_real_question_plan_latest_record_lookup_maps_to_latest_industry(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = _question_plan(
        task_type="latest_record_lookup",
        entities={"stock_codes": ["000637"], "industry_standard": "申万"},
        time_scope=TimeScope(kind="latest", value=None),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "000637 latest industry")

    assert package.metadata["status"] == "success"
    assert package.evidences[0].metadata["rows"][0]["交易日期"] == "20211231"
    assert package.evidences[0].metadata["rows"][0]["二级行业名称"] == "石油化工"


def test_daily_percent_change_uses_formula_metadata(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = SimplePlan(
        task_type="daily_percent_change",
        entities={"stock_codes": ["000001"]},
        time_scope={"kind": "trading_date", "value": "20210105"},
        formula="daily_percent_change",
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "daily change?")

    assert package.evidences[0].metadata["formula"]["identifier"] == "daily_percent_change"
    assert package.evidences[0].metadata["row_count"] == 1
    assert package.evidences[0].metadata["columns"][-1] == "daily_percent_change"
    assert package.evidences[0].metadata["rows"][0]["daily_percent_change"] == 5.0


def test_real_question_plan_quote_formula_uses_stock_name_resolution(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = _question_plan(
        task_type="quote_formula",
        entities={"stock_names": ["平安银行"], "stock_names_require_lookup": True},
        time_scope=TimeScope(kind="trading_date", value="20210105"),
        formula="daily_percent_change",
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "平安银行 daily change")

    assert package.metadata["status"] == "success"
    assert package.evidences[0].metadata["entity_resolution"][0]["status"] == "matched"
    assert package.evidences[0].metadata["entity_resolution"][0]["code"] == "000001"
    assert package.evidences[0].metadata["rows"][0]["daily_percent_change"] == 5.0


def test_real_question_plan_quote_formula_industry_ranking_compiles(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = _question_plan(
        task_type="quote_formula",
        entities={
            "industry_standard": "鐢充竾",
            "level1_industry": "鍖栧伐",
        },
        time_scope=TimeScope(kind="trading_date", value="20211231"),
        formula="daily_percent_change",
        constraints=AnswerConstraints(output_type="percentage", precision=2, top_n=1, order="desc"),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "industry max change")

    assert package.metadata["status"] == "success"
    assert package.evidences[0].metadata["tables"] == [
        "A股票日行情表",
        "A股公司行业划分表",
    ]
    assert package.evidences[0].metadata["rows"][0]["股票代码"] == "000637"
    assert package.evidences[0].metadata["rows"][0]["daily_percent_change"] == 5.0


def test_real_question_plan_point_lookup_stock_close_price_compiles(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = _question_plan(
        task_type="point_lookup",
        entities={"stock_codes": ["000001"], "columns": ["鏀剁洏浠?鍏?"]},
        time_scope=TimeScope(kind="trading_date", value="20210105"),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "stock close")

    assert package.metadata["status"] == "success"
    assert package.evidences[0].metadata["rows"][0]["收盘价(元)"] == 10.5


def test_stock_code_lookup_resolves_company_full_name_from_holding_alias(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    con = sqlite3.connect(db_path)
    con.execute(
        'INSERT INTO "基金股票持仓明细" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            "007484",
            "淇℃境鏍稿績绉戞妧娣峰悎A",
            "20211231",
            "300184",
            "力源信息",
            10,
            200,
            0.1,
            1,
            "深圳证券交易所",
            "中华人民共和国",
            "年报",
        ),
    )
    con.commit()
    con.close()
    plan = _question_plan(
        task_type="stock_code_lookup",
        entities={"stock_names": ["武汉力源信息技术股份有限公司"], "stock_names_require_lookup": True},
        time_scope=TimeScope(kind="not_applicable", value=None),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "武汉力源信息技术股份有限公司的股市代码是什么？")

    assert package.metadata["status"] == "success"
    assert package.evidences[0].metadata["result_value"] == "300184"
    row = package.evidences[0].metadata["rows"][0]
    assert row["股票代码"] == "300184"
    assert row["股票名称"] == "力源信息"


def test_name_resolution_failure_returns_explicit_failed_package(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = _question_plan(
        task_type="quote_formula",
        entities={"stock_names": ["不存在股票"], "stock_names_require_lookup": True},
        time_scope=TimeScope(kind="trading_date", value="20210105"),
        formula="daily_percent_change",
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "missing stock")

    assert package.metadata["status"] == "failed"
    assert package.metadata["error_type"] == "entity_resolution"
    assert package.metadata["entity_resolution"][0]["status"] == "no_match"
    assert package.metadata["repair_attempts"] <= 2


def test_fund_name_ambiguity_returns_explicit_failed_package(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = _question_plan(
        task_type="report_period_query",
        entities={"fund_names": ["信澳核心科技混合"], "fund_names_require_lookup": True, "top_n": 1},
        time_scope=TimeScope(kind="report_period", value="20201231", report_types=["季报"]),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "ambiguous fund")

    assert package.metadata["status"] == "failed"
    assert package.metadata["error_type"] == "entity_resolution"
    assert package.metadata["entity_resolution"][0]["status"] == "ambiguous"


def test_unsupported_formula_failure_includes_bounded_repair_metadata(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = _question_plan(
        task_type="quote_formula",
        entities={"stock_codes": ["000001"]},
        time_scope=TimeScope(kind="trading_date", value="20210105"),
        formula="not_registered",
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "unsupported formula")

    assert package.metadata["status"] == "failed"
    assert package.metadata["error_type"] == "compile"
    assert package.metadata["repair_attempts"] == 2
    assert len(package.metadata["repair_errors"]) == 2


def test_quote_formula_price_range_compiles(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = _question_plan(
        task_type="quote_formula",
        entities={"stock_codes": ["000001"]},
        time_scope=TimeScope(kind="trading_date", value="20210105"),
        formula="price_range",
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "price range")

    assert package.metadata["status"] == "success"
    assert package.evidences[0].metadata["formula"]["identifier"] == "price_range"
    assert package.evidences[0].metadata["rows"][0]["price_range"] == 1.2


def test_quote_formula_count_patterns_compile_for_annual_range(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)

    cases = [
        ("open_above_previous_close_days", 2),
        ("low_volume_days", 1),
        ("limit_up_days", 1),
    ]

    for formula, expected in cases:
        plan = _question_plan(
            task_type="quote_formula",
            entities={"stock_codes": ["000001"]},
            time_scope=TimeScope(kind="annual_range", value="2021", start="20210101", end="20211231"),
            formula=formula,
        )

        package = TextToSQLEvidenceTool(db_path).query(plan, formula)

        assert package.metadata["status"] == "success"
        assert package.evidences[0].metadata["formula"]["identifier"] == formula
        assert package.evidences[0].metadata["rows"][0][formula] == expected


def test_quote_formula_annualized_return_compiles_for_annual_range(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = _question_plan(
        task_type="quote_formula",
        entities={"stock_codes": ["000001"]},
        time_scope=TimeScope(kind="annual_range", value="2021", start="20210101", end="20211231"),
        formula="annualized_return",
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "annualized")

    assert package.metadata["status"] == "success"
    assert round(package.evidences[0].metadata["rows"][0]["annualized_return"], 6) == 14.705882


def test_report_period_holding_ranking_query(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = SimplePlan(
        task_type="report_period_holding_ranking",
        entities={"fund_codes": ["007484"], "top_n": 1},
        time_scope={"kind": "report_period", "value": "20201231", "report_types": ["季报"]},
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "top holding?")

    assert package.evidences[0].metadata["row_count"] == 1
    assert package.evidences[0].metadata["rows"][0]["股票名称"] == "法拉电子"


def test_planner_task_type_aliases_for_holding_ranking(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)

    for task_type in ["ranking", "aggregate_statistics", "report_period_query"]:
        plan = _question_plan(
            task_type=task_type,
            entities={"fund_codes": ["007484"], "top_n": 1},
            time_scope=TimeScope(kind="report_period", value="20201231", report_types=["季报"]),
        )

        package = TextToSQLEvidenceTool(db_path).query(plan, task_type)

        assert package.metadata["status"] == "success"
        assert package.evidences[0].metadata["rows"][0]["股票名称"] == "法拉电子"


def test_unsafe_sql_returns_failed_package_without_execution(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_financial_db(db_path)
    plan = SimplePlan(task_type="raw_sql", entities={"sql": "DROP TABLE 基金股票持仓明细"})

    package = TextToSQLEvidenceTool(db_path).query(plan, "bad sql")

    assert package.metadata["status"] == "failed"
    assert package.evidences == []
    assert "rejected" in package.metadata["error"]
