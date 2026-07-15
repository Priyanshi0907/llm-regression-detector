"""
Turns a CaseResult (or a before/after pair) into a plain-English explanation.
Used by the dashboard's Case Detail view and the Regression Diff Viewer —
this is the "why did the model fail" answer engineers actually want,
instead of just raw expected/actual fields.
"""
from __future__ import annotations
from src.models import CaseResult


def explain_failure(case: CaseResult) -> str:
    if case.error:
        return f"Request failed before scoring: {case.error}"
    if case.passed:
        return "Passed — category matched and summary was judged relevant."
    if not case.category_match:
        return (
            f"Category mismatch: expected '{case.expected_category.value}' but got "
            f"'{case.actual_category.value if case.actual_category else 'no output'}'. "
            f"This is the primary failure signal — summary quality wasn't the issue."
        )
    if case.summary_score < 3.0:
        return (
            f"Category was correct, but the summary was judged low-relevance "
            f"({case.summary_score}/5) — likely too vague, off-topic, or missing "
            f"the customer's actual intent."
        )
    return "Failed for an unspecified combination of category and summary scoring."


def short_reason(case: CaseResult) -> str:
    """Compact one-line version of explain_failure, for table cells."""
    if case.error:
        return "Request error"
    if case.passed:
        return "Passed"
    if not case.category_match:
        return "Category mismatch"
    if case.summary_score < 3.0:
        return "Low summary score"
    return "Other"


def explain_verdict(baseline: CaseResult | None, current: CaseResult) -> str:
    """Explains a regression/improvement in the diff viewer, comparing two runs."""
    if baseline is None:
        return "No baseline result available for this case."

    if baseline.passed and not current.passed:
        if not current.category_match:
            return (
                f"Regressed: previously classified correctly as "
                f"'{baseline.actual_category.value if baseline.actual_category else '—'}', "
                f"now misclassified as "
                f"'{current.actual_category.value if current.actual_category else 'no output'}'. "
                f"Likely cause: prompt change weakened category disambiguation for this input."
            )
        return (
            f"Regressed: category is still correct, but summary relevance dropped "
            f"from {baseline.summary_score}/5 to {current.summary_score}/5."
        )

    if not baseline.passed and current.passed:
        if not baseline.category_match:
            return (
                f"Improved: previously misclassified as "
                f"'{baseline.actual_category.value if baseline.actual_category else 'no output'}', "
                f"now correctly classified as "
                f"'{current.actual_category.value if current.actual_category else '—'}'. "
                f"More precise classification."
            )
        return (
            f"Improved: category was already correct; summary relevance rose "
            f"from {baseline.summary_score}/5 to {current.summary_score}/5."
        )

    return "No change in pass/fail status between the two runs."
