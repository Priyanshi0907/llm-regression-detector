import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.comparison import compare_runs, compute_category_accuracy, _two_proportion_z_test
from src.models import CaseResult, Category


def _case(case_id, expected_cat, actual_cat, passed, score=4.5):
    return CaseResult(
        case_id=case_id, input="test", expected_category=expected_cat,
        actual_category=actual_cat, expected_summary="x", actual_summary="x",
        category_match=(expected_cat == actual_cat), summary_score=score,
        latency_ms=100, tokens_used=50, passed=passed, error=None,
    )


def test_no_baseline_returns_pass():
    current = [_case("1", Category.billing, Category.billing, True)]
    result = compare_runs(current, None)
    assert result.status == "PASS"
    assert result.no_change_count == 1


def test_detects_regression():
    baseline = [_case("1", Category.account, Category.account, True)]
    current = [_case("1", Category.account, Category.general, False)]
    result = compare_runs(current, baseline)
    assert len(result.regressions) == 1
    assert result.regressions[0].case_id == "1"


def test_detects_improvement():
    baseline = [_case("1", Category.account, Category.general, False)]
    current = [_case("1", Category.account, Category.account, True)]
    result = compare_runs(current, baseline)
    assert len(result.improvements) == 1


def test_category_accuracy_buckets_correctly():
    results = [
        _case("1", Category.billing, Category.billing, True),
        _case("2", Category.billing, Category.general, False),
        _case("3", Category.technical, Category.technical, True),
    ]
    acc = compute_category_accuracy(results)
    assert acc["billing"] == 50.0
    assert acc["technical"] == 100.0


def test_z_test_identical_rates_gives_high_pvalue():
    p = _two_proportion_z_test(50, 100, 50, 100)
    assert p > 0.9


def test_z_test_large_gap_gives_low_pvalue():
    p = _two_proportion_z_test(30, 100, 90, 100)
    assert p < 0.01


if __name__ == "__main__":
    import inspect
    tests = [obj for name, obj in globals().items() if name.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
