from __future__ import annotations

from src.financial_sql.agent_types import FAILURE_CODES, RouteOutcome, SQLFailureCode


SOURCE_ORDER: tuple[str, ...] = ("rule", "lora", "api")
REPAIRABLE_FAILURE_CODES: frozenset[str] = frozenset({"compile_failed", "unsafe_sql", "execution_error"})


def classify_terminal_outcome(
    *,
    status: str,
    task_family: str | None = None,
    failure_code: str | None = None,
    empty_result_policy: str = "terminal",
) -> RouteOutcome:
    normalized_status = (status or "").strip().lower()
    normalized_policy = (empty_result_policy or "terminal").strip().lower()

    if normalized_status == "success":
        return RouteOutcome(
            accepted_result_kind="rows",
            failure_code=None,
            should_fallback=False,
            fallback_eligibility_reason="accepted_rows",
        )

    if normalized_status == "empty":
        if normalized_policy in {"fallback", "repair"}:
            return RouteOutcome(
                accepted_result_kind=None,
                failure_code="empty_result",
                should_fallback=True,
                fallback_eligibility_reason=f"empty_result_{normalized_policy}",
            )
        return RouteOutcome(
            accepted_result_kind="empty",
            failure_code="empty_result",
            should_fallback=False,
            fallback_eligibility_reason=_terminal_empty_reason(task_family),
        )

    stable_failure = _normalize_failure_code(failure_code)
    return RouteOutcome(
        accepted_result_kind=None,
        failure_code=stable_failure,
        should_fallback=stable_failure in REPAIRABLE_FAILURE_CODES,
        fallback_eligibility_reason=(
            "repairable_failure" if stable_failure in REPAIRABLE_FAILURE_CODES else "terminal_failure"
        ),
    )


def _normalize_failure_code(failure_code: str | None) -> SQLFailureCode:
    if failure_code in FAILURE_CODES:
        return failure_code  # type: ignore[return-value]
    return "all_candidates_failed"


def _terminal_empty_reason(task_family: str | None) -> str:
    if task_family:
        return f"empty_result_terminal:{task_family}"
    return "empty_result_terminal"
