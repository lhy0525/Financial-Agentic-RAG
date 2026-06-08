#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a SQL-backed financial Agentic RAG smoke query.")
    parser.add_argument("question", help="Financial SQL question to answer.")
    parser.add_argument("--db", required=True, help="Path to the Bosera SQLite database.")
    parser.add_argument("--json", action="store_true", help="Print the full structured response.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        from src.agentic.orchestrator import FinancialOrchestrator
        from src.agentic.planner import FinancialQuestionPlanner
        from src.financial_sql.text_to_sql_tool import TextToSQLEvidenceTool
    except ModuleNotFoundError as exc:
        print(
            "Financial query dependencies are not fully available yet: "
            f"{exc.name}. Ensure planner, shared types, and SQL evidence modules are installed.",
            file=sys.stderr,
        )
        return 2

    agent = FinancialOrchestrator(
        planner=FinancialQuestionPlanner(),
        sql_tool=TextToSQLEvidenceTool(Path(args.db)),
        prospectus_tool=None,
    )
    result = agent.answer(args.question)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["answer"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
