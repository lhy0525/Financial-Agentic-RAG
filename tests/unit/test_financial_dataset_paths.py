from pathlib import Path

from src.financial_dataset.paths import FinancialDatasetPaths, find_financial_dataset


def test_find_financial_dataset_from_repo_layout():
    paths = find_financial_dataset(Path(__file__).resolve().parents[3])

    assert paths.root.name == "bs_challenge_financial_14b_dataset"
    assert paths.question_json.name == "question.json"
    assert paths.pdf_txt_dir.name == "pdf_txt_file"
    assert paths.sqlite_db.suffix == ".db"


def test_missing_dataset_returns_skip_reason(tmp_path):
    paths = FinancialDatasetPaths.from_root(tmp_path / "missing")

    assert paths.available is False
    assert "not found" in paths.skip_reason.lower()
