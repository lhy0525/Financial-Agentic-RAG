#!/usr/bin/env python
"""Evaluation script for Modular RAG MCP Server.

Runs batch evaluation against a golden test set and outputs a metrics report.

Usage:
    # Run with default settings (custom evaluator)
    python scripts/evaluate.py

    # Specify a custom golden test set
    python scripts/evaluate.py --test-set path/to/golden.json

    # Use a specific collection
    python scripts/evaluate.py --collection technical_docs

    # JSON output
    python scripts/evaluate.py --json

Exit codes:
    0 - Success
    1 - Evaluation failure
    2 - Configuration error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run RAG evaluation against a golden test set."
    )
    parser.add_argument(
        "--test-set",
        default="tests/fixtures/golden_test_set.json",
        help="Path to golden test set JSON file (default: tests/fixtures/golden_test_set.json)",
    )
    parser.add_argument(
        "--collection",
        default=None,
        help="Collection name to search within.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of chunks to retrieve per query (default: 10).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of formatted text.",
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="Skip retrieval (evaluate with mock chunks for testing).",
    )
    parser.add_argument(
        "--financial",
        action="store_true",
        help="Run the financial Agentic RAG boundary evaluation mode.",
    )
    parser.add_argument(
        "--thresholds",
        default=None,
        help="Financial thresholds as a JSON object or path to a JSON file.",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    if args.financial:
        return _run_financial_evaluation(args)

    try:
        from src.core.settings import load_settings
        from src.libs.evaluator.evaluator_factory import EvaluatorFactory
        from src.observability.evaluation.eval_runner import EvalRunner

        settings = load_settings()
    except Exception as exc:
        print(f"❌ Configuration error: {exc}", file=sys.stderr)
        return 2

    # Create evaluator from config
    try:
        evaluator = EvaluatorFactory.create(settings)
        evaluator_name = type(evaluator).__name__
    except Exception as exc:
        print(f"❌ Failed to create evaluator: {exc}", file=sys.stderr)
        return 2

    # Create HybridSearch (unless --no-search)
    hybrid_search = None
    if not args.no_search:
        try:
            from src.core.query_engine.query_processor import QueryProcessor
            from src.core.query_engine.hybrid_search import create_hybrid_search
            from src.core.query_engine.dense_retriever import create_dense_retriever
            from src.core.query_engine.sparse_retriever import create_sparse_retriever
            from src.ingestion.storage.bm25_indexer import BM25Indexer
            from src.libs.embedding.embedding_factory import EmbeddingFactory
            from src.libs.vector_store.vector_store_factory import VectorStoreFactory

            collection = args.collection or "default"

            vector_store = VectorStoreFactory.create(
                settings, collection_name=collection,
            )
            embedding_client = EmbeddingFactory.create(settings)
            dense_retriever = create_dense_retriever(
                settings=settings,
                embedding_client=embedding_client,
                vector_store=vector_store,
            )
            bm25_indexer = BM25Indexer(index_dir=f"data/db/bm25/{collection}")
            sparse_retriever = create_sparse_retriever(
                settings=settings,
                bm25_indexer=bm25_indexer,
                vector_store=vector_store,
            )
            sparse_retriever.default_collection = collection

            query_processor = QueryProcessor()
            hybrid_search = create_hybrid_search(
                settings=settings,
                query_processor=query_processor,
                dense_retriever=dense_retriever,
                sparse_retriever=sparse_retriever,
            )
            print(f"✅ HybridSearch initialized for collection: {collection}")
        except Exception as exc:
            print(f"⚠️  Failed to initialize search (running without retrieval): {exc}")

    # Create and run EvalRunner
    runner = EvalRunner(
        settings=settings,
        hybrid_search=hybrid_search,
        evaluator=evaluator,
    )

    try:
        print(f"\n🔍 Running evaluation with {evaluator_name}...")
        print(f"📄 Test set: {args.test_set}")
        print(f"🔢 Top-K: {args.top_k}\n")

        report = runner.run(
            test_set_path=args.test_set,
            top_k=args.top_k,
            collection=args.collection,
        )
    except Exception as exc:
        print(f"❌ Evaluation failed: {exc}", file=sys.stderr)
        return 1

    # Output results
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        _print_report(report)

    return 0


def _run_financial_evaluation(args: argparse.Namespace) -> int:
    try:
        from src.observability.evaluation.financial_eval_runner import FinancialEvalRunner
    except Exception as exc:
        print(f"Financial evaluation dependencies are unavailable: {exc}", file=sys.stderr)
        return 2

    try:
        test_set = args.test_set
        if test_set == "tests/fixtures/golden_test_set.json":
            test_set = "tests/fixtures/financial_boundary_eval_cases.json"
        payload = _load_financial_test_set(test_set)
        if isinstance(payload, list):
            cases = payload
            thresholds = {}
        else:
            cases = payload.get("cases", [])
            thresholds = dict(payload.get("thresholds", {}))
        thresholds.update(_load_thresholds(args.thresholds))
    except Exception as exc:
        print(f"Financial evaluation setup failed: {exc}", file=sys.stderr)
        return 2

    agent = _NoSearchFinancialAgent() if args.no_search else _build_financial_agent()
    if agent is None:
        print(
            "Financial evaluation requires the local dataset for search mode; "
            "rerun with --no-search for fixture smoke evaluation.",
            file=sys.stderr,
        )
        return 2

    result = FinancialEvalRunner(agent=agent, thresholds=thresholds).run(cases)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_financial_report(result)
    return 0 if result.get("passed", False) else 1


def _load_financial_test_set(path: str) -> dict[str, Any] | list[dict[str, Any]]:
    test_set = Path(path)
    if not test_set.is_absolute():
        test_set = PROJECT_ROOT / test_set
    return json.loads(test_set.read_text(encoding="utf-8"))


def _load_thresholds(value: str | None) -> dict[str, float]:
    if not value:
        return {}
    candidate = Path(value)
    if candidate.exists():
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    else:
        payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("--thresholds must be a JSON object or a file containing one")
    return {str(key): float(metric_value) for key, metric_value in payload.items()}


def _build_financial_agent():
    try:
        from src.agentic.planner import FinancialQuestionPlanner
        from src.financial_dataset.paths import find_financial_dataset
        from src.financial_sql.text_to_sql_tool import TextToSQLEvidenceTool
    except Exception as exc:
        print(f"Financial search dependencies are unavailable: {exc}", file=sys.stderr)
        return None

    dataset = find_financial_dataset(PROJECT_ROOT)
    if not dataset.available:
        return None

    class SqlOnlyFinancialAgent:
        def __init__(self) -> None:
            self.planner = FinancialQuestionPlanner()
            self.sql_tool = TextToSQLEvidenceTool(dataset.sqlite_db)

        def answer(self, question: str) -> dict[str, Any]:
            plan = self.planner.plan(question)
            sources = []
            if plan.route == "text_to_sql":
                package = self.sql_tool.query(plan, question)
                sources = [evidence.to_dict() for evidence in package.evidences]
            status = "pass" if sources else "insufficient"
            return {
                "question_plan": plan.to_dict(),
                "verification_report": {"status": status},
                "answer": sources[0]["content"] if sources else "",
                "sources": sources,
                "trace": {"tool_sequence": ["plan", plan.route]},
            }

    return SqlOnlyFinancialAgent()


class _NoSearchFinancialAgent:
    def answer(self, question: str) -> dict[str, Any]:
        route = "pdf_rag" if "prospectus" in question.lower() else "text_to_sql"
        status = "partial" if route == "pdf_rag" else "pass"
        source_type = "txt" if route == "pdf_rag" else "db"
        evidence_type = "table" if route == "pdf_rag" else "sql_result"
        metadata = (
            {"raw_table_unavailable": True}
            if route == "pdf_rag"
            else {"sql_safety_passed": True, "sql_execution_success": True}
        )
        return {
            "question_plan": {
                "route": route,
                "hybrid_mode": None,
                "entities": {},
                "formula": None,
            },
            "verification_report": {"status": status},
            "answer": "financial fixture answer",
            "sources": [
                {
                    "evidence_id": "fixture-1",
                    "evidence_type": evidence_type,
                    "source_type": source_type,
                    "source": "fixture",
                    "metadata": metadata,
                }
            ],
            "trace": {"tool_sequence": ["plan", route]},
        }


def _print_financial_report(result: dict[str, Any]) -> None:
    print("=" * 60)
    print("  FINANCIAL EVALUATION REPORT")
    print("=" * 60)
    print(f"  Passed: {result.get('passed')}")
    print(f"  Cases:  {result.get('count')}")
    print(f"  Skips:  {len(result.get('skipped_cases', []))}")
    for failure in result.get("failed_thresholds", []):
        print(
            "  Failed threshold: "
            f"{failure['metric']}={failure['value']:.4f} < {failure['threshold']:.4f}"
        )


def _print_report(report) -> None:
    """Print formatted evaluation report."""
    print("=" * 60)
    print("  EVALUATION REPORT")
    print("=" * 60)
    print(f"  Evaluator: {report.evaluator_name}")
    print(f"  Test Set:  {report.test_set_path}")
    print(f"  Queries:   {len(report.query_results)}")
    print(f"  Time:      {report.total_elapsed_ms:.0f} ms")
    print()

    # Aggregate metrics
    print("─" * 60)
    print("  AGGREGATE METRICS")
    print("─" * 60)
    if report.aggregate_metrics:
        for metric, value in sorted(report.aggregate_metrics.items()):
            bar = "█" * int(value * 20) + "░" * (20 - int(value * 20))
            print(f"  {metric:<25s} {bar} {value:.4f}")
    else:
        print("  (no metrics computed)")
    print()

    # Per-query details
    print("─" * 60)
    print("  PER-QUERY RESULTS")
    print("─" * 60)
    for i, qr in enumerate(report.query_results, 1):
        print(f"\n  [{i}] {qr.query}")
        print(f"      Retrieved: {len(qr.retrieved_chunk_ids)} chunks")
        if qr.metrics:
            for metric, value in sorted(qr.metrics.items()):
                print(f"      {metric}: {value:.4f}")
        else:
            print("      (no metrics)")
        print(f"      Time: {qr.elapsed_ms:.0f} ms")

    print()
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
