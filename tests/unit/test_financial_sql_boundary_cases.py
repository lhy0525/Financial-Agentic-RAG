import sqlite3

from src.agentic.types import AnswerConstraints, QuestionPlan, TimeScope
from src.financial_sql.text_to_sql_tool import TextToSQLEvidenceTool


def _plan(task_type, entities, time_scope, formula=None, constraints=None):
    return QuestionPlan(
        route="text_to_sql",
        task_type=task_type,
        entities=entities,
        time_scope=time_scope,
        formula=formula,
        evidence_need=["sql_result"],
        sub_questions=[],
        answer_constraints=constraints or AnswerConstraints(),
        reason="boundary test",
    )


def _seed_boundary_db(path):
    con = sqlite3.connect(path)
    con.execute(
        'CREATE TABLE "基金基本信息" ("基金代码" TEXT, "基金全称" TEXT, "基金简称" TEXT, "管理人" TEXT, "托管人" TEXT, "基金类型" TEXT, "成立日期" TEXT, "到期日期" TEXT, "管理费率" TEXT, "托管费率" TEXT)'
    )
    con.execute(
        'CREATE TABLE "A股票日行情表" ("股票代码" TEXT, "交易日" TEXT, "昨收盘(元)" REAL, "今开盘(元)" REAL, "最高价(元)" REAL, "最低价(元)" REAL, "收盘价(元)" REAL, "成交量(股)" REAL, "成交金额(元)" REAL)'
    )
    con.execute(
        'CREATE TABLE "A股公司行业划分表" ("股票代码" TEXT, "交易日期" TEXT, "行业划分标准" TEXT, "一级行业名称" TEXT, "二级行业名称" TEXT)'
    )
    con.execute(
        'CREATE TABLE "基金股票持仓明细" ("基金代码" TEXT, "基金简称" TEXT, "持仓日期" TEXT, "股票代码" TEXT, "股票名称" TEXT, "数量" REAL, "市值" REAL, "市值占基金资产净值比" REAL, "第N大重仓股" INTEGER, "所在证券市场" TEXT, "所属国家(地区)" TEXT, "报告类型" TEXT)'
    )
    con.execute(
        'CREATE TABLE "基金规模变动表" ("基金代码" TEXT, "基金简称" TEXT, "公告日期" TEXT, "截止日期" TEXT, "报告期期初基金总份额" REAL, "报告期基金总申购份额" REAL, "报告期基金总赎回份额" REAL, "报告期期末基金总份额" REAL, "定期报告所属年度" TEXT, "报告类型" TEXT)'
    )
    con.execute(
        'CREATE TABLE "基金债券持仓明细" ("基金代码" TEXT, "基金简称" TEXT, "持仓日期" TEXT, "债券类型" TEXT, "债券名称" TEXT, "持债数量" REAL, "持债市值" REAL, "持债市值占基金资产净值比" REAL, "第N大重仓股" INTEGER, "所在证券市场" TEXT, "所属国家(地区)" TEXT, "报告类型" TEXT)'
    )
    con.execute(
        'CREATE TABLE "基金可转债持仓明细" ("基金代码" TEXT, "基金简称" TEXT, "持仓日期" TEXT, "对应股票代码" TEXT, "债券名称" TEXT, "数量" REAL, "市值" REAL, "市值占基金资产净值比" REAL, "第N大重仓股" INTEGER, "所在证券市场" TEXT, "所属国家(地区)" TEXT, "报告类型" TEXT)'
    )
    con.execute(
        'INSERT INTO "基金基本信息" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        ("007484", "信澳核心科技混合型证券投资基金A类", "信澳核心科技混合A", "信澳基金", "银行", "混合型", "20200101", "30001231", "1.2%", "0.2%"),
    )
    con.execute(
        'INSERT INTO "基金基本信息" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        ("007485", "信澳核心科技混合型证券投资基金C类", "信澳核心科技混合C", "信澳基金", "银行", "混合型", "20200101", "30001231", "1.2%", "0.2%"),
    )
    con.executemany(
        'INSERT INTO "A股票日行情表" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("000001", "20210105", 10.0, 10.2, 11.0, 9.8, 10.5, 1000, 10500),
            ("000002", "20210105", 20.0, 20.0, 21.0, 19.5, 21.0, 800, 16800),
            ("000003", "20210105", 0.0, 1.0, 1.2, 0.9, 1.1, 500, 550),
            ("000004", "20210105", 1.0, 0.0, 1.2, 0.8, 1.0, 400, 400),
            ("000004", "20210106", 1.0, 1.0, 1.4, 0.9, 1.3, 450, 585),
            ("000001", "20210106", 10.5, 10.0, 12.0, 10.0, 11.6, 500, 5800),
        ],
    )
    con.executemany(
        'INSERT INTO "A股公司行业划分表" VALUES (?, ?, ?, ?, ?)',
        [
            ("000001", "20210105", "申万行业分类", "银行", "股份制银行"),
            ("000002", "20210105", "申万行业分类", "银行", "房地产开发"),
            ("000003", "20210105", "申万行业分类", "银行", "其他金融"),
            ("000001", "20211231", "申万行业分类", "银行", "股份制银行"),
            ("000002", "20211231", "申万行业分类", "银行", "房地产开发"),
        ],
    )
    con.executemany(
        'INSERT INTO "基金股票持仓明细" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("007484", "信澳核心科技混合A", "20210630", "000002", "万科A", 20, 300, 0.3, 1, "深圳证券交易所", "中国", "半年度报告"),
            ("007484", "信澳核心科技混合A", "20211231", "000001", "平安银行", 10, 200, 0.2, 1, "深圳证券交易所", "中国", "年报"),
            ("007484", "信澳核心科技混合A", "20211231", "000002", "万科A", 10, 200, 0.2, 1, "深圳证券交易所", "中国", "年报"),
            ("007485", "信澳核心科技混合C", "20210630", "000003", "测试金融", 3, 30, 0.03, 1, "深圳证券交易所", "中国", "半年度报告"),
        ],
    )
    con.execute(
        'INSERT INTO "基金规模变动表" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        ("007484", "信澳核心科技混合A", "20220330", "20211231", 1000, 300, 100, 1200, "2021", "年报"),
    )
    con.executemany(
        'INSERT INTO "基金债券持仓明细" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("007484", "信澳核心科技混合A", "20211231", "企业债", "21测试债", 50, 500, 0.5, 1, "银行间", "中国", "年报"),
            ("007484", "信澳核心科技混合A", "20211231", "国债", "21国债", 30, 300, 0.3, 2, "银行间", "中国", "年报"),
        ],
    )
    con.executemany(
        'INSERT INTO "基金可转债持仓明细" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ("007484", "信澳核心科技混合A", "20211231", "000001", "银转债", 2, 20, 0.02, 1, "深圳证券交易所", "中国", "年报"),
            ("007484", "信澳核心科技混合A", "20211231", "000002", "万转债", 3, 30, 0.03, 2, "深圳证券交易所", "中国", "年报"),
        ],
    )
    con.commit()
    con.close()


def test_per_fund_latest_report_selects_latest_holding_date(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_boundary_db(db_path)
    plan = _plan(
        "report_period_query",
        {"fund_codes": ["007484"], "top_n": 2},
        TimeScope(kind="per_entity_latest_report", value="2021", start="20210101", end="20211231", report_types=["定期报告"], per_entity_latest=True),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "latest fund report")

    assert package.metadata["status"] == "success"
    assert {row["持仓日期"] for row in package.evidences[0].metadata["rows"]} == {"20211231"}
    assert package.evidences[0].metadata["selection_rules"]["per_entity_latest"] is True


def test_per_fund_latest_report_selects_latest_holding_date_for_each_fund(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_boundary_db(db_path)
    plan = _plan(
        "report_period_query",
        {"fund_codes": ["007484", "007485"], "top_n": 10},
        TimeScope(kind="per_entity_latest_report", value="2021", start="20210101", end="20211231", report_types=["定期报告"], per_entity_latest=True),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "latest fund reports")

    rows = package.evidences[0].metadata["rows"]
    latest_by_fund = {row["基金代码"]: row["持仓日期"] for row in rows}
    assert latest_by_fund == {"007484": "20211231", "007485": "20210630"}
    assert package.evidences[0].metadata["selection_rules"]["per_entity_latest"] is True


def test_report_period_year_value_uses_end_date_not_year_literal(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_boundary_db(db_path)
    plan = _plan(
        "report_period_query",
        {"fund_codes": ["007484"], "top_n": 2},
        TimeScope(kind="report_period", value="2021", start="20210101", end="20211231", report_types=["年度含半年度"]),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "annual report holdings")

    assert package.metadata["status"] == "success"
    assert {row["持仓日期"] for row in package.evidences[0].metadata["rows"]} == {"20211231"}
    assert package.evidences[0].metadata["selection_rules"]["report_type_filter"] == ["年报", "半年度报告"]


def test_fund_share_movement_reports_purchase_redemption_and_net_change(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_boundary_db(db_path)
    plan = _plan(
        "fund_share_movement",
        {"fund_codes": ["007484"]},
        TimeScope(kind="report_period", value="2021", start="20210101", end="20211231", report_types=["年报"]),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "share movement")

    row = package.evidences[0].metadata["rows"][0]
    assert row["报告期基金总申购份额"] == 300
    assert row["报告期基金总赎回份额"] == 100
    assert row["net_share_change"] == 200
    assert package.evidences[0].metadata["unit_assumptions"]["share_fields"] == "份"


def test_bond_holding_ranking_uses_stable_tie_breakers(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_boundary_db(db_path)
    plan = _plan(
        "bond_holding_ranking",
        {"fund_codes": ["007484"], "top_n": 2},
        TimeScope(kind="report_period", value="2021", start="20210101", end="20211231", report_types=["年报"]),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "bond ranking")

    rows = package.evidences[0].metadata["rows"]
    assert [row["债券名称"] for row in rows] == ["21测试债", "21国债"]
    assert package.evidences[0].metadata["selection_rules"]["tie_breakers"] == ["第N大重仓股", "债券名称"]


def test_convertible_bond_industry_aggregation_groups_by_industry(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_boundary_db(db_path)
    plan = _plan(
        "convertible_bond_industry_aggregation",
        {"fund_codes": ["007484"], "industry_standard": "申万"},
        TimeScope(kind="report_period", value="2021", start="20210101", end="20211231", report_types=["年报"]),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "convertible industry")

    rows = package.evidences[0].metadata["rows"]
    assert rows == [{"一级行业名称": "银行", "convertible_bond_market_value": 50.0, "holding_count": 2}]
    assert package.evidences[0].metadata["join_scope"]["join"] == "convertible_industry"


def test_industry_formula_ties_order_by_stock_code_and_safe_division(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_boundary_db(db_path)
    plan = _plan(
        "quote_formula",
        {"industry_standard": "申万", "level1_industry": "银行", "top_n": 3},
        TimeScope(kind="trading_date", value="20210105"),
        formula="daily_percent_change",
        constraints=AnswerConstraints(output_type="percentage", order="desc", top_n=3),
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "industry ranking")

    rows = package.evidences[0].metadata["rows"]
    assert [row["股票代码"] for row in rows] == ["000001", "000002", "000003"]
    assert rows[2]["daily_percent_change"] is None
    assert package.evidences[0].metadata["selection_rules"]["tie_breakers"] == ["daily_percent_change DESC", "股票代码 ASC"]
    assert package.evidences[0].metadata["formula"]["metadata"]["safe_division"] == "NULLIF denominator"


def test_stock_formula_and_annualized_return_use_safe_division(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_boundary_db(db_path)
    daily = _plan(
        "quote_formula",
        {"stock_codes": ["000003"]},
        TimeScope(kind="trading_date", value="20210105"),
        formula="daily_percent_change",
    )
    annualized = _plan(
        "quote_formula",
        {"stock_codes": ["000004"]},
        TimeScope(kind="annual_range", value="2021", start="20210105", end="20210106"),
        formula="annualized_return",
    )

    daily_package = TextToSQLEvidenceTool(db_path).query(daily, "safe daily")
    annualized_package = TextToSQLEvidenceTool(db_path).query(annualized, "safe annualized")

    assert daily_package.metadata["status"] == "success"
    assert daily_package.evidences[0].metadata["rows"][0]["daily_percent_change"] is None
    assert "NULLIF" in daily_package.metadata["sql"]
    assert daily_package.evidences[0].metadata["formula"]["metadata"]["safe_division"] == "NULLIF denominator"
    assert annualized_package.metadata["status"] == "success"
    assert annualized_package.evidences[0].metadata["rows"][0]["annualized_return"] is None
    assert "NULLIF" in annualized_package.metadata["sql"]


def test_convertible_bond_industry_join_rejects_ambiguous_and_lossy_matches(tmp_path):
    db_path = tmp_path / "finance.db"
    _seed_boundary_db(db_path)
    con = sqlite3.connect(db_path)
    con.execute(
        'INSERT INTO "A股公司行业划分表" VALUES (?, ?, ?, ?, ?)',
        ("000001", "20211231", "申万行业分类", "非银金融", "证券"),
    )
    con.commit()
    con.close()
    plan = _plan(
        "convertible_bond_industry_aggregation",
        {"fund_codes": ["007484"], "industry_standard": "申万"},
        TimeScope(kind="report_period", value="2021", start="20210101", end="20211231", report_types=["年报"]),
    )

    ambiguous = TextToSQLEvidenceTool(db_path).query(plan, "ambiguous convertible join")

    assert ambiguous.metadata["status"] == "failed"
    assert ambiguous.metadata["error_type"] == "join_scope"
    assert "ambiguous" in ambiguous.metadata["error"]

    db_path = tmp_path / "lossy.db"
    _seed_boundary_db(db_path)
    con = sqlite3.connect(db_path)
    con.execute(
        'DELETE FROM "A股公司行业划分表" WHERE "股票代码" = ? AND "交易日期" = ?',
        ("000002", "20211231"),
    )
    con.commit()
    con.close()

    lossy = TextToSQLEvidenceTool(db_path).query(plan, "lossy convertible join")

    assert lossy.metadata["status"] == "failed"
    assert lossy.metadata["error_type"] == "join_scope"
    assert "lossy" in lossy.metadata["error"]
