from src.agentic.planner import FinancialQuestionPlanner


def test_plans_industry_quote_formula_ranking_question():
    planner = FinancialQuestionPlanner()

    plan = planner.plan(
        "请帮我计算，在20210105，中信行业分类划分的一级行业为综合金融行业中，"
        "涨跌幅最大股票的股票代码是？涨跌幅是多少？百分数保留两位小数。"
    )

    assert plan.route == "text_to_sql"
    assert plan.task_type == "quote_formula"
    assert plan.time_scope.kind == "trading_date"
    assert plan.time_scope.value == "20210105"
    assert plan.entities["dates"] == ["20210105"]
    assert plan.entities["industry_standard"] == "中信行业分类"
    assert plan.entities["level1_industry"] == "综合金融"
    assert plan.formula == "daily_percent_change"
    assert plan.answer_constraints.output_type == "percentage"
    assert plan.answer_constraints.precision == 2
    assert plan.answer_constraints.order == "desc"
    assert plan.answer_constraints.top_n == 1


def test_plans_latest_industry_point_lookup_question():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("我想知道股票000637在申万行业分类下的二级行业是什么？用最新的数据。")

    assert plan.route == "text_to_sql"
    assert plan.task_type == "latest_record_lookup"
    assert plan.entities["stock_codes"] == ["000637"]
    assert plan.entities["industry_standard"] == "申万行业分类"
    assert plan.time_scope.kind == "latest"
    assert plan.time_scope.date_column == "交易日期"


def test_plans_prospectus_disclosure_question():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("深圳信立泰药业股份有限公司主营业务是什么？")

    assert plan.route == "pdf_rag"
    assert plan.task_type == "disclosure_fact"
    assert plan.entities["company_names"] == ["深圳信立泰药业股份有限公司"]
    assert plan.evidence_need == ["text"]
    assert plan.time_scope.kind == "not_applicable"


def test_plans_uploaded_pdf_document_questions_as_pdf_rag():
    planner = FinancialQuestionPlanner()

    questions = [
        "这份PDF的主要风险是什么？",
        "上传的PDF里基金投资策略是什么？",
        "这个文档里说了什么？",
        "prospectus risk factors",
    ]

    for question in questions:
        plan = planner.plan(question)
        assert plan.route == "pdf_rag"
        assert plan.task_type == "disclosure_fact"
        assert plan.evidence_need == ["text"]


def test_plans_company_stock_code_lookup_question():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("武汉力源信息技术股份有限公司的股市代码是什么？")

    assert plan.route == "text_to_sql"
    assert plan.task_type == "stock_code_lookup"
    assert plan.entities["company_names"] == ["武汉力源信息技术股份有限公司"]
    assert plan.entities["stock_names"] == ["武汉力源信息技术股份有限公司"]
    assert plan.entities["stock_names_require_lookup"] is True
    assert plan.time_scope.kind == "not_applicable"


def test_plans_sql_first_hybrid_question_with_report_period():
    planner = FinancialQuestionPlanner()

    plan = planner.plan(
        "我想了解博时研究优选灵活配置混合(LOF)A基金,在2021年四季度的季报第3大重仓股。"
        "该持仓股票当个季度的涨跌幅?"
    )

    assert plan.route == "hybrid"
    assert plan.hybrid_mode == "sql_first"
    assert plan.task_type == "hybrid"
    assert plan.entities["fund_names"] == ["博时研究优选灵活配置混合(LOF)A基金"]
    assert plan.entities["years"] == ["2021"]
    assert plan.entities["quarters"] == ["Q4"]
    assert plan.answer_constraints.top_n == 3
    assert plan.formula == "daily_percent_change"
    assert plan.time_scope.kind == "report_period"
    assert plan.time_scope.value == "2021Q4"
    assert "季报" in plan.time_scope.report_types
    assert [item["target_path"] for item in plan.sub_questions] == [
        "text_to_sql",
        "entity_mapping",
        "text_to_sql",
    ]
    assert plan.sub_questions[1]["mapping"] == "sql_stock_result_to_prospectus_company_name"


def test_fund_code_context_preserves_obvious_fund_identifier():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("基金000001在2021年度收益率是多少？")

    assert plan.entities["fund_codes"] == ["000001"]
    assert "000001" not in plan.entities.get("stock_codes", [])
    assert plan.entities["fund_codes_require_lookup"] is False


def test_stock_name_requires_alias_lookup():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("贵州茅台在2021年度年化收益率是多少？")

    assert plan.entities["stock_names"] == ["贵州茅台"]
    assert plan.entities["stock_names_require_lookup"] is True


def test_stock_name_alias_lookup_common_forms_without_codes():
    planner = FinancialQuestionPlanner()

    questions = [
        "贵州茅台的年化收益率是多少？",
        "贵州茅台股票在2021年度年化收益率是多少？",
        "贵州茅台2021年度年化收益率是多少？",
    ]

    for question in questions:
        plan = planner.plan(question)
        assert plan.entities["stock_names"] == ["贵州茅台"]
        assert plan.entities["stock_names_require_lookup"] is True
        assert "基金" not in plan.entities["stock_names"]
        assert "股票" not in plan.entities["stock_names"]
        assert "行业" not in plan.entities["stock_names"]


def test_default_sql_first_hybrid_includes_entity_mapping_step():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("股票000001的主营业务是什么？")

    assert plan.route == "hybrid"
    assert plan.hybrid_mode == "sql_first"
    assert [item["target_path"] for item in plan.sub_questions] == [
        "text_to_sql",
        "entity_mapping",
        "pdf_rag",
    ]
    assert plan.sub_questions[1]["mapping"] == "sql_stock_result_to_prospectus_company_name"


def test_plans_annual_range_and_per_entity_latest_report():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("使用每只基金2021年度最晚的定期报告数据，统计基金数量和份额合计。")

    assert plan.route == "text_to_sql"
    assert plan.task_type == "aggregate_statistics"
    assert plan.entities["years"] == ["2021"]
    assert plan.time_scope.kind == "per_entity_latest_report"
    assert plan.time_scope.start == "20210101"
    assert plan.time_scope.end == "20211231"
    assert plan.time_scope.per_entity_latest is True
    assert "定期报告" in plan.time_scope.report_types
    assert plan.answer_constraints.count is True
    assert plan.answer_constraints.sum is True


def test_plans_report_period_from_q2_and_explicit_date():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("易方达蓝筹精选混合基金在2021 Q2和20210630半年度报告中的股票持仓是多少？")

    assert plan.route == "text_to_sql"
    assert plan.task_type == "report_period_query"
    assert plan.entities["fund_names"] == ["易方达蓝筹精选混合基金"]
    assert plan.entities["fund_names_require_lookup"] is True
    assert plan.entities["dates"] == ["20210630"]
    assert plan.entities["quarters"] == ["Q2"]
    assert plan.time_scope.kind == "report_period"
    assert plan.time_scope.value == "2021Q2"
    assert plan.time_scope.start == "20210401"
    assert plan.time_scope.end == "20210630"
    assert "半年度报告" in plan.time_scope.report_types


def test_detects_formula_and_constraint_variants():
    planner = FinancialQuestionPlanner()

    cases = [
        ("2021年度股票000001涨停天数是多少？涨停定义为收盘价除以前收盘价减一大于等于9.8%。", "limit_up_days"),
        ("2021年股票000001最高价和最低价的价差最大是多少？", "price_range"),
        ("2021年股票000001开盘价高于昨收盘价的交易日有几天？", "open_above_previous_close_days"),
        ("2021年股票000001成交量低于全年平均成交量的交易日有多少？", "low_volume_days"),
        ("2021年度股票000001年化收益率是多少？", "annualized_return"),
    ]

    for question, formula in cases:
        plan = planner.plan(question)
        assert plan.formula == formula

    limit_up = planner.plan("股票000001涨停天数是多少？涨停定义为收盘价除以前收盘价减一大于等于9.8%。")
    assert limit_up.formula_params["threshold"] == 0.098
    assert "9.8%" in limit_up.raw_formula_text

    ranking = planner.plan("列出2021年收益率最高的前5只基金，平均收益率保留3位小数。")
    assert ranking.task_type == "ranking"
    assert ranking.answer_constraints.top_n == 5
    assert ranking.answer_constraints.average is True
    assert ranking.answer_constraints.precision == 3


def test_unknown_formula_preserves_raw_formula_text():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("股票000001的神奇收益指标是多少？公式为收盘价乘以月亮系数。")

    assert plan.formula == "unknown"
    assert plan.raw_formula_text == "收盘价乘以月亮系数"


def test_normalizes_mojibake_and_english_industry_standards():
    planner = FinancialQuestionPlanner()

    assert planner.plan("CITIC industry classification 下股票000001的行业是什么？").entities[
        "industry_standard"
    ] == "中信行业分类"
    assert planner.plan("Shenwan industry classification 下股票000001的行业是什么？").entities[
        "industry_standard"
    ] == "申万行业分类"
    assert planner.plan("涓俊琛屼笟鍒嗙被 下股票000001的行业是什么？").entities[
        "industry_standard"
    ] == "中信行业分类"
    assert planner.plan("鐢充竾琛屼笟鍒嗙被 下股票000001的行业是什么？").entities[
        "industry_standard"
    ] == "申万行业分类"


def test_preserves_mojibake_formula_routing_and_constraints():
    planner = FinancialQuestionPlanner()

    plan = planner.plan(
        "璇峰府鎴戣绠楋紝鍦?0210105锛屼腑淇¤涓氬垎绫诲垝鍒嗙殑涓€绾ц涓氫负缁煎悎閲戣瀺琛屼笟涓紝"
        "娑ㄨ穼骞呮渶澶ц偂绁ㄧ殑鑲＄エ浠ｇ爜鏄紵娑ㄨ穼骞呮槸澶氬皯锛熺櫨鍒嗘暟淇濈暀涓や綅灏忔暟銆?"
    )

    assert plan.route == "text_to_sql"
    assert plan.formula == "daily_percent_change"
    assert plan.answer_constraints.output_type == "percentage"
    assert plan.answer_constraints.precision == 2
    assert plan.answer_constraints.order == "desc"
    assert plan.answer_constraints.top_n == 1


def test_preserves_mojibake_prospectus_route_and_company_extraction():
    planner = FinancialQuestionPlanner()

    plan = planner.plan("娣卞湷淇＄珛娉拌嵂涓氳偂浠芥湁闄愬叕鍙镐富钀ヤ笟鍔℃槸浠€涔堬紵")

    assert plan.route == "pdf_rag"
    assert plan.task_type == "disclosure_fact"
    assert plan.entities["company_names"] == ["娣卞湷淇＄珛娉拌嵂涓氳偂浠芥湁闄愬叕鍙?"]
    assert plan.time_scope.kind == "not_applicable"


def test_preserves_mojibake_latest_report_period_and_fund_extraction():
    planner = FinancialQuestionPlanner()

    latest = planner.plan(
        "鎴戞兂鐭ラ亾鑲＄エ000637鍦ㄧ敵涓囪涓氬垎绫讳笅鐨勪簩绾ц涓氭槸浠€涔堬紵鐢ㄦ渶鏂扮殑鏁版嵁銆?"
    )
    assert latest.task_type == "latest_record_lookup"
    assert latest.time_scope.kind == "latest"

    report_period = planner.plan(
        "鏄撴柟杈捐摑绛圭簿閫夋贩鍚堝熀閲戝湪2021 Q2鍜?0210630鍗婂勾搴︽姤鍛婁腑鐨勮偂绁ㄦ寔浠撴槸澶氬皯锛?"
    )
    assert report_period.task_type == "report_period_query"
    assert report_period.entities["fund_names"] == ["鏄撴柟杈捐摑绛圭簿閫夋贩鍚堝熀閲?"]
    assert report_period.time_scope.kind == "report_period"
    assert report_period.time_scope.value == "2021Q2"
