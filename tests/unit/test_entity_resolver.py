import sqlite3

from src.financial_sql.entity_resolver import EntityResolver


def _seed_entity_db(path):
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE "基金基本信息" ("基金代码" TEXT, "基金全称" TEXT, "基金简称" TEXT)')
    con.execute('CREATE TABLE "基金股票持仓明细" ("股票代码" TEXT, "股票名称" TEXT)')
    con.executemany(
        'INSERT INTO "基金基本信息" VALUES (?, ?, ?)',
        [
            ("000001", "华富成长趋势混合型证券投资基金", "华富成长趋势"),
            ("000002", "华富成长优选混合型证券投资基金", "华富成长优选"),
        ],
    )
    con.executemany(
        'INSERT INTO "基金股票持仓明细" VALUES (?, ?)',
        [("600519", "贵州茅台"), ("000001", "平安银行")],
    )
    con.commit()
    con.close()


def test_resolves_stock_code_without_database_lookup():
    result = EntityResolver().resolve_stock("600519")

    assert result.status == "matched"
    assert result.code == "600519"
    assert result.metadata["resolution_strategy"] == "direct_code"


def test_resolves_stock_name_against_sqlite(tmp_path):
    db_path = tmp_path / "entities.db"
    _seed_entity_db(db_path)

    result = EntityResolver(db_path).resolve_stock("贵州茅台")

    assert result.status == "matched"
    assert result.code == "600519"
    assert result.name == "贵州茅台"


def test_resolves_stock_short_name_from_company_full_name(tmp_path):
    db_path = tmp_path / "entities.db"
    _seed_entity_db(db_path)
    con = sqlite3.connect(db_path)
    con.execute(
        'INSERT INTO "基金股票持仓明细" VALUES (?, ?)',
        ("300184", "力源信息"),
    )
    con.commit()
    con.close()

    result = EntityResolver(db_path).resolve_stock("武汉力源信息技术股份有限公司")

    assert result.status == "matched"
    assert result.code == "300184"
    assert result.name == "力源信息"
    assert result.metadata["resolution_strategy"] == "sqlite_alias"


def test_reports_fund_alias_ambiguity(tmp_path):
    db_path = tmp_path / "entities.db"
    _seed_entity_db(db_path)

    result = EntityResolver(db_path).resolve_fund("华富成长")

    assert result.status == "ambiguous"
    assert result.code is None
    assert len(result.candidates) == 2


def test_reports_no_match_with_metadata(tmp_path):
    db_path = tmp_path / "entities.db"
    _seed_entity_db(db_path)

    result = EntityResolver(db_path).resolve_fund("不存在基金")

    assert result.status == "no_match"
    assert result.metadata["searched_tables"] == ["基金基本信息"]
