from __future__ import annotations

import hashlib
from pathlib import Path
import re

from src.core.types import Document


class ProspectusTxtLoader:
    def __init__(self, collection: str | None = None) -> None:
        self.collection = collection

    def load(self, file_path: str | Path) -> Document:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        placeholders = re.findall(r"<\|(TABLE_[^|]+)\|>", text)
        metadata = {
            "source_path": str(path),
            "doc_type": "prospectus_txt",
            "document_id": f"txt_{digest}",
            "document_type": "prospectus",
            "table_placeholders": placeholders,
        }
        if self.collection is not None:
            metadata["collection"] = self.collection
        return Document(id=f"txt_{digest}", text=text, metadata=metadata)
