from src.financial_sql.sql_safety import SQLSafetyChecker


def test_read_only_select_passes_safety():
    result = SQLSafetyChecker(default_limit=50).check('SELECT "股票代码" FROM "A股票日行情表" LIMIT 5')

    assert result.allowed is True
    assert result.sql.endswith("LIMIT 5")
    assert result.applied_limit is None


def test_rejects_unsafe_and_multiple_statements():
    checker = SQLSafetyChecker()

    for sql in [
        "DELETE FROM 基金基本信息",
        "DROP TABLE 基金基本信息",
        "SELECT 1; SELECT 2",
        "SELECT 1;",
        "WITH x AS (DELETE FROM t) SELECT 1",
    ]:
        assert checker.check(sql).allowed is False


def test_applies_limit_to_non_aggregate_queries():
    result = SQLSafetyChecker(default_limit=25).check("SELECT * FROM 基金基本信息")

    assert result.allowed is True
    assert result.sql == "SELECT * FROM 基金基本信息 LIMIT 25"
    assert result.applied_limit == 25


def test_does_not_limit_aggregate_only_query():
    result = SQLSafetyChecker(default_limit=25).check("SELECT COUNT(*) AS total FROM 基金基本信息")

    assert result.allowed is True
    assert result.sql == "SELECT COUNT(*) AS total FROM 基金基本信息"
    assert result.applied_limit is None
