import json

from src.financial_dataset.question_loader import load_question_jsonl, select_questions


def test_load_question_jsonl_reads_one_object_per_line(tmp_path):
    path = tmp_path / "question.json"
    path.write_text(
        "\n".join(
            [
                json.dumps({"id": 1, "question": "SQL question"}, ensure_ascii=False),
                json.dumps({"id": 2, "question": "prospectus question"}, ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )

    rows = load_question_jsonl(path)

    assert rows == [
        {"id": 1, "question": "SQL question"},
        {"id": 2, "question": "prospectus question"},
    ]


def test_select_questions_by_id_keeps_requested_order():
    rows = [
        {"id": 1, "question": "one"},
        {"id": 2, "question": "two"},
        {"id": 3, "question": "three"},
    ]

    selected = select_questions(rows, [3, 1])

    assert [row["id"] for row in selected] == [3, 1]
