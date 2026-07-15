"""
The core value of this system: diffing one run against a baseline.

Computes aggregate deltas, flags individual cases that flipped pass->fail
(regressions) or fail->pass (improvements), and runs a statistical
significance test (two-proportion z-test via scipy) so a handful of flipped
cases in a noisy 60-case dataset don't trigger false alarms.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from scipy import stats as scipy_stats

from src.config import settings
from src.models import CaseResult, EvalRun


@dataclass
class CaseDelta:
    case_id: str
    input: str
    expected_category: str
    previous_category: str | None
    previous_summary_score: float | None
    new_category: str | None
    new_summary_score: float
    kind: str  # "regression" | "improvement"


@dataclass
class ComparisonResult:
    overall_accuracy_delta: float
    category_accuracy_delta: dict[str, float]
    regressions: list[CaseDelta] = field(default_factory=list)
    improvements: list[CaseDelta] = field(default_factory=list)
    no_change_count: int = 0
    p_value: float | None = None
    statistically_significant: bool = False
    status: str = "PASS"  # PASS | WARNING | FAIL


def _two_proportion_z_test(pass_a: int, n_a: int, pass_b: int, n_b: int) -> float:
    """Returns the p-value for whether pass rates differ significantly."""
    if n_a == 0 or n_b == 0:
        return 1.0
    p_a, p_b = pass_a / n_a, pass_b / n_b
    p_pool = (pass_a + pass_b) / (n_a + n_b)
    se = (p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b)) ** 0.5
    if se == 0:
        return 1.0
    z = (p_a - p_b) / se
    p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z)))
    return float(p_value)


def compute_category_accuracy(results: list[CaseResult]) -> dict[str, float]:
    buckets: dict[str, list[bool]] = {}
    for r in results:
        buckets.setdefault(r.expected_category.value, []).append(r.category_match)
    return {cat: (sum(v) / len(v) * 100 if v else 0.0) for cat, v in buckets.items()}


def compute_difficulty_breakdown(results: list[CaseResult]) -> dict[str, dict[str, int]]:
    """Returns {"easy": {"passed": 21, "total": 22}, ...} — pass/total counts
    per difficulty tier, used to show that 'hard' edge cases are the ones
    actually worth watching (see golden_dataset notes)."""
    buckets: dict[str, dict[str, int]] = {}
    for r in results:
        tier = r.expected_difficulty.value
        b = buckets.setdefault(tier, {"passed": 0, "total": 0})
        b["total"] += 1
        if r.passed:
            b["passed"] += 1
    return buckets


def compare_runs(
    current_results: list[CaseResult],
    baseline_results: list[CaseResult] | None,
) -> ComparisonResult:
    current_pass = sum(r.passed for r in current_results)
    current_n = len(current_results)
    current_accuracy = (current_pass / current_n * 100) if current_n else 0.0
    current_cat_acc = compute_category_accuracy(current_results)

    if not baseline_results:
        # First run ever — nothing to diff against.
        return ComparisonResult(
            overall_accuracy_delta=0.0,
            category_accuracy_delta={},
            no_change_count=current_n,
            status="PASS",
        )

    baseline_by_id = {r.case_id: r for r in baseline_results}
    baseline_pass = sum(r.passed for r in baseline_results)
    baseline_n = len(baseline_results)
    baseline_accuracy = (baseline_pass / baseline_n * 100) if baseline_n else 0.0
    baseline_cat_acc = compute_category_accuracy(baseline_results)

    overall_delta = current_accuracy - baseline_accuracy
    cat_delta = {
        cat: current_cat_acc.get(cat, 0.0) - baseline_cat_acc.get(cat, 0.0)
        for cat in set(current_cat_acc) | set(baseline_cat_acc)
    }

    regressions: list[CaseDelta] = []
    improvements: list[CaseDelta] = []
    no_change = 0

    for cur in current_results:
        base = baseline_by_id.get(cur.case_id)
        if base is None:
            continue
        if base.passed and not cur.passed:
            regressions.append(CaseDelta(
                case_id=cur.case_id, input=cur.input,
                expected_category=cur.expected_category.value,
                previous_category=base.actual_category.value if base.actual_category else None,
                previous_summary_score=base.summary_score,
                new_category=cur.actual_category.value if cur.actual_category else None,
                new_summary_score=cur.summary_score,
                kind="regression",
            ))
        elif not base.passed and cur.passed:
            improvements.append(CaseDelta(
                case_id=cur.case_id, input=cur.input,
                expected_category=cur.expected_category.value,
                previous_category=base.actual_category.value if base.actual_category else None,
                previous_summary_score=base.summary_score,
                new_category=cur.actual_category.value if cur.actual_category else None,
                new_summary_score=cur.summary_score,
                kind="improvement",
            ))
        else:
            no_change += 1

    p_value = _two_proportion_z_test(current_pass, current_n, baseline_pass, baseline_n)
    significant = p_value < 0.05

    abs_delta = abs(overall_delta)
    if abs_delta >= settings.critical_threshold_pct and overall_delta < 0:
        status = "FAIL"
    elif abs_delta >= settings.warning_threshold_pct and overall_delta < 0:
        status = "WARNING"
    else:
        status = "PASS"

    return ComparisonResult(
        overall_accuracy_delta=overall_delta,
        category_accuracy_delta=cat_delta,
        regressions=regressions,
        improvements=improvements,
        no_change_count=no_change,
        p_value=p_value,
        statistically_significant=significant,
        status=status,
    )
