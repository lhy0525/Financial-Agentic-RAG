import sqlite3

from src.financial_sql.sql_executor import SQLiteQueryExecutor


def _seed_db(path):
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE "items" ("id" INTEGER, "name" TEXT)')
    con.executemany('INSERT INTO "items" VALUES (?, ?)', [(1, "a"), (2, "b"), (3, "c")])
    con.commit()
    con.close()


def test_executor_returns_rows_columns_and_elapsed_time(tmp_path):
    db_path = tmp_path / "data.db"
    _seed_db(db_path)

    result = SQLiteQueryExecutor(db_path, row_cap=2).execute("SELECT * FROM items ORDER BY id")

    assert result.status == "success"
    assert result.columns == ["id", "name"]
    assert result.row_count == 2
    assert result.rows == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    assert result.elapsed_ms >= 0


def test_executor_empty_result_is_explicit(tmp_path):
    db_path = tmp_path / "data.db"
    _seed_db(db_path)

    result = SQLiteQueryExecutor(db_path).execute("SELECT * FROM items WHERE id = 99")

    assert result.status == "empty"
    assert result.row_count == 0
    assert result.rows == []


def test_executor_failure_result_is_explicit(tmp_path):
    db_path = tmp_path / "data.db"
    _seed_db(db_path)

    result = SQLiteQueryExecutor(db_path).execute("SELECT missing FROM items")

    assert result.status == "failed"
    assert "missing" in result.error


def test_executor_logs_query_attempts(tmp_path):
    db_path = tmp_path / "data.db"
    log_path = tmp_path / "queries.db"
    _seed_db(db_path)

    result = SQLiteQueryExecutor(db_path, log_db_path=log_path).execute(
        "SELECT * FROM items WHERE id = 1",
        question="question",
    )

    assert result.status == "success"
    con = sqlite3.connect(log_path)
    row = con.execute(
        "SELECT question, sql, status, row_count FROM sql_query_log"
    ).fetchone()
    con.close()
    assert row == ("question", "SELECT * FROM items WHERE id = 1", "success", 1)


def test_executor_logs_attempt_context(tmp_path):
    db_path = tmp_path / "data.db"
    log_path = tmp_path / "queries.db"
    _seed_db(db_path)

    result = SQLiteQueryExecutor(db_path, log_db_path=log_path).execute(
        "SELECT * FROM items WHERE id = 1",
        question="question",
        attempt_context={
            "source": "rule",
            "attempt_id": "attempt-1",
            "parent_attempt_id": None,
            "failure_code": None,
            "repair_reason": None,
            "safety_status": "allowed",
            "execution_status": "success",
            "selected": True,
        },
    )

    assert result.status == "success"
    con = sqlite3.connect(log_path)
    con.row_factory = sqlite3.Row
    row = con.execute(
        """
        SELECT source, attempt_id, parent_attempt_id, failure_code,
               repair_reason, safety_status, execution_status, selected
        FROM sql_query_log
        """
    ).fetchone()
    con.close()
    assert dict(row) == {
        "source": "rule",
        "attempt_id": "attempt-1",
        "parent_attempt_id": None,
        "failure_code": None,
        "repair_reason": None,
        "safety_status": "allowed",
        "execution_status": "success",
        "selected": 1,
    }


def test_executor_marks_selected_from_success_status(tmp_path):
    db_path = tmp_path / "data.db"
    log_path = tmp_path / "queries.db"
    _seed_db(db_path)

    SQLiteQueryExecutor(db_path, log_db_path=log_path).execute(
        "SELECT * FROM items WHERE id = 1",
        question="question",
        attempt_context={
            "source": "rule",
            "attempt_id": "rule-1",
            "selected_statuses": ["success", "empty"],
        },
    )

    con = sqlite3.connect(log_path)
    selected = con.execute("SELECT selected FROM sql_query_log").fetchone()[0]
    con.close()
    assert selected == 1
