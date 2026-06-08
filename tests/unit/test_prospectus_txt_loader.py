from src.prospectus_evidence.txt_loader import ProspectusTxtLoader


def test_txt_loader_preserves_table_placeholders_and_metadata(tmp_path):
    path = tmp_path / "prospectus.txt"
    path.write_text(
        "公司主营业务如下。\n<|TABLE_0001_0000.xlsx|>\n表后风险提示。",
        encoding="utf-8",
    )

    document = ProspectusTxtLoader(collection="ipo").load(path)

    assert "<|TABLE_0001_0000.xlsx|>" in document.text
    assert document.metadata["source_path"] == str(path)
    assert document.metadata["doc_type"] == "prospectus_txt"
    assert document.metadata["collection"] == "ipo"
    assert document.metadata["table_placeholders"] == ["TABLE_0001_0000.xlsx"]
