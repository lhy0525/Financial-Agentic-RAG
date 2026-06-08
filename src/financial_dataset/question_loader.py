from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_question_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"question.json line {line_number} must be a JSON object")
            missing = {"id", "question"} - row.keys()
            if missing:
                raise ValueError(
                    f"question.json line {line_number} missing required keys: {sorted(missing)}"
                )
            rows.append(row)
    return rows


def select_questions(rows: list[dict[str, Any]], ids: list[Any]) -> list[dict[str, Any]]:
    by_id = {row["id"]: row for row in rows}
    missing = [question_id for question_id in ids if question_id not in by_id]
    if missing:
        raise KeyError(f"question ids not found: {missing}")
    return [by_id[question_id] for question_id in ids]
