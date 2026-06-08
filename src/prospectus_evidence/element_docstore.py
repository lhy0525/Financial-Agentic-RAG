from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RawElementPayload:
    element_id: str
    raw_content: str
    raw_format: str
    metadata: dict[str, Any]


class ElementDocstore:
    """Extension point for future raw PDF table/image/chart payload lookup."""

    def get(self, element_id: str) -> RawElementPayload | None:
        return None
