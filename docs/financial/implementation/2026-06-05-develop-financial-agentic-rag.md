# Develop Financial Agentic RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Historical note:** This implementation plan was written before the financial project was consolidated into `financial-agentic-rag` as a standalone repository. References to `MODULAR-RAG-MCP-SERVER/...` should now be read as paths rooted at the current repository root.

**Goal:** Build the spec-driven financial Agentic RAG layer that plans finance questions, produces SQL and prospectus evidence, verifies results, and evaluates dataset task families.

**Architecture:** Additive modules live under `src` in this repository and reuse existing RAG retrieval components instead of rewriting MCP tools. The flow is `QuestionPlan -> SQL Evidence / Prospectus Evidence -> Orchestrator -> Merger -> Verifier -> FinalAnswer`, with evaluation runners measuring each stage.

**Tech Stack:** Python 3.10+, dataclasses, sqlite3, pytest, existing Chroma/BM25 retrieval, existing trace collector, OpenSpec artifacts in `openspec/changes/develop-financial-agentic-rag`.

---

## Ground Rules

- Run implementation commands from the `financial-agentic-rag` repository root.
- Keep all code additive unless a task explicitly modifies an existing file.
- Do not change existing MCP tool schemas in the first pass.
- Use deterministic rules before LLM calls for planner, formula, SQL safety, and verifier behavior.
- After each task, run the listed focused tests before committing.
- Use the current repository as the product boundary for commands, docs, tests, and commits.

## File Structure

Create these modules:

- `src/agentic/types.py`: shared contracts for plans, evidence, verification, and final answers.
- `src/agentic/planner.py`: rule-first `FinancialQuestionPlanner`.
- `src/agentic/orchestrator.py`: single-path and hybrid flow controller.
- `src/agentic/merger.py`: evidence grouping and deduplication.
- `src/agentic/verifier.py`: sufficiency, source priority, numeric checks, and answer formatting.
- `src/financial_sql/schema_registry.py`: SQLite table/column metadata and aliases.
- `src/financial_sql/formula_registry.py`: formula identifiers and deterministic formula expressions.
- `src/financial_sql/entity_resolver.py`: fund/stock alias resolution.
- `src/financial_sql/sql_safety.py`: SELECT-only safety checker.
- `src/financial_sql/sql_executor.py`: sqlite execution, row caps, and logs.
- `src/financial_sql/text_to_sql_tool.py`: SQL evidence path facade.
- `src/prospectus_evidence/txt_loader.py`: parsed TXT document loader.
- `src/prospectus_evidence/evidence_tool.py`: wraps retrieval results as evidence packages.
- `src/prospectus_evidence/element_docstore.py`: minimal docstore interface for future raw table recovery.
- `src/observability/evaluation/financial_eval_runner.py`: staged financial evaluation runner.
- `scripts/financial_query.py`: CLI smoke entrypoint for financial QA.

Create these tests:

- `tests/unit/test_agentic_types.py`
- `tests/unit/test_financial_planner.py`
- `tests/unit/test_schema_registry.py`
- `tests/unit/test_formula_registry.py`
- `tests/unit/test_entity_resolver.py`
- `tests/unit/test_sql_safety.py`
- `tests/unit/test_sql_executor.py`
- `tests/unit/test_text_to_sql_tool.py`
- `tests/unit/test_prospectus_txt_loader.py`
- `tests/unit/test_prospectus_evidence_tool.py`
- `tests/unit/test_financial_merger_verifier.py`
- `tests/unit/test_financial_orchestrator.py`
- `tests/unit/test_financial_eval_runner.py`
- `tests/integration/test_financial_sql_dataset.py`

## Task 1: Shared Agent Contracts

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/src/agentic/__init__.py`
- Create: `MODULAR-RAG-MCP-SERVER/src/agentic/types.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_agentic_types.py`

- [ ] **Step 1: Write failing shared contract tests**

Add this to `tests/unit/test_agentic_types.py`:

```python
from src.agentic.types import (
    AnswerConstraints,
    Evidence,
    EvidencePackage,
    QuestionPlan,
    TimeScope,
    VerificationReport,
)


def test_question_plan_serializes_nested_fields():
    plan = QuestionPlan(
        route="text_to_sql",
        task_type="quote_formula",
        entities={"stock_codes": ["000001"]},
        time_scope=TimeScope(kind="trading_date", value="20210105"),
        formula="daily_percent_change",
        evidence_need=["sql_result"],
        sub_questions=[],
        answer_constraints=AnswerConstraints(output_type="percentage", precision=2),
        reason="needs quote calculation",
    )

    data = plan.to_dict()

    assert data["route"] == "text_to_sql"
    assert data["time_scope"]["kind"] == "trading_date"
    assert data["answer_constraints"]["precision"] == 2
    assert QuestionPlan.from_dict(data) == plan


def test_evidence_package_serializes_sql_metadata():
    evidence = Evidence(
        evidence_id="sql-1",
        evidence_type="sql_result",
        source_type="db",
        content="股票代码=000001, 涨跌幅=1.23%",
        source="博金杯比赛数据.db",
        metadata={"sql": "SELECT 1", "row_count": 1},
    )
    package = EvidencePackage(path="text_to_sql", question="q", evidences=[evidence])

    data = package.to_dict()

    assert data["evidences"][0]["metadata"]["sql"] == "SELECT 1"
    assert EvidencePackage.from_dict(data) == package


def test_verification_report_marks_missing_evidence():
    report = VerificationReport(
        status="insufficient",
        selected_evidence_ids=[],
        conflicts=[],
        missing_evidence=["raw_table"],
        notes=["Only placeholder was retrieved"],
    )

    assert report.to_dict()["status"] == "insufficient"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/unit/test_agentic_types.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.agentic'`.

- [ ] **Step 3: Create minimal implementation**

Create `src/agentic/__init__.py`:

```python
"""Agentic financial QA components."""
```

Create `src/agentic/types.py` with dataclasses:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional


Route = Literal["pdf_rag", "text_to_sql", "hybrid"]
HybridMode = Literal["doc_first", "sql_first"]
EvidenceType = Literal["text", "table", "image", "chart", "sql_result"]
SourceType = Literal["pdf", "txt", "db"]
VerificationStatus = Literal["pass", "partial", "conflict", "insufficient"]


@dataclass(frozen=True)
class TimeScope:
    kind: str
    value: Any
    start: Optional[str] = None
    end: Optional[str] = None
    report_types: list[str] = field(default_factory=list)
    date_column: Optional[str] = None
    per_entity_latest: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimeScope":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnswerConstraints:
    output_type: str = "text"
    precision: Optional[int] = None
    unit: Optional[str] = None
    preserve_identifier_zeroes: bool = True
    order: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnswerConstraints":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuestionPlan:
    route: Route
    task_type: str
    entities: dict[str, Any]
    time_scope: TimeScope
    formula: Optional[str]
    evidence_need: list[str]
    sub_questions: list[dict[str, str]]
    answer_constraints: AnswerConstraints
    reason: str
    hybrid_mode: Optional[HybridMode] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestionPlan":
        copy = dict(data)
        copy["time_scope"] = TimeScope.from_dict(copy["time_scope"])
        copy["answer_constraints"] = AnswerConstraints.from_dict(copy["answer_constraints"])
        return cls(**copy)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    evidence_type: EvidenceType
    source_type: SourceType
    content: str
    source: str
    score: Optional[float] = None
    page: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidencePackage:
    path: Literal["pdf_rag", "text_to_sql"]
    question: str
    evidences: list[Evidence]
    trace_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidencePackage":
        copy = dict(data)
        copy["evidences"] = [Evidence.from_dict(item) for item in copy["evidences"]]
        return cls(**copy)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationReport:
    status: VerificationStatus
    selected_evidence_ids: list[str]
    conflicts: list[dict[str, Any]]
    missing_evidence: list[str]
    notes: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationReport":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
pytest tests/unit/test_agentic_types.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/agentic tests/unit/test_agentic_types.py
git commit -m "feat: add financial agent contracts"
```

## Task 2: Schema and Formula Registries

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/src/financial_sql/__init__.py`
- Create: `MODULAR-RAG-MCP-SERVER/src/financial_sql/schema_registry.py`
- Create: `MODULAR-RAG-MCP-SERVER/src/financial_sql/formula_registry.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_schema_registry.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_formula_registry.py`

- [ ] **Step 1: Write failing registry tests**

Add `tests/unit/test_schema_registry.py`:

```python
from src.financial_sql.schema_registry import FinancialSchemaRegistry


def test_registry_resolves_quote_alias():
    registry = FinancialSchemaRegistry()
    table = registry.find_table("A股股票日行情")

    assert table.name == "A股票日行情表"
    assert table.date_columns == ["交易日"]
    assert "收盘价(元)" in table.columns


def test_registry_resolves_industry_standard_aliases():
    registry = FinancialSchemaRegistry()

    assert registry.normalize_industry_standard("中信行业分类") == "中信行业分类"
    assert registry.normalize_industry_standard("申万行业分类") == "申万行业分类"


def test_registry_returns_join_hint_for_stock_industry_quotes():
    registry = FinancialSchemaRegistry()
    hint = registry.get_join_hint("quote_industry")

    assert hint.left_table == "A股票日行情表"
    assert hint.right_table == "A股公司行业划分表"
    assert hint.keys == ["股票代码", "交易日=交易日期"]
```

Add `tests/unit/test_formula_registry.py`:

```python
from src.financial_sql.formula_registry import FormulaRegistry


def test_daily_percent_change_sql_expression():
    registry = FormulaRegistry()
    formula = registry.get("daily_percent_change")

    assert formula.identifier == "daily_percent_change"
    assert formula.sql_expression == '("收盘价(元)" / "昨收盘(元)" - 1) * 100'


def test_limit_up_threshold_metadata():
    registry = FormulaRegistry()
    formula = registry.get("limit_up_days")

    assert formula.default_threshold == 0.098
    assert "收盘价(元)" in formula.required_columns


def test_unknown_formula_returns_none():
    registry = FormulaRegistry()

    assert registry.get("not_registered") is None
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/unit/test_schema_registry.py tests/unit/test_formula_registry.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.financial_sql'`.

- [ ] **Step 3: Implement registries**

Create `src/financial_sql/__init__.py`:

```python
"""Financial SQL evidence path."""
```

Create `src/financial_sql/schema_registry.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: list[str]
    aliases: list[str] = field(default_factory=list)
    date_columns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class JoinHint:
    name: str
    left_table: str
    right_table: str
    keys: list[str]


class FinancialSchemaRegistry:
    def __init__(self) -> None:
        self._tables = {
            "基金基本信息": TableSchema(
                name="基金基本信息",
                aliases=["基金信息", "基金基本", "管理人", "基金类型"],
                columns=["基金代码", "基金全称", "基金简称", "管理人", "托管人", "基金类型", "成立日期", "到期日期", "管理费率", "托管费率"],
                date_columns=["成立日期", "到期日期"],
            ),
            "基金股票持仓明细": TableSchema(
                name="基金股票持仓明细",
                aliases=["股票持仓", "重仓股", "基金持仓"],
                columns=["基金代码", "基金简称", "持仓日期", "股票代码", "股票名称", "数量", "市值", "市值占基金资产净值比", "第N大重仓股", "所在证券市场", "所属国家(地区)", "报告类型"],
                date_columns=["持仓日期"],
            ),
            "基金债券持仓明细": TableSchema(
                name="基金债券持仓明细",
                aliases=["债券持仓", "持债", "债券类型"],
                columns=["基金代码", "基金简称", "持仓日期", "债券类型", "债券名称", "持债数量", "持债市值", "持债市值占基金资产净值比", "第N大重仓股", "所在证券市场", "所属国家(地区)", "报告类型"],
                date_columns=["持仓日期"],
            ),
            "基金可转债持仓明细": TableSchema(
                name="基金可转债持仓明细",
                aliases=["可转债", "可转债持仓"],
                columns=["基金代码", "基金简称", "持仓日期", "对应股票代码", "债券名称", "数量", "市值", "市值占基金资产净值比", "第N大重仓股", "所在证券市场", "所属国家(地区)", "报告类型"],
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
                aliases=["A股股票日行情", "A股行情", "股票行情", "日行情", "成交金额", "成交量"],
                columns=["股票代码", "交易日", "昨收盘(元)", "今开盘(元)", "最高价(元)", "最低价(元)", "收盘价(元)", "成交量(股)", "成交金额(元)"],
                date_columns=["交易日"],
            ),
            "港股票日行情表": TableSchema(
                name="港股票日行情表",
                aliases=["港股行情", "港股票行情"],
                columns=["股票代码", "交易日", "昨收盘(元)", "今开盘(元)", "最高价(元)", "最低价(元)", "收盘价(元)", "成交量(股)", "成交金额(元)"],
                date_columns=["交易日"],
            ),
            "A股公司行业划分表": TableSchema(
                name="A股公司行业划分表",
                aliases=["行业划分", "行业分类", "中信行业", "申万行业"],
                columns=["股票代码", "交易日期", "行业划分标准", "一级行业名称", "二级行业名称"],
                date_columns=["交易日期"],
            ),
            "基金规模变动表": TableSchema(
                name="基金规模变动表",
                aliases=["基金规模", "申购", "赎回", "份额变动"],
                columns=["基金代码", "基金简称", "公告日期", "截止日期", "报告期期初基金总份额", "报告期基金总申购份额", "报告期基金总赎回份额", "报告期期末基金总份额", "定期报告所属年度", "报告类型"],
                date_columns=["公告日期", "截止日期"],
            ),
            "基金份额持有人结构": TableSchema(
                name="基金份额持有人结构",
                aliases=["持有人结构", "机构投资者", "个人投资者"],
                columns=["基金代码", "基金简称", "公告日期", "截止日期", "机构投资者持有的基金份额", "机构投资者持有的基金份额占总份额比例", "个人投资者持有的基金份额", "个人投资者持有的基金份额占总份额比例", "定期报告所属年度", "报告类型"],
                date_columns=["公告日期", "截止日期"],
            ),
        }
        self._joins = {
            "quote_industry": JoinHint("quote_industry", "A股票日行情表", "A股公司行业划分表", ["股票代码", "交易日=交易日期"]),
            "holding_industry": JoinHint("holding_industry", "基金股票持仓明细", "A股公司行业划分表", ["股票代码", "持仓日期=交易日期"]),
            "convertible_industry": JoinHint("convertible_industry", "基金可转债持仓明细", "A股公司行业划分表", ["对应股票代码=股票代码", "持仓日期=交易日期"]),
        }

    def find_table(self, phrase: str) -> Optional[TableSchema]:
        if phrase in self._tables:
            return self._tables[phrase]
        for table in self._tables.values():
            if any(alias in phrase or phrase in alias for alias in table.aliases):
                return table
        return None

    def get_table(self, name: str) -> TableSchema:
        return self._tables[name]

    def get_join_hint(self, name: str) -> JoinHint:
        return self._joins[name]

    def normalize_industry_standard(self, raw: str) -> str:
        if "申万" in raw:
            return "申万行业分类"
        if "中信" in raw:
            return "中信行业分类"
        return raw
```

Create `src/financial_sql/formula_registry.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FormulaDefinition:
    identifier: str
    sql_expression: str
    required_columns: list[str]
    default_threshold: Optional[float] = None
    output_type: str = "number"


class FormulaRegistry:
    def __init__(self) -> None:
        self._definitions = {
            "daily_percent_change": FormulaDefinition(
                identifier="daily_percent_change",
                sql_expression='("收盘价(元)" / "昨收盘(元)" - 1) * 100',
                required_columns=["收盘价(元)", "昨收盘(元)"],
                output_type="percentage",
            ),
            "daily_return": FormulaDefinition(
                identifier="daily_return",
                sql_expression='("收盘价(元)" - "昨收盘(元)") / "昨收盘(元)"',
                required_columns=["收盘价(元)", "昨收盘(元)"],
            ),
            "limit_up_days": FormulaDefinition(
                identifier="limit_up_days",
                sql_expression='("收盘价(元)" / "昨收盘(元)" - 1)',
                required_columns=["收盘价(元)", "昨收盘(元)"],
                default_threshold=0.098,
            ),
            "intraday_price_range": FormulaDefinition(
                identifier="intraday_price_range",
                sql_expression='("最高价(元)" - "最低价(元)")',
                required_columns=["最高价(元)", "最低价(元)"],
            ),
            "annualized_return": FormulaDefinition(
                identifier="annualized_return",
                sql_expression="computed_from_first_open_and_last_close",
                required_columns=["今开盘(元)", "收盘价(元)", "交易日"],
                output_type="percentage",
            ),
        }

    def get(self, identifier: str) -> Optional[FormulaDefinition]:
        return self._definitions.get(identifier)
```

- [ ] **Step 4: Run registry tests**

Run:

```powershell
pytest tests/unit/test_schema_registry.py tests/unit/test_formula_registry.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/financial_sql tests/unit/test_schema_registry.py tests/unit/test_formula_registry.py
git commit -m "feat: add financial SQL registries"
```

## Task 3: Rule-First Financial Question Planner

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/src/agentic/planner.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_financial_planner.py`

- [ ] **Step 1: Write failing planner tests**

Add `tests/unit/test_financial_planner.py`:

```python
from src.agentic.planner import FinancialQuestionPlanner


def test_plans_industry_quote_formula_question():
    planner = FinancialQuestionPlanner()
    plan = planner.plan("请帮我计算，在20210105，中信行业分类划分的一级行业为综合金融行业中，涨跌幅最大股票的股票代码是？涨跌幅是多少？百分数保留两位小数。")

    assert plan.route == "text_to_sql"
    assert plan.task_type == "quote_formula"
    assert plan.time_scope.kind == "trading_date"
    assert plan.time_scope.value == "20210105"
    assert plan.entities["industry_standard"] == "中信行业分类"
    assert plan.entities["level1_industry"] == "综合金融"
    assert plan.formula == "daily_percent_change"
    assert plan.answer_constraints.output_type == "percentage"
    assert plan.answer_constraints.precision == 2


def test_plans_latest_industry_question():
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
    assert plan.task_type == "business_description"
    assert plan.entities["company_names"] == ["深圳信立泰药业股份有限公司"]
    assert plan.evidence_need == ["text"]


def test_plans_sql_first_hybrid_question():
    planner = FinancialQuestionPlanner()
    plan = planner.plan("我想了解博时研究优选灵活配置混合(LOF)A基金,在2021年四季度的季报第3大重股。该持仓股票当个季度的涨跌幅?")

    assert plan.route == "hybrid"
    assert plan.hybrid_mode == "sql_first"
    assert plan.task_type == "holding_return"
    assert len(plan.sub_questions) == 2
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/unit/test_financial_planner.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.agentic.planner'`.

- [ ] **Step 3: Implement planner**

Create `src/agentic/planner.py`:

```python
from __future__ import annotations

import re

from src.agentic.types import AnswerConstraints, QuestionPlan, TimeScope


class FinancialQuestionPlanner:
    def plan(self, question: str) -> QuestionPlan:
        stock_codes = re.findall(r"(?<!\d)(?:00|30|60|68)\d{4}(?!\d)", question)
        date_match = re.search(r"(20\d{6})", question)
        precision = self._extract_precision(question)
        industry_standard = self._extract_industry_standard(question)
        level1_industry = self._extract_level_industry(question, "一级行业")
        company_names = re.findall(r"([\u4e00-\u9fa5A-Za-z0-9（）()]+股份有限公司)", question)

        if self._is_hybrid_holding_return(question):
            return QuestionPlan(
                route="hybrid",
                hybrid_mode="sql_first",
                task_type="holding_return",
                entities={"fund_names": self._extract_fund_names(question), "stock_codes": stock_codes},
                time_scope=self._extract_report_time_scope(question),
                formula="holding_period_return",
                evidence_need=["sql_result"],
                sub_questions=[
                    {"target_path": "text_to_sql", "question": "Resolve fund holding stock by report period and rank"},
                    {"target_path": "text_to_sql", "question": "Compute holding stock return during the quarter"},
                ],
                answer_constraints=AnswerConstraints(output_type="percentage", precision=precision),
                reason="Fund holding must be resolved before quote return calculation",
            )

        if self._is_prospectus_question(question):
            return QuestionPlan(
                route="pdf_rag",
                task_type=self._prospectus_task_type(question),
                entities={"company_names": company_names},
                time_scope=TimeScope(kind="not_applicable", value=None),
                formula=None,
                evidence_need=["text"],
                sub_questions=[],
                answer_constraints=AnswerConstraints(output_type="text"),
                reason="Question asks for prospectus disclosure",
            )

        if "最新" in question:
            return QuestionPlan(
                route="text_to_sql",
                task_type="latest_record_lookup",
                entities={"stock_codes": stock_codes, "industry_standard": industry_standard},
                time_scope=TimeScope(kind="latest", value=None, date_column="交易日期"),
                formula=None,
                evidence_need=["sql_result"],
                sub_questions=[],
                answer_constraints=AnswerConstraints(output_type="text"),
                reason="Question asks for latest database record",
            )

        return QuestionPlan(
            route="text_to_sql",
            task_type="quote_formula",
            entities={
                "stock_codes": stock_codes,
                "industry_standard": industry_standard,
                "level1_industry": level1_industry,
            },
            time_scope=TimeScope(kind="trading_date", value=date_match.group(1) if date_match else None),
            formula=self._extract_formula(question),
            evidence_need=["sql_result"],
            sub_questions=[],
            answer_constraints=AnswerConstraints(output_type="percentage" if "百分" in question or "涨跌幅" in question else "number", precision=precision),
            reason="Question asks for structured database calculation",
        )

    def _extract_precision(self, question: str) -> int | None:
        if "两位" in question or "2位" in question:
            return 2
        if "三位" in question or "3位" in question:
            return 3
        if "五位" in question or "5位" in question:
            return 5
        if "取整" in question:
            return 0
        return None

    def _extract_industry_standard(self, question: str) -> str | None:
        if "申万" in question:
            return "申万行业分类"
        if "中信" in question:
            return "中信行业分类"
        return None

    def _extract_level_industry(self, question: str, marker: str) -> str | None:
        match = re.search(rf"{marker}(?:为|下)?([\u4e00-\u9fa5]+?)(?:行业|的|中|里)", question)
        return match.group(1) if match else None

    def _extract_formula(self, question: str) -> str | None:
        if "涨停" in question:
            return "limit_up_days"
        if "日收益率" in question:
            return "daily_return"
        if "最高价" in question and "最低价" in question:
            return "intraday_price_range"
        if "年化收益率" in question:
            return "annualized_return"
        if "涨跌幅" in question:
            return "daily_percent_change"
        return None

    def _is_prospectus_question(self, question: str) -> bool:
        disclosure_terms = ["主营业务", "经营模式", "控股股东", "法定代表人", "专利", "供应商", "竞争优势", "募集资金", "招股"]
        return any(term in question for term in disclosure_terms) and not any(term in question for term in ["基金", "股票日", "交易日"])

    def _prospectus_task_type(self, question: str) -> str:
        if "主营业务" in question:
            return "business_description"
        if "控股股东" in question:
            return "shareholder_fact"
        if "专利" in question:
            return "patent_fact"
        return "disclosure_fact"

    def _is_hybrid_holding_return(self, question: str) -> bool:
        return "基金" in question and "重" in question and ("涨跌幅" in question or "收益" in question)

    def _extract_fund_names(self, question: str) -> list[str]:
        match = re.search(r"我想了解(.+?)基金", question)
        return [match.group(1) + "基金"] if match else []

    def _extract_report_time_scope(self, question: str) -> TimeScope:
        if "四季度" in question or "Q4" in question:
            return TimeScope(kind="report_period", value="Q4", report_types=["季报"])
        if "半年度" in question or "20210630" in question:
            return TimeScope(kind="report_period", value="H1", report_types=["年报(含半年报)"])
        return TimeScope(kind="report_period", value=None)
```

- [ ] **Step 4: Run planner tests**

Run:

```powershell
pytest tests/unit/test_financial_planner.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/agentic/planner.py tests/unit/test_financial_planner.py
git commit -m "feat: add financial question planner"
```

## Task 4: SQL Safety and Executor

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/src/financial_sql/sql_safety.py`
- Create: `MODULAR-RAG-MCP-SERVER/src/financial_sql/sql_executor.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_sql_safety.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_sql_executor.py`

- [ ] **Step 1: Write failing safety and executor tests**

Add `tests/unit/test_sql_safety.py`:

```python
from src.financial_sql.sql_safety import SQLSafetyChecker


def test_select_only_sql_passes():
    checker = SQLSafetyChecker()

    result = checker.check('SELECT "股票代码" FROM "A股票日行情表" LIMIT 5')

    assert result.allowed is True
    assert result.reason == "ok"


def test_delete_sql_is_rejected():
    checker = SQLSafetyChecker()

    result = checker.check('DELETE FROM "A股票日行情表"')

    assert result.allowed is False
    assert "forbidden" in result.reason


def test_multiple_statements_are_rejected():
    checker = SQLSafetyChecker()

    result = checker.check('SELECT 1; SELECT 2')

    assert result.allowed is False
    assert "multiple" in result.reason
```

Add `tests/unit/test_sql_executor.py`:

```python
import sqlite3

from src.financial_sql.sql_executor import SQLiteQueryExecutor


def test_executor_returns_rows_and_columns(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE "基金基本信息" ("基金代码" TEXT, "基金简称" TEXT)')
    conn.execute('INSERT INTO "基金基本信息" VALUES ("000001", "测试基金")')
    conn.commit()
    conn.close()

    executor = SQLiteQueryExecutor(db_path=db_path, default_limit=10)
    result = executor.execute('SELECT "基金代码", "基金简称" FROM "基金基本信息"')

    assert result.status == "success"
    assert result.columns == ["基金代码", "基金简称"]
    assert result.rows == [{"基金代码": "000001", "基金简称": "测试基金"}]
    assert result.row_count == 1


def test_executor_rejects_unsafe_sql(tmp_path):
    db_path = tmp_path / "test.db"
    sqlite3.connect(db_path).close()
    executor = SQLiteQueryExecutor(db_path=db_path)

    result = executor.execute('DROP TABLE "基金基本信息"')

    assert result.status == "rejected"
    assert result.rows == []
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/unit/test_sql_safety.py tests/unit/test_sql_executor.py -v
```

Expected: FAIL with missing modules.

- [ ] **Step 3: Implement SQL safety and executor**

Create `src/financial_sql/sql_safety.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SQLSafetyResult:
    allowed: bool
    reason: str


class SQLSafetyChecker:
    _forbidden = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA)\b", re.IGNORECASE)

    def check(self, sql: str) -> SQLSafetyResult:
        stripped = sql.strip()
        if not stripped.lower().startswith("select"):
            return SQLSafetyResult(False, "not_select")
        if self._forbidden.search(stripped):
            return SQLSafetyResult(False, "forbidden_keyword")
        if ";" in stripped.rstrip(";"):
            return SQLSafetyResult(False, "multiple_statements")
        return SQLSafetyResult(True, "ok")
```

Create `src/financial_sql/sql_executor.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
import time
from typing import Any

from src.financial_sql.sql_safety import SQLSafetyChecker


@dataclass(frozen=True)
class SQLExecutionResult:
    status: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    elapsed_ms: float
    error: str | None = None


class SQLiteQueryExecutor:
    def __init__(self, db_path: str | Path, default_limit: int = 50) -> None:
        self.db_path = Path(db_path)
        self.default_limit = default_limit
        self.safety = SQLSafetyChecker()

    def execute(self, sql: str) -> SQLExecutionResult:
        safety = self.safety.check(sql)
        if not safety.allowed:
            return SQLExecutionResult("rejected", sql, [], [], 0, 0.0, safety.reason)

        safe_sql = self._with_limit(sql)
        started = time.monotonic()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(safe_sql)
            fetched = cursor.fetchall()
            columns = [item[0] for item in cursor.description or []]
            rows = [dict(row) for row in fetched]
            conn.close()
            elapsed_ms = (time.monotonic() - started) * 1000
            return SQLExecutionResult("success", safe_sql, columns, rows, len(rows), elapsed_ms)
        except Exception as exc:
            elapsed_ms = (time.monotonic() - started) * 1000
            return SQLExecutionResult("failed", safe_sql, [], [], 0, elapsed_ms, str(exc))

    def _with_limit(self, sql: str) -> str:
        if re_search_limit(sql):
            return sql.rstrip(";")
        return f"{sql.rstrip(';')} LIMIT {self.default_limit}"


def re_search_limit(sql: str) -> bool:
    import re
    return re.search(r"\blimit\s+\d+\b", sql, re.IGNORECASE) is not None
```

- [ ] **Step 4: Run safety/executor tests**

Run:

```powershell
pytest tests/unit/test_sql_safety.py tests/unit/test_sql_executor.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/financial_sql/sql_safety.py src/financial_sql/sql_executor.py tests/unit/test_sql_safety.py tests/unit/test_sql_executor.py
git commit -m "feat: add safe SQLite executor"
```

## Task 5: Entity Resolver and SQL Evidence Tool

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/src/financial_sql/entity_resolver.py`
- Create: `MODULAR-RAG-MCP-SERVER/src/financial_sql/text_to_sql_tool.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_entity_resolver.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_text_to_sql_tool.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/integration/test_financial_sql_dataset.py`

- [ ] **Step 1: Write failing unit tests**

Add `tests/unit/test_entity_resolver.py`:

```python
import sqlite3

from src.financial_sql.entity_resolver import EntityResolver


def test_resolves_fund_name_to_code(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE "基金基本信息" ("基金代码" TEXT, "基金简称" TEXT, "基金全称" TEXT)')
    conn.execute('INSERT INTO "基金基本信息" VALUES ("000001", "测试基金A", "测试基金A全称")')
    conn.commit()
    conn.close()

    resolver = EntityResolver(db_path)

    assert resolver.resolve_fund_code("测试基金A") == "000001"


def test_ambiguous_fund_name_returns_none(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE "基金基本信息" ("基金代码" TEXT, "基金简称" TEXT, "基金全称" TEXT)')
    conn.execute('INSERT INTO "基金基本信息" VALUES ("000001", "测试基金", "测试基金一")')
    conn.execute('INSERT INTO "基金基本信息" VALUES ("000002", "测试基金", "测试基金二")')
    conn.commit()
    conn.close()

    resolver = EntityResolver(db_path)

    assert resolver.resolve_fund_code("测试基金") is None
```

Add `tests/unit/test_text_to_sql_tool.py`:

```python
import sqlite3

from src.agentic.types import AnswerConstraints, QuestionPlan, TimeScope
from src.financial_sql.text_to_sql_tool import TextToSQLEvidenceTool


def test_tool_returns_sql_evidence_for_latest_industry(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE "A股公司行业划分表" ("股票代码" TEXT, "交易日期" TEXT, "行业划分标准" TEXT, "一级行业名称" TEXT, "二级行业名称" TEXT)')
    conn.execute('INSERT INTO "A股公司行业划分表" VALUES ("000637", "20200101", "申万行业分类", "化工", "石油化工")')
    conn.execute('INSERT INTO "A股公司行业划分表" VALUES ("000637", "20211231", "申万行业分类", "化工", "炼油化工")')
    conn.commit()
    conn.close()

    plan = QuestionPlan(
        route="text_to_sql",
        task_type="latest_record_lookup",
        entities={"stock_codes": ["000637"], "industry_standard": "申万行业分类"},
        time_scope=TimeScope(kind="latest", value=None, date_column="交易日期"),
        formula=None,
        evidence_need=["sql_result"],
        sub_questions=[],
        answer_constraints=AnswerConstraints(output_type="text"),
        reason="latest industry",
    )

    package = TextToSQLEvidenceTool(db_path).query(plan, "question")

    assert package.path == "text_to_sql"
    assert package.evidences[0].metadata["row_count"] == 1
    assert "炼油化工" in package.evidences[0].content
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/unit/test_entity_resolver.py tests/unit/test_text_to_sql_tool.py -v
```

Expected: FAIL with missing modules.

- [ ] **Step 3: Implement entity resolver**

Create `src/financial_sql/entity_resolver.py`:

```python
from __future__ import annotations

from pathlib import Path
import sqlite3


class EntityResolver:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def resolve_fund_code(self, fund_name: str) -> str | None:
        sql = '''
        SELECT DISTINCT "基金代码"
        FROM "基金基本信息"
        WHERE "基金简称" = ? OR "基金全称" = ? OR "基金简称" LIKE ? OR "基金全称" LIKE ?
        '''
        pattern = f"%{fund_name}%"
        rows = self._fetch_values(sql, (fund_name, fund_name, pattern, pattern))
        return rows[0] if len(rows) == 1 else None

    def resolve_stock_code(self, stock_name: str) -> str | None:
        sql = '''
        SELECT DISTINCT "股票代码"
        FROM "基金股票持仓明细"
        WHERE "股票名称" = ? OR "股票名称" LIKE ?
        '''
        rows = self._fetch_values(sql, (stock_name, f"%{stock_name}%"))
        return rows[0] if len(rows) == 1 else None

    def _fetch_values(self, sql: str, params: tuple[str, ...]) -> list[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = [str(row[0]) for row in conn.execute(sql, params).fetchall()]
            return rows
        finally:
            conn.close()
```

- [ ] **Step 4: Implement SQL evidence tool for first query families**

Create `src/financial_sql/text_to_sql_tool.py`:

```python
from __future__ import annotations

from pathlib import Path
import json

from src.agentic.types import Evidence, EvidencePackage, QuestionPlan
from src.financial_sql.sql_executor import SQLiteQueryExecutor


class TextToSQLEvidenceTool:
    def __init__(self, db_path: str | Path, max_rows: int = 50) -> None:
        self.db_path = Path(db_path)
        self.executor = SQLiteQueryExecutor(self.db_path, default_limit=max_rows)

    def query(self, plan: QuestionPlan, question: str) -> EvidencePackage:
        sql = self._compile_sql(plan)
        result = self.executor.execute(sql)
        metadata = {
            "sql": result.sql,
            "database": str(self.db_path),
            "columns": result.columns,
            "row_count": result.row_count,
            "status": result.status,
            "error": result.error,
            "formula": plan.formula,
            "time_scope": plan.time_scope.to_dict(),
        }
        evidence = Evidence(
            evidence_id="sql_result_1",
            evidence_type="sql_result",
            source_type="db",
            content=json.dumps(result.rows, ensure_ascii=False),
            source=str(self.db_path),
            metadata=metadata,
        )
        return EvidencePackage(path="text_to_sql", question=question, evidences=[evidence], metadata={"status": result.status})

    def _compile_sql(self, plan: QuestionPlan) -> str:
        if plan.task_type == "latest_record_lookup":
            stock_code = plan.entities["stock_codes"][0]
            standard = plan.entities["industry_standard"]
            return f'''
            SELECT "股票代码", "交易日期", "行业划分标准", "一级行业名称", "二级行业名称"
            FROM "A股公司行业划分表"
            WHERE "股票代码" = '{stock_code}'
              AND "行业划分标准" = '{standard}'
              AND "交易日期" = (
                SELECT MAX("交易日期")
                FROM "A股公司行业划分表"
                WHERE "股票代码" = '{stock_code}'
                  AND "行业划分标准" = '{standard}'
              )
            '''
        raise ValueError(f"Unsupported task_type: {plan.task_type}")
```

- [ ] **Step 5: Run unit tests**

Run:

```powershell
pytest tests/unit/test_entity_resolver.py tests/unit/test_text_to_sql_tool.py -v
```

Expected: PASS.

- [ ] **Step 6: Add dataset integration test**

Add `tests/integration/test_financial_sql_dataset.py`:

```python
from pathlib import Path

import pytest

from src.agentic.planner import FinancialQuestionPlanner
from src.financial_sql.text_to_sql_tool import TextToSQLEvidenceTool


DATASET_DB = Path(__file__).resolve().parents[3] / "bs_challenge_financial_14b_dataset" / "dataset" / "博金杯比赛数据.db"


@pytest.mark.integration
def test_latest_industry_query_against_dataset():
    if not DATASET_DB.exists():
        pytest.skip("Bosera dataset DB is not available")

    planner = FinancialQuestionPlanner()
    plan = planner.plan("我想知道股票000637在申万行业分类下的二级行业是什么？用最新的数据。")
    package = TextToSQLEvidenceTool(DATASET_DB).query(plan, "question")

    assert package.evidences[0].metadata["status"] == "success"
    assert package.evidences[0].metadata["row_count"] >= 1
```

- [ ] **Step 7: Run dataset integration test**

Run:

```powershell
pytest tests/integration/test_financial_sql_dataset.py -v
```

Expected: PASS when dataset DB exists; SKIP when DB is missing.

- [ ] **Step 8: Commit**

```powershell
git add src/financial_sql/entity_resolver.py src/financial_sql/text_to_sql_tool.py tests/unit/test_entity_resolver.py tests/unit/test_text_to_sql_tool.py tests/integration/test_financial_sql_dataset.py
git commit -m "feat: add SQL evidence path"
```

## Task 6: Prospectus TXT Evidence Baseline

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/src/prospectus_evidence/__init__.py`
- Create: `MODULAR-RAG-MCP-SERVER/src/prospectus_evidence/txt_loader.py`
- Create: `MODULAR-RAG-MCP-SERVER/src/prospectus_evidence/evidence_tool.py`
- Create: `MODULAR-RAG-MCP-SERVER/src/prospectus_evidence/element_docstore.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_prospectus_txt_loader.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_prospectus_evidence_tool.py`

- [ ] **Step 1: Write failing TXT loader tests**

Add `tests/unit/test_prospectus_txt_loader.py`:

```python
from src.prospectus_evidence.txt_loader import ProspectusTxtLoader


def test_loads_txt_and_preserves_table_placeholder(tmp_path):
    path = tmp_path / "abc.txt"
    path.write_text("公司名称\n<|TABLE_0001_0000.xlsx|>\n主营业务为软件开发。", encoding="utf-8")

    doc = ProspectusTxtLoader().load(path)

    assert doc.id.startswith("txt_")
    assert doc.metadata["doc_type"] == "prospectus_txt"
    assert "<|TABLE_0001_0000.xlsx|>" in doc.text
    assert doc.metadata["table_placeholders"] == ["TABLE_0001_0000.xlsx"]
```

Add `tests/unit/test_prospectus_evidence_tool.py`:

```python
from src.core.types import RetrievalResult
from src.prospectus_evidence.evidence_tool import ProspectusEvidenceTool


class FakeSearch:
    def search(self, query, top_k, filters=None, trace=None, return_details=False):
        return [
            RetrievalResult(
                chunk_id="chunk-1",
                score=0.9,
                text="主营业务为软件开发。<|TABLE_0001_0000.xlsx|>",
                metadata={"source_path": "a.txt", "chunk_index": 0},
            )
        ]


def test_wraps_retrieval_results_and_marks_table_placeholder():
    tool = ProspectusEvidenceTool(search=FakeSearch())

    package = tool.query("主营业务是什么", top_k=3)

    evidence = package.evidences[0]
    assert evidence.source_type == "txt"
    assert evidence.metadata["raw_table_unavailable"] is True
    assert evidence.metadata["table_placeholders"] == ["TABLE_0001_0000.xlsx"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/unit/test_prospectus_txt_loader.py tests/unit/test_prospectus_evidence_tool.py -v
```

Expected: FAIL with missing modules.

- [ ] **Step 3: Implement TXT loader and evidence wrapper**

Create `src/prospectus_evidence/__init__.py`:

```python
"""Prospectus evidence retrieval helpers."""
```

Create `src/prospectus_evidence/txt_loader.py`:

```python
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from src.core.types import Document


class ProspectusTxtLoader:
    def load(self, file_path: str | Path) -> Document:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        placeholders = re.findall(r"<\|(TABLE_[^|]+)\|>", text)
        return Document(
            id=f"txt_{digest}",
            text=text,
            metadata={
                "source_path": str(path),
                "doc_type": "prospectus_txt",
                "table_placeholders": placeholders,
            },
        )
```

Create `src/prospectus_evidence/evidence_tool.py`:

```python
from __future__ import annotations

import re

from src.agentic.types import Evidence, EvidencePackage


class ProspectusEvidenceTool:
    def __init__(self, search) -> None:
        self.search = search

    def query(self, question: str, top_k: int = 5) -> EvidencePackage:
        results = self.search.search(query=question, top_k=top_k, filters=None, trace=None, return_details=False)
        evidences = []
        for index, result in enumerate(results, start=1):
            placeholders = re.findall(r"<\|(TABLE_[^|]+)\|>", result.text)
            evidences.append(
                Evidence(
                    evidence_id=f"prospectus_{index}",
                    evidence_type="table" if placeholders else "text",
                    source_type="txt",
                    content=result.text,
                    source=result.metadata.get("source_path", ""),
                    score=result.score,
                    metadata={
                        "chunk_id": result.chunk_id,
                        "chunk_index": result.metadata.get("chunk_index"),
                        "table_placeholders": placeholders,
                        "raw_table_unavailable": bool(placeholders),
                    },
                )
            )
        return EvidencePackage(path="pdf_rag", question=question, evidences=evidences)
```

Create `src/prospectus_evidence/element_docstore.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RawElementPayload:
    element_id: str
    raw_content: str
    raw_format: str
    metadata: dict


class ElementDocstore:
    def get(self, element_id: str) -> Optional[RawElementPayload]:
        return None
```

- [ ] **Step 4: Run prospectus tests**

Run:

```powershell
pytest tests/unit/test_prospectus_txt_loader.py tests/unit/test_prospectus_evidence_tool.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/prospectus_evidence tests/unit/test_prospectus_txt_loader.py tests/unit/test_prospectus_evidence_tool.py
git commit -m "feat: add prospectus TXT evidence baseline"
```

## Task 7: Merger, Verifier, and Formatting

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/src/agentic/merger.py`
- Create: `MODULAR-RAG-MCP-SERVER/src/agentic/verifier.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_financial_merger_verifier.py`

- [ ] **Step 1: Write failing merger/verifier tests**

Add `tests/unit/test_financial_merger_verifier.py`:

```python
from src.agentic.merger import EvidenceMerger
from src.agentic.types import AnswerConstraints, Evidence, EvidencePackage, QuestionPlan, TimeScope
from src.agentic.verifier import FinancialVerifier


def test_merger_preserves_evidence_ids():
    sql = EvidencePackage("text_to_sql", "q", [Evidence("sql-1", "sql_result", "db", "{}", "db")])
    pdf = EvidencePackage("pdf_rag", "q", [Evidence("txt-1", "text", "txt", "content", "a.txt")])

    merged = EvidenceMerger().merge([sql, pdf])

    assert [item.evidence_id for item in merged] == ["sql-1", "txt-1"]


def test_verifier_marks_placeholder_table_as_partial():
    plan = QuestionPlan(
        route="pdf_rag",
        task_type="financial_table_fact",
        entities={},
        time_scope=TimeScope("not_applicable", None),
        formula=None,
        evidence_need=["table"],
        sub_questions=[],
        answer_constraints=AnswerConstraints(output_type="number"),
        reason="table fact",
    )
    evidence = Evidence("txt-1", "table", "txt", "<|TABLE_0001_0000.xlsx|>", "a.txt", metadata={"raw_table_unavailable": True})

    report = FinancialVerifier().verify(plan, [evidence])

    assert report.status == "partial"
    assert "raw_table" in report.missing_evidence


def test_percentage_formatting_preserves_percent_sign():
    verifier = FinancialVerifier()

    assert verifier.format_value(1.2345, AnswerConstraints(output_type="percentage", precision=2)) == "1.23%"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/unit/test_financial_merger_verifier.py -v
```

Expected: FAIL with missing modules.

- [ ] **Step 3: Implement merger and verifier**

Create `src/agentic/merger.py`:

```python
from __future__ import annotations

from src.agentic.types import Evidence, EvidencePackage


class EvidenceMerger:
    def merge(self, packages: list[EvidencePackage]) -> list[Evidence]:
        seen: set[str] = set()
        merged: list[Evidence] = []
        for package in packages:
            for evidence in package.evidences:
                if evidence.evidence_id in seen:
                    continue
                seen.add(evidence.evidence_id)
                merged.append(evidence)
        return merged
```

Create `src/agentic/verifier.py`:

```python
from __future__ import annotations

from typing import Any

from src.agentic.types import AnswerConstraints, Evidence, QuestionPlan, VerificationReport


class FinancialVerifier:
    def verify(self, plan: QuestionPlan, evidences: list[Evidence]) -> VerificationReport:
        if not evidences:
            return VerificationReport("insufficient", [], [], list(plan.evidence_need), ["No evidence returned"])

        missing: list[str] = []
        notes: list[str] = []
        status = "pass"

        if plan.task_type == "financial_table_fact":
            if any(item.metadata.get("raw_table_unavailable") for item in evidences):
                status = "partial"
                missing.append("raw_table")
                notes.append("Retrieved table placeholder but raw table payload is unavailable")

        return VerificationReport(
            status=status,
            selected_evidence_ids=[item.evidence_id for item in evidences],
            conflicts=[],
            missing_evidence=missing,
            notes=notes,
        )

    def format_value(self, value: Any, constraints: AnswerConstraints) -> str:
        if constraints.output_type == "percentage":
            number = float(value)
            precision = constraints.precision if constraints.precision is not None else 2
            return f"{number:.{precision}f}%"
        if constraints.precision is not None and isinstance(value, (int, float)):
            return f"{float(value):.{constraints.precision}f}"
        return str(value)
```

- [ ] **Step 4: Run merger/verifier tests**

Run:

```powershell
pytest tests/unit/test_financial_merger_verifier.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/agentic/merger.py src/agentic/verifier.py tests/unit/test_financial_merger_verifier.py
git commit -m "feat: add financial evidence verifier"
```

## Task 8: Financial Orchestrator

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/src/agentic/orchestrator.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_financial_orchestrator.py`

- [ ] **Step 1: Write failing orchestrator tests**

Add `tests/unit/test_financial_orchestrator.py`:

```python
from src.agentic.orchestrator import FinancialOrchestrator
from src.agentic.types import Evidence, EvidencePackage


class FakePlanner:
    def plan(self, question):
        from src.agentic.types import AnswerConstraints, QuestionPlan, TimeScope
        return QuestionPlan("text_to_sql", "latest_record_lookup", {"stock_codes": ["000637"]}, TimeScope("latest", None), None, ["sql_result"], [], AnswerConstraints(), "test")


class FakeSQLTool:
    def query(self, plan, question):
        return EvidencePackage("text_to_sql", question, [Evidence("sql-1", "sql_result", "db", '[{"二级行业名称": "炼油化工"}]', "db")])


def test_orchestrator_answers_sql_only_question():
    orchestrator = FinancialOrchestrator(planner=FakePlanner(), sql_tool=FakeSQLTool(), prospectus_tool=None)

    result = orchestrator.answer("question")

    assert result["verification_report"]["status"] == "pass"
    assert result["sources"][0]["evidence_id"] == "sql-1"
    assert "炼油化工" in result["answer"]
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
pytest tests/unit/test_financial_orchestrator.py -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement orchestrator**

Create `src/agentic/orchestrator.py`:

```python
from __future__ import annotations

from src.agentic.merger import EvidenceMerger
from src.agentic.verifier import FinancialVerifier


class FinancialOrchestrator:
    def __init__(self, planner, sql_tool, prospectus_tool) -> None:
        self.planner = planner
        self.sql_tool = sql_tool
        self.prospectus_tool = prospectus_tool
        self.merger = EvidenceMerger()
        self.verifier = FinancialVerifier()

    def answer(self, question: str) -> dict:
        plan = self.planner.plan(question)
        packages = []
        if plan.route == "text_to_sql":
            packages.append(self.sql_tool.query(plan, question))
        elif plan.route == "pdf_rag":
            packages.append(self.prospectus_tool.query(question))
        elif plan.route == "hybrid":
            packages.append(self.sql_tool.query(plan, question))
            if self.prospectus_tool is not None:
                packages.append(self.prospectus_tool.query(question))

        evidences = self.merger.merge(packages)
        report = self.verifier.verify(plan, evidences)
        answer = self._build_answer(evidences)
        return {
            "answer": answer,
            "sources": [item.to_dict() for item in evidences],
            "question_plan": plan.to_dict(),
            "verification_report": report.to_dict(),
        }

    def _build_answer(self, evidences) -> str:
        if not evidences:
            return "未找到足够证据。"
        return "\n".join(item.content for item in evidences)
```

- [ ] **Step 4: Run orchestrator tests**

Run:

```powershell
pytest tests/unit/test_financial_orchestrator.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/agentic/orchestrator.py tests/unit/test_financial_orchestrator.py
git commit -m "feat: add financial orchestrator"
```

## Task 9: Financial Evaluation Runner

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/src/observability/evaluation/financial_eval_runner.py`
- Test: `MODULAR-RAG-MCP-SERVER/tests/unit/test_financial_eval_runner.py`

- [ ] **Step 1: Write failing evaluation tests**

Add `tests/unit/test_financial_eval_runner.py`:

```python
from src.observability.evaluation.financial_eval_runner import FinancialEvalRunner


class FakeAgent:
    def answer(self, question):
        return {
            "question_plan": {"route": "text_to_sql", "hybrid_mode": None, "entities": {"stock_codes": ["000637"]}, "formula": None},
            "verification_report": {"status": "pass"},
            "answer": "炼油化工",
            "sources": [],
        }


def test_eval_runner_reports_route_and_status_accuracy():
    cases = [
        {
            "id": "case-1",
            "question": "q",
            "expected_route": "text_to_sql",
            "expected_status": "pass",
            "task_family": "latest-record lookup",
        }
    ]
    result = FinancialEvalRunner(agent=FakeAgent()).run(cases)

    assert result["count"] == 1
    assert result["route_accuracy"] == 1.0
    assert result["verification_status_accuracy"] == 1.0
    assert result["families"]["latest-record lookup"]["count"] == 1
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
pytest tests/unit/test_financial_eval_runner.py -v
```

Expected: FAIL with missing module.

- [ ] **Step 3: Implement evaluation runner**

Create `src/observability/evaluation/financial_eval_runner.py`:

```python
from __future__ import annotations

from collections import defaultdict
from typing import Any


class FinancialEvalRunner:
    def __init__(self, agent) -> None:
        self.agent = agent

    def run(self, cases: list[dict[str, Any]]) -> dict[str, Any]:
        route_hits = 0
        status_hits = 0
        families: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0})

        for case in cases:
            result = self.agent.answer(case["question"])
            plan = result["question_plan"]
            report = result["verification_report"]
            if plan.get("route") == case.get("expected_route"):
                route_hits += 1
            if report.get("status") == case.get("expected_status"):
                status_hits += 1
            family = case.get("task_family", "unknown")
            families[family]["count"] += 1

        count = len(cases)
        return {
            "count": count,
            "route_accuracy": route_hits / count if count else 0.0,
            "verification_status_accuracy": status_hits / count if count else 0.0,
            "families": dict(families),
        }
```

- [ ] **Step 4: Run evaluation tests**

Run:

```powershell
pytest tests/unit/test_financial_eval_runner.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/observability/evaluation/financial_eval_runner.py tests/unit/test_financial_eval_runner.py
git commit -m "feat: add financial evaluation runner"
```

## Task 10: CLI Smoke Entry Point

**Files:**
- Create: `MODULAR-RAG-MCP-SERVER/scripts/financial_query.py`
- Test: run focused smoke command against a temporary or dataset DB

- [ ] **Step 1: Create CLI script**

Create `scripts/financial_query.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from src.agentic.orchestrator import FinancialOrchestrator
from src.agentic.planner import FinancialQuestionPlanner
from src.financial_sql.text_to_sql_tool import TextToSQLEvidenceTool


def main() -> None:
    parser = argparse.ArgumentParser(description="Run financial Agentic RAG query")
    parser.add_argument("question")
    parser.add_argument("--db", required=True, help="Path to Bosera SQLite database")
    args = parser.parse_args()

    agent = FinancialOrchestrator(
        planner=FinancialQuestionPlanner(),
        sql_tool=TextToSQLEvidenceTool(Path(args.db)),
        prospectus_tool=None,
    )
    result = agent.answer(args.question)
    print(result["answer"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run CLI smoke**

Run:

```powershell
python scripts/financial_query.py "我想知道股票000637在申万行业分类下的二级行业是什么？用最新的数据。" --db "..\bs_challenge_financial_14b_dataset\dataset\博金杯比赛数据.db"
```

Expected: output includes JSON-like SQL evidence content with one latest industry record, or a clear SQL error if the dataset DB is unavailable.

- [ ] **Step 3: Run full focused suite**

Run:

```powershell
pytest tests/unit/test_agentic_types.py tests/unit/test_financial_planner.py tests/unit/test_schema_registry.py tests/unit/test_formula_registry.py tests/unit/test_entity_resolver.py tests/unit/test_sql_safety.py tests/unit/test_sql_executor.py tests/unit/test_text_to_sql_tool.py tests/unit/test_financial_sql_boundary_cases.py tests/unit/test_prospectus_txt_loader.py tests/unit/test_prospectus_evidence_tool.py tests/unit/test_financial_merger_verifier.py tests/unit/test_financial_orchestrator.py tests/unit/test_financial_eval_runner.py -v
```

Expected: PASS.

- [ ] **Step 4: Validate OpenSpec remains valid**

Run from `D:\workspace\financial-agentic-rag`:

```powershell
openspec validate develop-financial-agentic-rag
```

Expected: `Change 'develop-financial-agentic-rag' is valid`.

- [ ] **Step 5: Commit**

```powershell
git add scripts/financial_query.py
git commit -m "feat: add financial query CLI smoke entrypoint"
```

## Task 11: Documentation and OpenSpec Task Sync

**Files:**
- Modify: `D:\workspace\financial-agentic-rag\docs\financial-agentic-rag-design.md`
- Modify: `D:\workspace\financial-agentic-rag\openspec\changes\develop-financial-agentic-rag\tasks.md`

- [ ] **Step 1: Add implementation notes to design doc**

Append a short section to `docs/financial-agentic-rag-design.md`:

```markdown
## 14. Implementation Notes

The first implementation pass is additive inside `MODULAR-RAG-MCP-SERVER/src`.
It starts with deterministic planning, schema/formula registries, safe SQLite execution,
TXT prospectus evidence wrapping, verifier behavior, and evaluation scaffolding.

Native PDF table recovery and full `financial_qa` MCP exposure remain later extension points.
```

- [ ] **Step 2: Mark completed OpenSpec tasks**

In `openspec/changes/develop-financial-agentic-rag/tasks.md`, mark only the tasks actually completed during execution. Do not mark a task complete unless its focused tests passed.

Example checkbox edit:

```markdown
- [x] 1.2 Define shared dataclasses for `QuestionPlan`, `Evidence`, `EvidencePackage`, and `VerificationReport`
```

- [ ] **Step 3: Run OpenSpec status**

Run:

```powershell
openspec status --change develop-financial-agentic-rag
```

Expected: artifacts remain complete.

- [ ] **Step 4: Commit documentation and task status**

From a git root that tracks these files, run:

```powershell
git add docs/financial-agentic-rag-design.md openspec/changes/develop-financial-agentic-rag/tasks.md
git commit -m "docs: record financial agent implementation progress"
```

If the outer workspace is not a git repository, record the completed task status in the final implementation summary instead of committing.

## Self-Review

- Spec coverage: This plan covers shared contracts, planning, entity/time/formula handling, safe SQL evidence, prospectus TXT evidence, hybrid orchestration, verifier behavior, answer formatting, and evaluation scaffolding. Native PDF raw table extraction is intentionally represented by an `ElementDocstore` interface because the current spec allows TXT baseline first and element-aware extension later.
- Placeholder scan: The plan contains no unfinished placeholders or copy-forward task references.
- Type consistency: `QuestionPlan`, `Evidence`, `EvidencePackage`, `TimeScope`, `AnswerConstraints`, and `VerificationReport` signatures are introduced in Task 1 and reused consistently in later tasks.
