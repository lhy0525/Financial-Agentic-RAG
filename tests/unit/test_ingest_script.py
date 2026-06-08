from __future__ import annotations

from argparse import Namespace

from scripts.ingest import PipelineResult, print_summary, resolve_collection


def test_resolve_collection_defaults_to_default_without_financial_flag(tmp_path):
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text("financial_platform:\n  prospectus_collection: prospectus_docs\n", encoding="utf-8")

    collection = resolve_collection(
        Namespace(collection=None, financial_prospectus=False),
        settings_file,
    )

    assert collection == "default"


def test_resolve_collection_reads_financial_prospectus_collection(tmp_path):
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text("financial_platform:\n  prospectus_collection: prospectus_docs\n", encoding="utf-8")

    collection = resolve_collection(
        Namespace(collection=None, financial_prospectus=True),
        settings_file,
    )

    assert collection == "prospectus_docs"


def test_explicit_collection_overrides_financial_prospectus_default(tmp_path):
    settings_file = tmp_path / "settings.yaml"
    settings_file.write_text("financial_platform:\n  prospectus_collection: prospectus_docs\n", encoding="utf-8")

    collection = resolve_collection(
        Namespace(collection="manual_collection", financial_prospectus=True),
        settings_file,
    )

    assert collection == "manual_collection"


def test_print_summary_reports_skipped_duplicates(capsys):
    print_summary(
        [
            PipelineResult(success=True, file_path="a.pdf", stages={"integrity": {"skipped": True}}),
            PipelineResult(success=True, file_path="b.pdf", chunk_count=2),
            PipelineResult(success=False, file_path="c.pdf", error="parse failed"),
        ]
    )

    output = capsys.readouterr().out

    assert "Total files processed: 3" in output
    assert "[SKIP] Skipped duplicates: 1" in output
    assert "[FAIL] Failed: 1" in output
