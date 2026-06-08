from pathlib import Path


DOCS = Path(__file__).resolve().parents[2] / "docs" / "financial"


def test_domain_rules_doc_covers_required_sections():
    text = (DOCS / "domain-rules.md").read_text(encoding="utf-8")

    for required in [
        "Supported Formulas",
        "Table And Column Aliases",
        "Report Periods",
        "Source Priority",
        "Known Unsupported Patterns",
    ]:
        assert required in text


def test_dataset_setup_doc_covers_smoke_workflows_and_failures():
    text = (DOCS / "dataset-setup.md").read_text(encoding="utf-8")

    for required in [
        "SQLite Database Path",
        "Prospectus TXT Ingestion Smoke",
        "SQL Evidence Smoke",
        "Evaluation Smoke",
        "Common Failures",
    ]:
        assert required in text
