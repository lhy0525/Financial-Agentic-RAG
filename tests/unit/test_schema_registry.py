from src.financial_sql.schema_registry import FinancialSchemaRegistry


def test_registry_exposes_all_financial_tables():
    registry = FinancialSchemaRegistry()

    assert len(registry.tables) == 10
    assert registry.find_table("A股股票日行情").name == "A股票日行情表"
    assert registry.find_table("基金持仓").name == "基金股票持仓明细"


def test_registry_resolves_columns_and_industry_standard_aliases():
    registry = FinancialSchemaRegistry()
    quote = registry.find_table("A股股票日行情")

    assert quote.date_columns == ["交易日"]
    assert registry.find_column(quote.name, "收盘") == "收盘价(元)"
    assert registry.normalize_industry_standard("申万") == "申万行业分类"
    assert registry.normalize_industry_standard("中信行业分类") == "中信行业分类"


def test_registry_returns_join_hint_for_stock_industry_quotes():
    registry = FinancialSchemaRegistry()
    hint = registry.get_join_hint("quote_industry")

    assert hint.left_table == "A股票日行情表"
    assert hint.right_table == "A股公司行业划分表"
    assert hint.keys == ["股票代码", "交易日=交易日期"]
