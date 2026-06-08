from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from src.agentic.merger import EvidenceMerger
from src.agentic.types import Evidence, EvidencePackage, QuestionPlan, VerificationReport
from src.agentic.verifier import FinancialVerifier


class FinancialOrchestrator:
    """Coordinate planning, evidence tools, merging, verification, and answer text."""

    def __init__(
        self,
        planner: Any,
        sql_tool: Any = None,
        prospectus_tool: Any = None,
        merger: EvidenceMerger | None = None,
        verifier: FinancialVerifier | None = None,
    ) -> None:
        self.planner = planner
        self.sql_tool = sql_tool
        self.prospectus_tool = prospectus_tool
        self.merger = merger or EvidenceMerger()
        self.verifier = verifier or FinancialVerifier()

    def answer(self, question: str) -> dict[str, Any]:
        trace: dict[str, Any] = {"tool_sequence": ["plan"], "stages": []}
        plan = self.planner.plan(question)
        trace["stages"].append({"stage": "planning", "route": plan.route, "hybrid_mode": getattr(plan, "hybrid_mode", None)})

        packages, dependency_failure = self._collect_evidence(plan, question, trace)
        evidences = self.merger.merge(packages)
        trace["tool_sequence"].append("merge")
        trace["stages"].append({"stage": "merge", "evidence_count": len(evidences)})

        report = self.verifier.verify(plan, evidences)
        if dependency_failure:
            report = self._with_dependency_failure(report)
        trace["tool_sequence"].append("verify")
        trace["stages"].append({"stage": "verification", "status": report.status})

        answer = self._build_answer(plan, evidences, report)
        trace["tool_sequence"].append("answer")
        trace["stages"].append({"stage": "answer_generation", "answer_length": len(answer)})

        return {
            "answer": answer,
            "sources": [self._to_dict(item) for item in evidences],
            "question_plan": self._to_dict(plan),
            "verification_report": self._to_dict(report),
            "trace": trace,
        }

    def _collect_evidence(
        self,
        plan: QuestionPlan,
        question: str,
        trace: dict[str, Any],
    ) -> tuple[list[EvidencePackage], bool]:
        if plan.route == "text_to_sql":
            return [self._query_sql(plan, question, trace)], False
        if plan.route == "pdf_rag":
            return [self._query_prospectus(question, trace)], False
        if plan.route != "hybrid":
            return [], False
        return self._query_hybrid(plan, question, trace)

    def _query_hybrid(
        self,
        plan: QuestionPlan,
        question: str,
        trace: dict[str, Any],
    ) -> tuple[list[EvidencePackage], bool]:
        steps = self._hybrid_steps(plan)
        packages: list[EvidencePackage] = []
        context: dict[str, Any] = {}

        for index, step in enumerate(steps):
            path = step.get("path") or step.get("target_path")
            if path == "entity_mapping":
                trace["tool_sequence"].append("entity_mapping")
                trace["stages"].append(
                    {
                        "stage": "entity_mapping",
                        "mapping": step.get("mapping"),
                        "context_keys": sorted(context),
                    }
                )
                continue
            sub_question = self._render_sub_question(step.get("question") or question, context)
            package = (
                self._query_sql(plan, sub_question, trace)
                if path == "text_to_sql"
                else self._query_prospectus(sub_question, trace)
            )
            packages.append(package)
            self._update_context(context, package.evidences)

            is_first_step = index == 0 and len(steps) > 1
            if is_first_step and not self._has_dependency_evidence(package.evidences):
                return packages, True

        return packages, False

    def _hybrid_steps(self, plan: QuestionPlan) -> list[dict[str, str]]:
        if getattr(plan, "sub_questions", None):
            return [dict(step) for step in plan.sub_questions]
        if getattr(plan, "hybrid_mode", None) == "doc_first":
            return [{"path": "pdf_rag", "question": ""}, {"path": "text_to_sql", "question": ""}]
        return [{"path": "text_to_sql", "question": ""}, {"path": "pdf_rag", "question": ""}]

    def _query_sql(self, plan: QuestionPlan, question: str, trace: dict[str, Any]) -> EvidencePackage:
        trace["tool_sequence"].append("text_to_sql")
        if self.sql_tool is None:
            return EvidencePackage("text_to_sql", question, [])
        package = self.sql_tool.query(self._sql_step_plan(plan), question)
        trace["stages"].append({"stage": "sql_evidence", "question": question, "evidence_count": len(package.evidences)})
        return package

    def _sql_step_plan(self, plan: QuestionPlan) -> QuestionPlan:
        if plan.task_type != "hybrid":
            return plan
        if plan.formula:
            task_type = "quote_formula"
        elif plan.time_scope.kind == "latest":
            task_type = "latest_record_lookup"
        else:
            task_type = "point_lookup"
        try:
            return replace(plan, route="text_to_sql", task_type=task_type)
        except TypeError:
            return QuestionPlan(
                route="text_to_sql",
                task_type=task_type,
                entities=plan.entities,
                time_scope=plan.time_scope,
                formula=plan.formula,
                evidence_need=["sql_result"],
                sub_questions=[],
                answer_constraints=plan.answer_constraints,
                reason=plan.reason,
                formula_params=getattr(plan, "formula_params", {}),
                raw_formula_text=getattr(plan, "raw_formula_text", None),
            )

    def _query_prospectus(self, question: str, trace: dict[str, Any]) -> EvidencePackage:
        trace["tool_sequence"].append("pdf_rag")
        if self.prospectus_tool is None:
            return EvidencePackage("pdf_rag", question, [])
        package = self.prospectus_tool.query(question)
        trace["stages"].append({"stage": "prospectus_evidence", "question": question, "evidence_count": len(package.evidences)})
        return package

    def _has_dependency_evidence(self, evidences: list[Evidence]) -> bool:
        return any(
            evidence.content.strip()
            or (getattr(evidence, "metadata", {}) or {}).get("entities")
            or (getattr(evidence, "metadata", {}) or {}).get("facts")
            for evidence in evidences
        )

    def _update_context(self, context: dict[str, Any], evidences: list[Evidence]) -> None:
        for evidence in evidences:
            metadata = getattr(evidence, "metadata", {}) or {}
            for group in ("entities", "facts"):
                values = metadata.get(group, {})
                if isinstance(values, dict):
                    for key, value in values.items():
                        context[key] = value

    def _render_sub_question(self, template: str, context: dict[str, Any]) -> str:
        rendered = template
        for key, value in context.items():
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            rendered = rendered.replace("{" + key + "}", str(value))
        return rendered

    def _with_dependency_failure(self, report: VerificationReport) -> VerificationReport:
        missing = list(report.missing_evidence)
        if "hybrid_dependency" not in missing:
            missing.insert(0, "hybrid_dependency")
        status = "partial" if report.selected_evidence_ids else "insufficient"
        notes = list(report.notes) + ["First hybrid step returned no dependency evidence"]
        try:
            return replace(report, status=status, missing_evidence=missing, notes=notes)
        except TypeError:
            return VerificationReport(status, report.selected_evidence_ids, report.conflicts, missing, notes)

    def _build_answer(
        self,
        plan: QuestionPlan,
        evidences: list[Evidence],
        report: VerificationReport,
    ) -> str:
        if not evidences:
            return "Insufficient evidence to answer."
        selected_ids = set(report.selected_evidence_ids) if report.selected_evidence_ids else {
            item.evidence_id for item in evidences
        }
        selected = [item for item in evidences if item.evidence_id in selected_ids]
        if not selected:
            selected = evidences
        prefix = ""
        if report.status == "conflict":
            prefix = "Conflicting evidence found. "
        elif report.status in {"partial", "insufficient"}:
            prefix = "Partial answer based on available evidence. "
        structured_value = self._extract_answer_value(plan, selected)
        if structured_value is not None:
            return prefix + self.verifier.format_answer(structured_value, plan)
        return prefix + "\n".join(item.content for item in selected)

    def _extract_answer_value(self, plan: QuestionPlan, evidences: list[Evidence]) -> Any:
        constraints = getattr(plan, "answer_constraints", None)
        output_type = getattr(constraints, "output_type", None)
        for evidence in evidences:
            metadata = getattr(evidence, "metadata", {}) or {}
            if "result_value" in metadata:
                return metadata["result_value"]
            if "rows" in metadata and output_type in {"ranked", "top_n", "top-N", "multi_value", "multi-year", "multi_year"}:
                rows = metadata["rows"]
                top_n = getattr(constraints, "top_n", None)
                if isinstance(rows, list) and top_n:
                    return rows[:top_n]
                return rows
            if "values" in metadata:
                return metadata["values"]
        return None

    def _to_dict(self, value: Any) -> dict[str, Any]:
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return asdict(value)
