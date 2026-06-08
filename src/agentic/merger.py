from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import Any

from src.agentic.types import Evidence, EvidencePackage


class EvidenceMerger:
    """Merge evidence packages while keeping source traceability intact."""

    def merge(self, packages: list[EvidencePackage]) -> list[Evidence]:
        merged: list[Evidence] = []
        index_by_id: dict[str, int] = {}
        index_by_source_content: dict[tuple[str, str, str], int] = {}

        for package in packages:
            for evidence in package.evidences:
                duplicate_index = self._duplicate_index(
                    evidence=evidence,
                    index_by_id=index_by_id,
                    index_by_source_content=index_by_source_content,
                )
                if duplicate_index is None:
                    index = len(merged)
                    merged.append(self._with_trace_metadata(evidence, package))
                    index_by_id[evidence.evidence_id] = index
                    index_by_source_content[self._source_content_key(evidence)] = index
                    continue

                merged[duplicate_index] = self._group_duplicate(
                    merged[duplicate_index],
                    evidence,
                    package,
                )
                index_by_id[evidence.evidence_id] = duplicate_index

        return merged

    def _duplicate_index(
        self,
        evidence: Evidence,
        index_by_id: dict[str, int],
        index_by_source_content: dict[tuple[str, str, str], int],
    ) -> int | None:
        if evidence.evidence_id in index_by_id:
            return index_by_id[evidence.evidence_id]
        return index_by_source_content.get(self._source_content_key(evidence))

    def _source_content_key(self, evidence: Evidence) -> tuple[str, str, str]:
        return (evidence.source_type, evidence.source, evidence.content.strip())

    def _with_trace_metadata(self, evidence: Evidence, package: EvidencePackage) -> Evidence:
        metadata = dict(getattr(evidence, "metadata", {}) or {})
        metadata.setdefault("source_path", evidence.source)
        metadata.setdefault("package_path", package.path)
        metadata.setdefault("duplicate_evidence_ids", [evidence.evidence_id])
        metadata.setdefault("duplicate_sources", [evidence.source])
        if package.trace_id:
            metadata.setdefault("trace_ids", [package.trace_id])
        return self._replace_metadata(evidence, metadata)

    def _group_duplicate(
        self,
        retained: Evidence,
        duplicate: Evidence,
        package: EvidencePackage,
    ) -> Evidence:
        prior_metadata = dict(getattr(retained, "metadata", {}) or {})
        duplicate_metadata = dict(getattr(duplicate, "metadata", {}) or {})
        prior_id = retained.evidence_id
        prior_source = retained.source
        retained = self._choose_stronger(retained, duplicate)
        metadata = dict(getattr(retained, "metadata", {}) or {})
        self._preserve_traceability(metadata, prior_metadata)
        self._preserve_traceability(metadata, duplicate_metadata)
        duplicate_ids = list(metadata.get("duplicate_evidence_ids", [prior_id]))
        duplicate_sources = list(metadata.get("duplicate_sources", [prior_source]))
        trace_ids = list(metadata.get("trace_ids", []))

        self._append_unique(duplicate_ids, duplicate.evidence_id)
        self._append_unique(duplicate_sources, duplicate.source)
        if package.trace_id:
            self._append_unique(trace_ids, package.trace_id)

        metadata["duplicate_evidence_ids"] = duplicate_ids
        metadata["duplicate_sources"] = duplicate_sources
        if trace_ids:
            metadata["trace_ids"] = trace_ids
        return self._replace_metadata(retained, metadata)

    def _choose_stronger(self, current: Evidence, candidate: Evidence) -> Evidence:
        current_score = getattr(current, "score", None)
        candidate_score = getattr(candidate, "score", None)
        if candidate_score is None:
            return current
        if current_score is None or candidate_score > current_score:
            metadata = dict(getattr(candidate, "metadata", {}) or {})
            current_metadata = dict(getattr(current, "metadata", {}) or {})
            metadata.setdefault(
                "duplicate_evidence_ids",
                current_metadata.get("duplicate_evidence_ids", [current.evidence_id]),
            )
            metadata.setdefault(
                "duplicate_sources",
                current_metadata.get("duplicate_sources", [current.source]),
            )
            return self._replace_metadata(candidate, metadata)
        return current

    def _preserve_traceability(
        self,
        metadata: dict[str, Any],
        prior_metadata: dict[str, Any],
    ) -> None:
        for key in ("source_path", "package_path"):
            if key in prior_metadata:
                metadata.setdefault(key, prior_metadata[key])
        for key in ("trace_ids", "duplicate_evidence_ids", "duplicate_sources"):
            for value in prior_metadata.get(key, []):
                values = metadata.setdefault(key, [])
                self._append_unique(values, value)

    def _replace_metadata(self, evidence: Evidence, metadata: dict[str, Any]) -> Evidence:
        if is_dataclass(evidence):
            return replace(evidence, metadata=metadata)
        evidence.metadata = metadata
        return evidence

    def _append_unique(self, values: list[Any], value: Any) -> None:
        if value not in values:
            values.append(value)
