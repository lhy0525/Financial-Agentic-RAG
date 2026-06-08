from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Route = Literal["pdf_rag", "text_to_sql", "hybrid"]
HybridMode = Literal["doc_first", "sql_first"]
VerificationStatus = Literal["pass", "partial", "conflict", "insufficient"]


@dataclass(frozen=True)
class TimeScope:
    kind: str
    value: Any
    start: str | None = None
    end: str | None = None
    report_types: list[str] = field(default_factory=list)
    date_column: str | None = None
    per_entity_latest: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimeScope":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnswerConstraints:
    output_type: str = "text"
    precision: int | None = None
    unit: str | None = None
    preserve_identifier_zeroes: bool = True
    order: str | None = None
    top_n: int | None = None
    count: bool = False
    sum: bool = False
    average: bool = False

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
    formula: str | None
    evidence_need: list[str]
    sub_questions: list[dict[str, str]]
    answer_constraints: AnswerConstraints
    reason: str
    hybrid_mode: HybridMode | None = None
    formula_params: dict[str, Any] = field(default_factory=dict)
    raw_formula_text: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestionPlan":
        payload = dict(data)
        payload["time_scope"] = TimeScope.from_dict(payload["time_scope"])
        payload["answer_constraints"] = AnswerConstraints.from_dict(
            payload["answer_constraints"]
        )
        return cls(**payload)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    evidence_type: str
    source_type: str
    content: str
    source: str
    score: float | None = None
    page: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidencePackage:
    path: str
    question: str
    evidences: list[Evidence]
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidencePackage":
        payload = dict(data)
        payload["evidences"] = [
            Evidence.from_dict(item) for item in payload["evidences"]
        ]
        return cls(**payload)

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
