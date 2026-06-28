from __future__ import annotations

import re

from src.agentic.types import Evidence, EvidencePackage


class ProspectusEvidenceTool:
    def __init__(self, search, element_docstore=None) -> None:
        self.search = search
        self.element_docstore = element_docstore

    def query(
        self,
        question: str,
        top_k: int = 5,
        filters: dict | None = None,
        expected: dict | None = None,
    ) -> EvidencePackage:
        results = self.search.search(
            query=question,
            top_k=top_k,
            filters=filters,
            trace=None,
            return_details=False,
        )
        evidences = [self._to_evidence(index, result) for index, result in enumerate(results, start=1)]
        metrics = self._hit_metrics(evidences, expected or {})
        status = "success" if evidences else "empty"
        if evidences and metrics.get("negative_reasons"):
            status = "mismatch"
        return EvidencePackage(
            path="pdf_rag",
            question=question,
            evidences=evidences,
            metadata={
                "status": status,
                "result_count": len(evidences),
                "top_k": top_k,
                **metrics,
            },
        )

    def query_knowledge_hub(self, request: dict) -> EvidencePackage:
        return self.query(
            str(request.get("query", "")),
            top_k=int(request.get("top_k", 5)),
            filters=request.get("filters"),
            expected=request.get("expected"),
        )

    def _to_evidence(self, index: int, result) -> Evidence:
        metadata = dict(getattr(result, "metadata", {}) or {})
        text = getattr(result, "text", "")
        placeholders = re.findall(r"<\|(TABLE_[^|]+)\|>", text)
        element_id = metadata.get("element_id")
        page = metadata.get("page", metadata.get("page_num"))
        image_refs = self._image_refs(text, metadata)
        images = metadata.get("images") if isinstance(metadata.get("images"), list) else []
        image_captions = self._image_captions(metadata.get("image_captions"))
        modalities = self._modalities(text, placeholders, metadata, image_refs)
        raw_payload_available = bool(metadata.get("raw_payload_available"))
        if element_id and self.element_docstore is not None:
            raw_payload_available = self.element_docstore.get(element_id) is not None
        evidence_metadata = {
            "chunk_id": getattr(result, "chunk_id", None),
            "chunk_index": metadata.get("chunk_index"),
            "element_id": element_id,
            "element_type": metadata.get("element_type"),
            "page": page,
            "page_num": metadata.get("page_num"),
            "section": metadata.get("section"),
            "company_name": metadata.get("company_name"),
            "disclosure_family": metadata.get("disclosure_family"),
            "modalities": modalities,
            "table_placeholders": placeholders,
            "raw_payload_available": raw_payload_available,
            "raw_table_unavailable": bool(placeholders) and not raw_payload_available,
            "image_refs": image_refs,
            "images": images,
            "image_captions": image_captions,
        }
        evidence_metadata.update(
            {key: value for key, value in metadata.items() if key not in evidence_metadata}
        )
        return Evidence(
            evidence_id=f"prospectus-{index}",
            evidence_type=self._evidence_type(modalities),
            source_type="txt",
            content=text,
            source=metadata.get("source_path", ""),
            score=getattr(result, "score", None),
            page=page,
            metadata=evidence_metadata,
        )

    def _modalities(
        self,
        text: str,
        placeholders: list[str],
        metadata: dict,
        image_refs: list[str],
    ) -> list[str]:
        modalities: list[str] = []
        text_without_refs = re.sub(r"\[IMAGE:\s*[^\]]+\]", "", text)
        text_without_refs = re.sub(r"<\|TABLE_[^|]+\|>", "", text_without_refs).strip()
        if text_without_refs:
            modalities.append("text")
        if placeholders or metadata.get("element_type") == "table" or metadata.get("table_placeholders"):
            modalities.append("table")
        if image_refs:
            modalities.append("image")
        return modalities or ["text"]

    def _evidence_type(self, modalities: list[str]) -> str:
        if "image" in modalities and len(modalities) > 1:
            return "multimodal"
        if "image" in modalities:
            return "image"
        if "table" in modalities:
            return "table"
        return "text"

    def _image_refs(self, text: str, metadata: dict) -> list[str]:
        refs: list[str] = []
        raw_refs = metadata.get("image_refs")
        if isinstance(raw_refs, list):
            refs.extend(str(ref) for ref in raw_refs if ref)
        images = metadata.get("images")
        if isinstance(images, list):
            refs.extend(
                str(image.get("id"))
                for image in images
                if isinstance(image, dict) and image.get("id")
            )
        refs.extend(match.strip() for match in re.findall(r"\[IMAGE:\s*([^\]]+)\]", text))
        return list(dict.fromkeys(refs))

    def _image_captions(self, raw_captions) -> list[dict]:
        if isinstance(raw_captions, list):
            return [caption for caption in raw_captions if isinstance(caption, dict)]
        if isinstance(raw_captions, dict):
            return [
                {"id": str(image_id), "caption": caption}
                for image_id, caption in raw_captions.items()
            ]
        return []

    def _hit_metrics(self, evidences: list[Evidence], expected: dict) -> dict:
        negative_reasons = []
        if expected and not evidences:
            negative_reasons.append("no_relevant_disclosure")
        hit_rank = self._expected_hit_rank(evidences, expected)
        metrics = {
            "top_k_hit": hit_rank is not None,
            "hit_rank": hit_rank,
            "source_hit": self._any_metadata_match(evidences, "source_path", expected.get("source_path")),
            "page_hit": self._any_page_match(evidences, expected.get("page")),
            "section_hit": self._any_metadata_match(evidences, "section", expected.get("section")),
            "disclosure_family_hit": self._any_metadata_match(
                evidences,
                "disclosure_family",
                expected.get("disclosure_family"),
            ),
            "negative_reasons": negative_reasons,
            "response_fields": ["path", "question", "evidences", "metadata"],
        }
        if not expected:
            return metrics
        if expected.get("company_name") and not self._any_metadata_match(
            evidences, "company_name", expected["company_name"]
        ):
            metrics["negative_reasons"].append("wrong_company")
        if (
            expected.get("ambiguous_alias") is False
            and self._any_metadata_match(evidences, "ambiguous_alias", True)
        ):
            metrics["negative_reasons"].append("ambiguous_alias")
        if expected.get("disclosure_family") and not metrics["disclosure_family_hit"]:
            metrics["negative_reasons"].append("neighboring_topic")
        if expected.get("source_path") and not metrics["source_hit"]:
            metrics["negative_reasons"].append("wrong_source")
        return metrics

    def _any_metadata_match(self, evidences: list[Evidence], key: str, expected) -> bool:
        if expected is None:
            return False
        return any((evidence.metadata or {}).get(key) == expected for evidence in evidences)

    def _any_page_match(self, evidences: list[Evidence], expected) -> bool:
        if expected is None:
            return False
        return any(evidence.page == expected or (evidence.metadata or {}).get("page") == expected for evidence in evidences)

    def _expected_hit_rank(self, evidences: list[Evidence], expected: dict) -> int | None:
        criteria = {
            "source_path": expected.get("source_path"),
            "page": expected.get("page"),
            "section": expected.get("section"),
            "disclosure_family": expected.get("disclosure_family"),
            "company_name": expected.get("company_name"),
        }
        active = {key: value for key, value in criteria.items() if value is not None}
        if not active:
            return None
        for rank, evidence in enumerate(evidences, start=1):
            metadata = evidence.metadata or {}
            matched = True
            for key, value in active.items():
                actual = evidence.page if key == "page" else metadata.get(key)
                if actual != value:
                    matched = False
                    break
            if matched:
                return rank
        return None
