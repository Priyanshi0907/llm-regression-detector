"""
Drift detection: catches gradual degradation that per-run diffs miss.

A prompt can lose 1-2% accuracy on five consecutive runs — each one too
small to trip the per-run WARNING/FAIL thresholds — and still end up 8%
worse than where it started. We track a rolling N-run moving average and
fire a separate "slow drift" warning if it drops below the first run's
baseline average by more than DRIFT_THRESHOLD_PCT, even when no single
run triggered an alert on its own.
"""
from __future__ import annotations
from dataclasses import dataclass

from src.config import settings
from src.models import EvalRun


@dataclass
class DriftStatus:
    is_drifting: bool
    current_moving_avg: float
    reference_avg: float
    delta_pct: float
    window: int
    message: str


def check_drift(historical_runs: list[EvalRun]) -> DriftStatus | None:
    """historical_runs must be sorted oldest -> newest and include the current run."""
    window = settings.drift_window
    if len(historical_runs) < window:
        return None  # not enough history yet

    accuracies = [r.overall_accuracy for r in historical_runs]

    # Reference: the moving average from the *first* full window we ever had.
    reference_avg = sum(accuracies[:window]) / window
    # Current: the moving average over the most recent window.
    current_window = accuracies[-window:]
    current_moving_avg = sum(current_window) / window

    delta_pct = reference_avg - current_moving_avg
    is_drifting = delta_pct >= settings.drift_threshold_pct

    if is_drifting:
        message = (
            f"Slow drift detected: {window}-run moving average dropped "
            f"{delta_pct:.1f} pts below its reference baseline "
            f"({current_moving_avg:.1f}% vs {reference_avg:.1f}%) despite no "
            f"single run individually triggering a regression alert."
        )
    else:
        message = (
            f"No slow drift. {window}-run moving average: {current_moving_avg:.1f}% "
            f"(reference: {reference_avg:.1f}%)."
        )

    return DriftStatus(
        is_drifting=is_drifting,
        current_moving_avg=current_moving_avg,
        reference_avg=reference_avg,
        delta_pct=delta_pct,
        window=window,
        message=message,
    )
