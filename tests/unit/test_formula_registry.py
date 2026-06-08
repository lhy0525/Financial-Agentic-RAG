from src.financial_sql.formula_registry import FormulaRegistry


def test_daily_percent_change_sql_expression():
    formula = FormulaRegistry().get("daily_percent_change")

    assert formula.identifier == "daily_percent_change"
    assert formula.sql_expression == '(("收盘价(元)" / "昨收盘(元)") - 1) * 100'
    assert formula.output_unit == "percent"


def test_limit_up_threshold_metadata():
    formula = FormulaRegistry().get("limit_up_days")

    assert formula.default_threshold == 0.098
    assert "收盘价(元)" in formula.required_columns
    assert "昨收盘(元)" in formula.required_columns


def test_unknown_formula_returns_none():
    assert FormulaRegistry().get("not_registered") is None


def test_planner_formula_aliases_are_registered():
    registry = FormulaRegistry()

    for identifier in [
        "price_range",
        "open_above_previous_close_days",
        "low_volume_days",
        "annualized_return",
        "limit_up_days",
    ]:
        assert registry.get(identifier).identifier == identifier
