from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DATASET_DIR_NAME = "bs_challenge_financial_14b_dataset"
REPO_DATASET_RELATIVE_PATH = Path("data") / "datasets" / DATASET_DIR_NAME


@dataclass(frozen=True)
class FinancialDatasetPaths:
    root: Path
    question_json: Path
    sqlite_db: Path
    pdf_txt_dir: Path
    pdf_dir: Path
    available: bool
    skip_reason: str

    @classmethod
    def from_root(cls, root: str | Path) -> "FinancialDatasetPaths":
        root = Path(root).resolve()
        question_json = root / "question.json"
        pdf_txt_dir = root / "pdf_txt_file"
        pdf_dir = root / "pdf"
        dataset_dir = root / "dataset"
        sqlite_db = next(iter(sorted(dataset_dir.glob("*.db"))), dataset_dir / "")

        missing: list[str] = []
        if not root.exists():
            missing.append(f"dataset root not found: {root}")
        if not question_json.is_file():
            missing.append(f"question.json not found: {question_json}")
        if not dataset_dir.is_dir():
            missing.append(f"dataset directory not found: {dataset_dir}")
        elif not sqlite_db.is_file():
            missing.append(f"sqlite .db not found under: {dataset_dir}")
        if not pdf_txt_dir.is_dir():
            missing.append(f"pdf_txt_file directory not found: {pdf_txt_dir}")
        if not pdf_dir.is_dir():
            missing.append(f"pdf directory not found: {pdf_dir}")

        available = not missing
        skip_reason = "" if available else "Financial dataset incomplete data: " + "; ".join(missing)

        return cls(
            root=root,
            question_json=question_json,
            sqlite_db=sqlite_db,
            pdf_txt_dir=pdf_txt_dir,
            pdf_dir=pdf_dir,
            available=available,
            skip_reason=skip_reason,
        )


def find_financial_dataset(start: str | Path | None = None) -> FinancialDatasetPaths:
    start_path = Path.cwd() if start is None else Path(start)
    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    candidates: list[Path] = []
    for parent in [current, *current.parents]:
        candidates.append(parent / REPO_DATASET_RELATIVE_PATH)
        candidates.append(parent / DATASET_DIR_NAME)
        if parent.parent != parent:
            candidates.append(parent.parent / DATASET_DIR_NAME)

    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        paths = FinancialDatasetPaths.from_root(candidate)
        if paths.available or candidate.exists():
            return paths

    return FinancialDatasetPaths.from_root(current / REPO_DATASET_RELATIVE_PATH)
