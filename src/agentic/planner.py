from __future__ import annotations

import re
from dataclasses import dataclass

from src.agentic.types import AnswerConstraints, QuestionPlan, TimeScope


@dataclass(frozen=True)
class _Quarter:
    label: str
    start_suffix: str
    end_suffix: str
    report_type: str


_QUARTERS = {
    "Q1": _Quarter("Q1", "0101", "0331", "一季报"),
    "Q2": _Quarter("Q2", "0401", "0630", "半年度报告"),
    "Q3": _Quarter("Q3", "0701", "0930", "三季报"),
    "Q4": _Quarter("Q4", "1001", "1231", "季报"),
}


LEGACY_ENTITY_WORDS = {
    "fund": ["基金", "鍩洪噾", "熀閲?"],
    "stock": ["股票", "鑲＄エ", "偂绁?"],
}

LEGACY_YEAR_MARKERS = r"年|年度|骞|[一二三四]季度| Q[1-4]|Q[1-4]|$"


class FinancialQuestionPlanner:
    """Rule-first financial question planner.

    The planner intentionally uses deterministic string and regex rules. It is
    a lightweight contract producer for downstream SQL/prospectus components.
    """

    def plan(self, question: str) -> QuestionPlan:
        entities = self._extract_entities(question)
        formula = self._extract_formula(question)
        formula_params = self._extract_formula_params(question, formula)
        raw_formula_text = self._extract_raw_formula_text(question, formula)
        constraints = self._extract_answer_constraints(question, formula)
        route = self._classify_route(question)
        task_type = self._detect_task_type(question, route, formula, constraints, entities)
        time_scope = self._extract_time_scope(question, task_type)
        evidence_need = self._evidence_need(route)
        sub_questions = self._build_sub_questions(question, route, task_type)
        hybrid_mode = "sql_first" if route == "hybrid" else None

        return QuestionPlan(
            route=route,
            hybrid_mode=hybrid_mode,
            task_type=task_type,
            entities=entities,
            time_scope=time_scope,
            formula=formula,
            evidence_need=evidence_need,
            sub_questions=sub_questions,
            answer_constraints=constraints,
            reason=self._reason(route, task_type),
            formula_params=formula_params,
            raw_formula_text=raw_formula_text,
        )

    def _classify_route(self, question: str) -> str:
        asks_prospectus = self._mentions_prospectus_disclosure(question)
        asks_database = self._mentions_database_fact(question)
        if asks_prospectus and self._mentions_uploaded_document_reference(question):
            return "pdf_rag"
        if asks_prospectus and asks_database:
            return "hybrid"
        if self._is_holding_return_hybrid(question):
            return "hybrid"
        if asks_prospectus:
            return "pdf_rag"
        return "text_to_sql"

    def _extract_entities(self, question: str) -> dict[str, object]:
        entities: dict[str, object] = {}
        stock_like_codes = re.findall(r"(?<!\d)(?:00|30|60|68)\d{4}(?!\d)", question)
        fund_context_codes = self._extract_contextual_codes(
            question, LEGACY_ENTITY_WORDS["fund"]
        )
        stock_context_codes = self._extract_contextual_codes(
            question, LEGACY_ENTITY_WORDS["stock"]
        )
        fund_codes = self._unique(
            re.findall(r"(?<!\d)(?:5[01]\d{4}|16\d{4})(?!\d)", question)
            + fund_context_codes
        )
        stock_codes = [
            code
            for code in stock_like_codes
            if code not in fund_context_codes or code in stock_context_codes
        ]
        dates = re.findall(r"(?<!\d)20\d{6}(?!\d)", question)
        years = re.findall(
            rf"(?<!\d)(20\d{{2}})(?={LEGACY_YEAR_MARKERS})",
            question,
        )
        quarters = self._extract_quarters(question)
        industry_standard = self._normalize_industry_standard(question)
        company_names = self._extract_company_names(question)
        fund_names = self._extract_fund_names(question)
        stock_names = self._extract_stock_names(question, stock_codes, company_names, fund_names)
        level1_industry = self._extract_level_industry(question, "一级行业")
        level2_industry = self._extract_level_industry(question, "二级行业")

        if stock_codes:
            entities["stock_codes"] = stock_codes
        if fund_codes:
            entities["fund_codes"] = fund_codes
            entities["fund_codes_require_lookup"] = False
        if fund_names:
            entities["fund_names"] = fund_names
            if not fund_codes:
                entities["fund_names_require_lookup"] = True
        if company_names:
            entities["company_names"] = company_names
            if self._mentions_stock_code_lookup(question) and not stock_codes:
                entities["stock_names"] = company_names
                entities["stock_names_require_lookup"] = True
        if stock_names:
            entities["stock_names"] = stock_names
            if not stock_codes:
                entities["stock_names_require_lookup"] = True
        if dates:
            entities["dates"] = dates
        if years:
            entities["years"] = sorted(set(years), key=years.index)
        if quarters:
            entities["quarters"] = quarters
        if industry_standard:
            entities["industry_standard"] = industry_standard
        if level1_industry:
            entities["level1_industry"] = level1_industry
        if level2_industry:
            entities["level2_industry"] = level2_industry
        return entities

    def _extract_time_scope(self, question: str, task_type: str) -> TimeScope:
        dates = re.findall(r"(?<!\d)(20\d{6})(?!\d)", question)
        years = re.findall(
            rf"(?<!\d)(20\d{{2}})(?={LEGACY_YEAR_MARKERS})",
            question,
        )
        quarters = self._extract_quarters(question)

        if self._mentions_latest(question) and self._mentions_regular_report(question):
            year = years[0] if years else None
            return TimeScope(
                kind="per_entity_latest_report",
                value=year,
                start=f"{year}0101" if year else None,
                end=f"{year}1231" if year else None,
                report_types=["定期报告"],
                date_column="截止日期",
                per_entity_latest=True,
            )

        if self._mentions_latest(question):
            return TimeScope(kind="latest", value=None, date_column="交易日期")

        if quarters:
            year = self._year_for_period(question, dates, years)
            quarter = _QUARTERS[quarters[0]]
            return TimeScope(
                kind="report_period",
                value=f"{year}{quarter.label}" if year else quarter.label,
                start=f"{year}{quarter.start_suffix}" if year else None,
                end=f"{year}{quarter.end_suffix}" if year else None,
                report_types=[quarter.report_type],
                date_column="持仓日期",
            )

        if self._mentions_report_period(question) or "20210630" in dates:
            year = self._year_for_period(question, dates, years)
            return TimeScope(
                kind="report_period",
                value=f"{year}Q2" if year else "Q2",
                start=f"{year}0401" if year else None,
                end=f"{year}0630" if year else "20210630",
                report_types=["半年度报告"],
                date_column="持仓日期",
            )

        if dates:
            return TimeScope(kind="trading_date", value=dates[0], date_column="交易日期")

        if years:
            year = years[0]
            kind = "annual_range"
            return TimeScope(
                kind=kind,
                value=year,
                start=f"{year}0101",
                end=f"{year}1231",
                date_column="交易日期" if task_type != "report_period_query" else "持仓日期",
            )

        if task_type in {"disclosure_fact", "stock_code_lookup"}:
            return TimeScope(kind="not_applicable", value=None)
        return TimeScope(kind="not_specified", value=None)

    def _detect_task_type(
        self,
        question: str,
        route: str,
        formula: str | None,
        constraints: AnswerConstraints,
        entities: dict[str, object],
    ) -> str:
        if route == "hybrid":
            return "hybrid"
        if route == "pdf_rag":
            return "disclosure_fact"
        if self._mentions_stock_code_lookup(question) and (
            entities.get("company_names") or entities.get("stock_names")
        ):
            return "stock_code_lookup"
        if constraints.top_n or self._has_ranking_word(question):
            if formula:
                return "quote_formula"
            return "ranking"
        if constraints.count or constraints.sum or constraints.average:
            return "aggregate_statistics"
        if self._mentions_latest(question):
            return "latest_record_lookup"
        if self._mentions_report_period(question) or self._extract_quarters(question):
            return "report_period_query"
        if formula:
            return "quote_formula"
        return "point_lookup"

    def _extract_formula(self, question: str) -> str | None:
        rules = [
            ("limit_up_days", ["涨停", "娑ㄥ仠", "9.8%", "9.8 percent"]),
            (
                "open_above_previous_close_days",
                [
                    "开盘价高于昨收盘价",
                    "开盘价高于前收盘价",
                    "寮€鐩樹环楂樹簬鏄ㄦ敹鐩樹环",
                    "寮€鐩樹环楂樹簬鍓嶆敹鐩樹环",
                ],
            ),
            (
                "low_volume_days",
                [
                    "低于全年平均成交量",
                    "低于年平均成交量",
                    "低成交量",
                    "浣庝簬鍏ㄥ勾骞冲潎鎴愪氦閲?",
                    "浣庝簬骞村钩鍧囨垚浜ら噺",
                    "浣庢垚浜ら噺",
                ],
            ),
            ("annualized_return", ["年化收益率", "年化回报", "骞村寲鏀剁泭鐜?", "骞村寲鍥炴姤"]),
            (
                "price_range",
                ["最高价和最低价", "最高价与最低价", "价差", "鏈€楂樹环鍜屾渶浣庝环", "鏈€楂樹环涓庢渶浣庝环", "浠峰樊"],
            ),
            (
                "daily_percent_change",
                ["涨跌幅", "娑ㄨ穼骞", "百分涨跌", "鐧惧垎娑ㄨ穼", "percentage change"],
            ),
            ("annualized_return", ["annualized return"]),
        ]
        for identifier, markers in rules:
            if any(marker.lower() in question.lower() for marker in markers):
                return identifier
        if self._has_any(question, ["收盘价", "鏀剁洏浠?"]) and self._has_any(
            question, ["昨收", "前收", "鏄ㄦ敹", "鍓嶆敹"]
        ):
            return "daily_percent_change"
        if self._extract_raw_formula_text(question, None):
            return "unknown"
        return None

    def _extract_formula_params(self, question: str, formula: str | None) -> dict[str, object]:
        if formula != "limit_up_days":
            return {}
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", question)
        if not match:
            return {}
        return {"threshold": float(match.group(1)) / 100}

    def _extract_raw_formula_text(self, question: str, formula: str | None) -> str | None:
        match = re.search(r"公式(?:为|是)?(.+?)(?:[。？?]|$)", question)
        if match:
            return match.group(1).strip(" ：:，,。")
        if formula == "limit_up_days":
            match = re.search(r"涨停定义为(.+?)(?:[。？?]|$)", question)
            if match:
                return match.group(1).strip(" ：:，,。")
        return None

    def _extract_answer_constraints(
        self, question: str, formula: str | None
    ) -> AnswerConstraints:
        top_n = self._extract_top_n(question)
        precision = self._extract_precision(question)
        output_type = "text"
        if formula in {
            "daily_percent_change",
            "limit_up_days",
            "annualized_return",
        } or self._has_any(
            question, ["百分", "鐧惧垎", "%", "收益率", "鏀剁泭鐜", "涨跌幅", "娑ㄨ穼骞"]
        ):
            output_type = "percentage"
        elif self._has_any(
            question, ["多少", "澶氬皯", "几", "鍑?", "合计", "鍚堣", "平均", "骞冲潎", "数量", "鏁伴噺"]
        ):
            output_type = "number"

        return AnswerConstraints(
            output_type=output_type,
            precision=precision,
            order="desc" if self._has_desc_word(question) else None,
            top_n=top_n,
            count=self._has_any(
                question,
                ["数量", "鏁伴噺", "多少只", "澶氬皯鍙?", "多少个", "澶氬皯涓?", "有几", "鏈夊嚑", "几天", "鍑犲ぉ", "天数", "澶╂暟", "统计", "缁熻"],
            ),
            sum=self._has_any(question, ["合计", "鍚堣", "总和", "鎬诲拰", "求和", "姹傚拰"]),
            average=self._has_any(question, ["平均", "骞冲潎", "均值", "鍧囧€?"]),
        )

    def _evidence_need(self, route: str) -> list[str]:
        if route == "pdf_rag":
            return ["text"]
        if route == "hybrid":
            return ["sql_result", "text"]
        return ["sql_result"]

    def _build_sub_questions(
        self, question: str, route: str, task_type: str
    ) -> list[dict[str, str]]:
        if route != "hybrid":
            return []
        if self._is_holding_return_hybrid(question):
            return [
                {
                    "target_path": "text_to_sql",
                    "question": "Resolve the fund holding stock for the requested report period and rank.",
                },
                {
                    "target_path": "entity_mapping",
                    "mapping": "sql_stock_result_to_prospectus_company_name",
                    "question": "Map the SQL stock result to a prospectus company name.",
                },
                {
                    "target_path": "text_to_sql",
                    "question": "Compute the resolved holding stock return for the requested period.",
                },
            ]
        return [
            {
                "target_path": "text_to_sql",
                "question": "Resolve structured database entities for the hybrid request.",
            },
            {
                "target_path": "entity_mapping",
                "mapping": "sql_stock_result_to_prospectus_company_name",
                "question": "Map the SQL stock result to a prospectus company name.",
            },
            {
                "target_path": "pdf_rag",
                "question": "Retrieve prospectus disclosure evidence for the resolved entity.",
            },
        ]

    def _normalize_industry_standard(self, question: str) -> str | None:
        raw = question.lower()
        if any(term in raw for term in ["申万", "shenwan", "鐢充竾"]):
            return "申万行业分类"
        if any(term in raw for term in ["中信", "citic", "涓俊"]):
            return "中信行业分类"
        return None

    def _extract_quarters(self, question: str) -> list[str]:
        quarters: list[str] = []
        quarter_markers = [
            ("Q1", ["Q1", "一季度", "1季度", "第一季度", "涓€瀛ｅ害"]),
            (
                "Q2",
                ["Q2", "二季度", "2季度", "第二季度", "半年度", "半年报", "20210630", "浜屽搴?", "鍗婂勾搴?", "鍗婂勾鎶?", "鍗婂勾搴︽姤鍛?"],
            ),
            ("Q3", ["Q3", "三季度", "3季度", "第三季度", "涓夊搴?"]),
            ("Q4", ["Q4", "四季度", "4季度", "第四季度", "鍥涘搴?"]),
        ]
        for label, markers in quarter_markers:
            if any(marker in question for marker in markers):
                quarters.append(label)
        return quarters

    def _extract_company_names(self, question: str) -> list[str]:
        legacy_candidates = re.findall(
            r"([\u4e00-\u9fffA-Za-z0-9()（）\uff04]+?\u5042\u6d60\u82a5\u6e41\u95c4\u612c\u53d5\u9359)(?=\u9550)",
            question,
        )
        if legacy_candidates:
            return self._unique([f"{item}?" for item in legacy_candidates])
        candidates = re.findall(
            r"([\u4e00-\u9fffA-Za-z0-9()（）]+?(?:股份有限公司|鑲′唤鏈夐檺鍏徃|偂浠芥湁闄愬叕鍙?))",
            question,
        )
        return self._unique(candidates)

    def _extract_fund_names(self, question: str) -> list[str]:
        legacy_candidates = re.findall(
            r"([\u4e00-\u9fffA-Za-z0-9()（）]+?\u7180\u95b2)(?=\u621d)",
            question,
        )
        if legacy_candidates:
            return self._unique([f"{item}?" for item in legacy_candidates])
        candidates = re.findall(
            r"([\u4e00-\u9fffA-Za-z0-9()（）]+?(?:基金|鍩洪噾|熀閲?))",
            question,
        )
        cleaned = []
        for item in candidates:
            item = re.sub(r"^(我想了解|鎴戞兂浜嗚В|请问|璇烽棶|查询|鏌ヨ|统计|缁熻)", "", item)
            cleaned.append(item)
        return self._unique(cleaned)

    def _extract_stock_names(
        self,
        question: str,
        stock_codes: list[str],
        company_names: list[str],
        fund_names: list[str],
    ) -> list[str]:
        if stock_codes:
            return []
        candidates = []
        for pattern in [
            r"^([\u4e00-\u9fffA-Za-z0-9()（）]{2,12})的",
            r"^([\u4e00-\u9fffA-Za-z0-9()（）]{2,12})股票在20\d{2}",
            r"^([\u4e00-\u9fffA-Za-z0-9()（）]{2,12})在20\d{2}",
            r"^([\u4e00-\u9fffA-Za-z0-9()（）]{2,12})20\d{2}",
        ]:
            match = re.match(pattern, question)
            if match:
                candidates.append(match.group(1))
        cleaned = []
        for candidate in candidates:
            candidate = re.sub(r"(股票在|股票|在)$", "", candidate)
            if candidate in company_names or candidate in fund_names:
                continue
            if candidate in {"基金", "股票", "行业"}:
                continue
            if any(term in candidate for term in ["基金", "行业"]):
                continue
            cleaned.append(candidate)
        return self._unique(cleaned)

    def _extract_contextual_codes(self, question: str, entity_words: list[str]) -> list[str]:
        marker = "|".join(re.escape(word) for word in entity_words)
        before = re.findall(rf"(?:{marker})\s*([0-9]{{6}})", question)
        after = re.findall(rf"([0-9]{{6}})\s*(?:{marker})", question)
        return self._unique(before + after)

    def _extract_level_industry(self, question: str, marker: str) -> str | None:
        pattern = rf"{marker}(?:为|是)?([\u4e00-\u9fffA-Za-z0-9]+?)(?:行业|中|下|的|，|,|。|\?)"
        match = re.search(pattern, question)
        if not match:
            return None
        return match.group(1)

    def _extract_top_n(self, question: str) -> int | None:
        if self._has_any(question, ["\u6e36\u6fb6", "\u69f8\u6fb6"]) and "\u5a11\u3128\u7a7c\u9a9e" in question:
            return 1
        rank_prefix = r"(?:前|第|鍓\?|绗\?|top\s*)"
        arabic = re.search(rf"{rank_prefix}(\d+)", question, re.IGNORECASE)
        if arabic:
            return int(arabic.group(1))
        chinese_digits = {
            "一": 1,
            "涓€": 1,
            "二": 2,
            "浜?": 2,
            "涓?": 2,
            "三": 3,
            "涓?": 3,
            "四": 4,
            "鍥?": 4,
            "五": 5,
            "浜?": 5,
            "六": 6,
            "鍏?": 6,
            "七": 7,
            "涓?": 7,
            "八": 8,
            "鍏?": 8,
            "九": 9,
            "涔?": 9,
            "十": 10,
            "鍗?": 10,
        }
        digit_markers = sorted(chinese_digits, key=len, reverse=True)
        digit_pattern = "|".join(re.escape(marker) for marker in digit_markers)
        match = re.search(rf"{rank_prefix}({digit_pattern})", question)
        if match:
            return chinese_digits[match.group(1)]
        if self._has_any(question, ["最大", "最高", "最多", "第一", "鏈€澶", "鏈€楂", "绗竴"]):
            return 1
        return None

    def _extract_precision(self, question: str) -> int | None:
        if "\u6dc7\u6fc8\u6680\u6d93\u3084\u7d85\u704f\u5fd4\u669f" in question:
            return 2
        digit_match = re.search(r"(?:保留|淇濈暀)(\d+)位", question)
        if digit_match:
            return int(digit_match.group(1))
        chinese_digits = {
            "零": 0,
            "一": 1,
            "两": 2,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "闆?": 0,
            "涓€": 1,
            "涓?": 2,
            "浜?": 2,
            "鍥?": 4,
        }
        match = re.search(r"(?:保留|淇濈暀)([零一两二三四五]|闆?|涓€|涓?|浜?|鍥?)位", question)
        if match:
            return chinese_digits[match.group(1)]
        if self._has_any(question, ["取整", "整数", "鍙栨暣", "鏁存暟"]):
            return 0
        return None

    def _year_for_period(
        self, question: str, dates: list[str], years: list[str]
    ) -> str | None:
        if years:
            return years[0]
        if dates:
            return dates[0][:4]
        match = re.search(r"(20\d{2})", question)
        return match.group(1) if match else None

    def _mentions_latest(self, question: str) -> bool:
        return self._has_any(question, ["最新", "最近", "最晚", "鏈€鏂", "渶鏂", "鏈€杩", "鏈€鏅", "latest"])

    def _mentions_stock_code_lookup(self, question: str) -> bool:
        lower_question = question.lower()
        return any(
            marker in lower_question
            for marker in [
                "股市代码",
                "股票代码",
                "证券代码",
                "股票代号",
                "stock code",
                "ticker",
            ]
        )

    def _mentions_regular_report(self, question: str) -> bool:
        return self._has_any(question, ["定期报告", "年报", "季报", "半年报", "瀹氭湡鎶ュ憡", "骞存姤", "瀛ｆ姤", "鍗婂勾鎶?"])

    def _mentions_report_period(self, question: str) -> bool:
        return any(
            term in question
            for term in ["年报", "季报", "半年报", "半年度报告", "报告期", "持仓日期", "骞存姤", "瀛ｆ姤", "鍗婂勾鎶?", "鍗婂勾搴︽姤鍛?", "鎶ュ憡鏈?", "鎸佷粨鏃ユ湡"]
        )

    def _mentions_prospectus_disclosure(self, question: str) -> bool:
        lower_question = question.lower()
        document_markers = [
            "pdf",
            "prospectus",
            "document",
            "uploaded",
            "upload",
            "文档",
            "文件",
            "上传",
            "招募说明书",
            "招募书",
            "说明书",
        ]
        disclosure_markers = [
            "风险",
            "风险因素",
            "投资策略",
            "投资目标",
            "基金经理",
            "费用",
            "主要内容",
            "主要风险",
            "说了什么",
            "disclosure",
            "risk",
            "risk factors",
            "strategy",
        ]
        if any(marker in lower_question for marker in document_markers):
            return True
        if any(marker in lower_question for marker in disclosure_markers):
            return True
        if "\u5bcc\u9480\u30e4\u7b1f\u9354\u2103" in question:
            return True
        return any(
            term in question
            for term in [
                "主营业务",
                "涓昏惀涓氬姟",
                "富钀ヤ笟鍔?",
                "招股",
                "鎷涜偂",
                "招股书",
                "鎷涜偂涔?",
                "招股说明书",
                "鎷涜偂璇存槑涔?",
                "专利",
                "涓撳埄",
                "供应商",
                "渚涘簲鍟?",
                "客户",
                "瀹㈡埛",
                "募投",
                "鍕熸姇",
                "控股股东",
                "鎺ц偂鑲′笢",
                "披露",
                "鎶湶",
                "风险因素",
                "椋庨櫓鍥犵礌",
            ]
        )

    def _mentions_uploaded_document_reference(self, question: str) -> bool:
        lower_question = question.lower()
        return any(
            marker in lower_question
            for marker in [
                "pdf",
                "uploaded",
                "upload",
                "this document",
                "the document",
                "这份",
                "这个文档",
                "这份文档",
                "上传",
                "上传的",
            ]
        )

    def _mentions_database_fact(self, question: str) -> bool:
        return any(
            term in question
            for term in [
                "股票",
                "鑲＄エ",
                "偂绁?",
                "基金",
                "鍩洪噾",
                "熀閲?",
                "行业分类",
                "琛屼笟鍒嗙被",
                "交易日",
                "浜ゆ槗鏃?",
                "持仓",
                "鎸佷粨",
                "涨跌幅",
                "娑ㄨ穼骞?",
                "收益率",
                "鏀剁泭鐜?",
                "成交量",
                "鎴愪氦閲?",
                "收盘价",
                "鏀剁洏浠?",
                "申万",
                "鐢充竾",
                "中信",
                "涓俊",
            ]
        )

    def _is_holding_return_hybrid(self, question: str) -> bool:
        return (
            self._has_any(question, LEGACY_ENTITY_WORDS["fund"])
            and self._has_any(question, ["持仓", "鎸佷粨"])
            and self._has_any(question, ["涨跌幅", "娑ㄨ穼骞", "收益率", "鏀剁泭鐜", "回报", "鍥炴姤"])
        )

    def _has_ranking_word(self, question: str) -> bool:
        return self._has_any(question, ["最大", "最高", "最多", "排名", "前", "第", "鏈€澶", "鏈€楂", "鎺掑悕", "鍓?", "绗?", "top"])

    def _has_desc_word(self, question: str) -> bool:
        if self._has_any(question, ["\u6e36\u6fb6", "\u69f8\u6fb6"]) and "\u5a11\u3128\u7a7c\u9a9e" in question:
            return True
        return self._has_any(question, ["最大", "最高", "最多", "前", "鏈€澶", "鏈€楂", "鍓?", "top"])

    def _reason(self, route: str, task_type: str) -> str:
        if route == "pdf_rag":
            return "Question asks for prospectus disclosure evidence."
        if route == "hybrid":
            return "Question requires staged database planning before the dependent evidence step."
        return f"Question can be answered from structured financial database rules as {task_type}."

    def _unique(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

    def _has_any(self, question: str, markers: list[str]) -> bool:
        return any(marker in question for marker in markers)
