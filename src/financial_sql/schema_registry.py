from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: list[str]
    aliases: list[str] = field(default_factory=list)
    date_columns: list[str] = field(default_factory=list)
    column_aliases: dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class JoinHint:
    name: str
    left_table: str
    right_table: str
    keys: list[str]


class FinancialSchemaRegistry:
    """Registry for the 10-table Bosera financial SQLite dataset."""

    def __init__(self) -> None:
        self._tables = self._build_tables()
        self._joins = {
            "quote_industry": JoinHint(
                name="quote_industry",
                left_table="A股票日行情表",
                right_table="A股公司行业划分表",
                keys=["股票代码", "交易日=交易日期"],
            ),
            "holding_industry": JoinHint(
                name="holding_industry",
                left_table="基金股票持仓明细",
                right_table="A股公司行业划分表",
                keys=["股票代码", "持仓日期=交易日期"],
            ),
            "convertible_industry": JoinHint(
                name="convertible_industry",
                left_table="基金可转债持仓明细",
                right_table="A股公司行业划分表",
                keys=["对应股票代码=股票代码", "持仓日期=交易日期"],
            ),
        }
        self._industry_standard_aliases = {
            "申万": "申万行业分类",
            "申万行业": "申万行业分类",
            "申万行业分类": "申万行业分类",
            "中信": "中信行业分类",
            "中信行业": "中信行业分类",
            "中信行业分类": "中信行业分类",
        }

    @property
    def tables(self) -> dict[str, TableSchema]:
        return dict(self._tables)

    def find_table(self, phrase: str) -> TableSchema | None:
        if phrase in self._tables:
            return self._tables[phrase]
        normalized = phrase.strip().lower()
        for table in self._tables.values():
            names = [table.name, *table.aliases]
            if any(normalized == item.lower() or normalized in item.lower() for item in names):
                return table
        return None

    def find_column(self, table_name: str, phrase: str) -> str | None:
        table = self._tables.get(table_name)
        if table is None:
            return None
        if phrase in table.columns:
            return phrase
        normalized = phrase.strip().lower()
        for alias, column in table.column_aliases.items():
            if normalized == alias.lower():
                return column
        for alias, column in table.column_aliases.items():
            if normalized in alias.lower():
                return column
        for column in table.columns:
            if normalized in column.lower():
                return column
        return None

    def get_join_hint(self, name: str) -> JoinHint | None:
        return self._joins.get(name)

    def normalize_industry_standard(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._industry_standard_aliases.get(value.strip(), value.strip())

    def _build_tables(self) -> dict[str, TableSchema]:
        quote_columns = [
            "股票代码",
            "交易日",
            "昨收盘(元)",
            "今开盘(元)",
            "最高价(元)",
            "最低价(元)",
            "收盘价(元)",
            "成交量(股)",
            "成交金额(元)",
        ]
        quote_aliases = {
            "股票": "股票代码",
            "日期": "交易日",
            "交易日期": "交易日",
            "昨收": "昨收盘(元)",
            "前收盘": "昨收盘(元)",
            "开盘": "今开盘(元)",
            "最高": "最高价(元)",
            "最低": "最低价(元)",
            "收盘": "收盘价(元)",
            "成交量": "成交量(股)",
            "成交金额": "成交金额(元)",
        }
        return {
            "基金基本信息": TableSchema(
                name="基金基本信息",
                aliases=["基金信息", "基金基本", "基金名称", "基金简称", "管理人"],
                columns=[
                    "基金代码",
                    "基金全称",
                    "基金简称",
                    "管理人",
                    "托管人",
                    "基金类型",
                    "成立日期",
                    "到期日期",
                    "管理费率",
                    "托管费率",
                ],
                date_columns=["成立日期", "到期日期"],
                column_aliases={"代码": "基金代码", "全称": "基金全称", "简称": "基金简称"},
                description="Fund master data.",
            ),
            "基金股票持仓明细": TableSchema(
                name="基金股票持仓明细",
                aliases=["基金持仓", "股票持仓", "重仓股", "持仓明细"],
                columns=[
                    "基金代码",
                    "基金简称",
                    "持仓日期",
                    "股票代码",
                    "股票名称",
                    "数量",
                    "市值",
                    "市值占基金资产净值比",
                    "第N大重仓股",
                    "所在证券市场",
                    "所属国家(地区)",
                    "报告类型",
                ],
                date_columns=["持仓日期"],
                column_aliases={
                    "基金": "基金代码",
                    "股票": "股票代码",
                    "名称": "股票名称",
                    "排名": "第N大重仓股",
                    "报告": "报告类型",
                },
                description="Fund stock holding records by report period.",
            ),
            "基金债券持仓明细": TableSchema(
                name="基金债券持仓明细",
                aliases=["债券持仓", "持债", "债券明细"],
                columns=[
                    "基金代码",
                    "基金简称",
                    "持仓日期",
                    "债券类型",
                    "债券名称",
                    "持债数量",
                    "持债市值",
                    "持债市值占基金资产净值比",
                    "第N大重仓股",
                    "所在证券市场",
                    "所属国家(地区)",
                    "报告类型",
                ],
                date_columns=["持仓日期"],
            ),
            "基金可转债持仓明细": TableSchema(
                name="基金可转债持仓明细",
                aliases=["可转债", "可转债持仓", "转债持仓"],
                columns=[
                    "基金代码",
                    "基金简称",
                    "持仓日期",
                    "对应股票代码",
                    "债券名称",
                    "数量",
                    "市值",
                    "市值占基金资产净值比",
                    "第N大重仓股",
                    "所在证券市场",
                    "所属国家(地区)",
                    "报告类型",
                ],
                date_columns=["持仓日期"],
            ),
            "基金日行情表": TableSchema(
                name="基金日行情表",
                aliases=["基金行情", "基金净值", "单位净值", "资产净值"],
                columns=["基金代码", "交易日期", "单位净值", "复权单位净值", "累计单位净值", "资产净值"],
                date_columns=["交易日期"],
            ),
            "A股票日行情表": TableSchema(
                name="A股票日行情表",
                aliases=["A股股票日行情", "A股行情", "股票行情", "日行情"],
                columns=quote_columns,
                date_columns=["交易日"],
                column_aliases=quote_aliases,
                description="A-share daily quote records.",
            ),
            "港股票日行情表": TableSchema(
                name="港股票日行情表",
                aliases=["港股股票日行情", "港股行情", "港股票行情"],
                columns=quote_columns,
                date_columns=["交易日"],
                column_aliases=quote_aliases,
            ),
            "A股公司行业划分表": TableSchema(
                name="A股公司行业划分表",
                aliases=["行业划分", "行业分类", "申万行业", "中信行业", "股票行业"],
                columns=["股票代码", "交易日期", "行业划分标准", "一级行业名称", "二级行业名称"],
                date_columns=["交易日期"],
                column_aliases={
                    "股票": "股票代码",
                    "日期": "交易日期",
                    "交易日": "交易日期",
                    "行业标准": "行业划分标准",
                    "一级行业": "一级行业名称",
                    "二级行业": "二级行业名称",
                },
                description="A-share industry classification by standard and date.",
            ),
            "基金规模变动表": TableSchema(
                name="基金规模变动表",
                aliases=["基金规模", "申购", "赎回", "份额变动"],
                columns=[
                    "基金代码",
                    "基金简称",
                    "公告日期",
                    "截止日期",
                    "报告期期初基金总份额",
                    "报告期基金总申购份额",
                    "报告期基金总赎回份额",
                    "报告期期末基金总份额",
                    "定期报告所属年度",
                    "报告类型",
                ],
                date_columns=["公告日期", "截止日期"],
            ),
            "基金份额持有人结构": TableSchema(
                name="基金份额持有人结构",
                aliases=["持有人结构", "机构投资者", "个人投资者"],
                columns=[
                    "基金代码",
                    "基金简称",
                    "公告日期",
                    "截止日期",
                    "机构投资者持有的基金份额",
                    "机构投资者持有的基金份额占总份额比例",
                    "个人投资者持有的基金份额",
                    "个人投资者持有的基金份额占总份额比例",
                    "定期报告所属年度",
                    "报告类型",
                ],
                date_columns=["公告日期", "截止日期"],
            ),
        }
