from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FormulaDefinition:
    identifier: str
    sql_expression: str
    required_columns: list[str]
    description: str
    output_unit: str | None = None
    default_threshold: float | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class FormulaRegistry:
    def __init__(self) -> None:
        self._formulas = {
            "daily_percent_change": FormulaDefinition(
                identifier="daily_percent_change",
                sql_expression='(("收盘价(元)" / "昨收盘(元)") - 1) * 100',
                required_columns=["收盘价(元)", "昨收盘(元)"],
                description="Daily percent change from close and previous close.",
                output_unit="percent",
                metadata={"safe_division": "NULLIF denominator"},
            ),
            "daily_return": FormulaDefinition(
                identifier="daily_return",
                sql_expression='("收盘价(元)" - "昨收盘(元)") / "昨收盘(元)"',
                required_columns=["收盘价(元)", "昨收盘(元)"],
                description="Daily return as a ratio.",
                output_unit="ratio",
            ),
            "limit_up_days": FormulaDefinition(
                identifier="limit_up_days",
                sql_expression='(("收盘价(元)" / "昨收盘(元)") - 1) >= 0.098',
                required_columns=["收盘价(元)", "昨收盘(元)"],
                description="Trading days whose close-to-previous-close return reaches the limit-up threshold.",
                output_unit="count",
                default_threshold=0.098,
            ),
            "price_range": FormulaDefinition(
                identifier="price_range",
                sql_expression='"最高价(元)" - "最低价(元)"',
                required_columns=["最高价(元)", "最低价(元)"],
                description="Difference between intraday high and low.",
                output_unit="currency",
            ),
            "intraday_price_range": FormulaDefinition(
                identifier="intraday_price_range",
                sql_expression='"最高价(元)" - "最低价(元)"',
                required_columns=["最高价(元)", "最低价(元)"],
                description="Difference between intraday high and low.",
                output_unit="currency",
            ),
            "open_above_previous_close_days": FormulaDefinition(
                identifier="open_above_previous_close_days",
                sql_expression='"今开盘(元)" > "昨收盘(元)"',
                required_columns=["今开盘(元)", "昨收盘(元)"],
                description="Count of days whose open price is above previous close.",
                output_unit="count",
            ),
            "open_above_previous_close": FormulaDefinition(
                identifier="open_above_previous_close",
                sql_expression='"今开盘(元)" > "昨收盘(元)"',
                required_columns=["今开盘(元)", "昨收盘(元)"],
                description="True when open price is above previous close.",
                output_unit="count",
            ),
            "low_volume_days": FormulaDefinition(
                identifier="low_volume_days",
                sql_expression='"成交量(股)" < AVG("成交量(股)")',
                required_columns=["成交量(股)"],
                description="Days whose volume is lower than an annual average volume.",
                output_unit="count",
            ),
            "annualized_return": FormulaDefinition(
                identifier="annualized_return",
                sql_expression='(("收盘价(元)" / "今开盘(元)") - 1) * 100',
                required_columns=["收盘价(元)", "今开盘(元)"],
                description="Percent return using first opening and final closing prices in a period.",
                output_unit="percent",
            ),
        }

    def get(self, identifier: str) -> FormulaDefinition | None:
        return self._formulas.get(identifier)

    def all(self) -> dict[str, FormulaDefinition]:
        return dict(self._formulas)
