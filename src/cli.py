"""
Main entrypoint. Orchestrates: load prompt + dataset -> run eval ->
score -> save to DB -> diff against baseline -> check drift ->
generate HTML report -> alert (Slack/Discord/email) -> exit non-zero on
FAIL (so CI can block the merge).

Usage:
    python -m src.cli --prompt prompts/v8.yaml
    python -m src.cli --prompt prompts/v8.yaml --provider anthropic
    python -m src.cli --prompt prompts/v8.yaml --providers openai,anthropic,gemini
"""
from __future__ import annotations
import argparse
import asyncio
import sys

from src.config import settings
from src import storage
from src.eval_runner import load_golden_dataset, run_eval
from src.llm_feature import load_prompt_config
from src.providers.registry import SUPPORTED_PROVIDERS, default_model_for
from src.comparison import compare_runs, compute_category_accuracy, compute_difficulty_breakdown
from src.drift import check_drift
from src.report_generator import generate_report, save_report
from src.slack_alert import send_slack_alert
from src.discord_alert import send_discord_alert
from src.email_alert import send_email_alert
from src.models import EvalRun, CaseResult, PromptConfig


def _aggregate(case_results: list[CaseResult], prompt_version: str, model: str, provider: str,
                baseline_run_id: str | None) -> EvalRun:
    from datetime import datetime, timezone
    n = len(case_results)
    passed = sum(r.passed for r in case_results)
    accuracy = (passed / n * 100) if n else 0.0
    cat_acc = compute_category_accuracy(case_results)
    difficulty_breakdown = compute_difficulty_breakdown(case_results)
    avg_summary = sum(r.summary_score for r in case_results) / n if n else 0.0
    sem_scores = [r.semantic_similarity for r in case_results if r.semantic_similarity is not None]
    avg_semantic = (sum(sem_scores) / len(sem_scores)) if sem_scores else None
    avg_latency = sum(r.latency_ms for r in case_results) / n if n else 0.0
    avg_tokens = sum(r.tokens_used for r in case_results) / n if n else 0.0
    avg_cost = (avg_tokens / 1000) * settings.cost_per_1k_tokens

    return EvalRun(
        run_id=EvalRun.new_id(),
        prompt_version=prompt_version,
        model=model,
        provider=provider,
        baseline_run_id=baseline_run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_cases=n,
        overall_accuracy=accuracy,
        category_accuracy=cat_acc,
        difficulty_breakdown=difficulty_breakdown,
        avg_summary_relevance=avg_summary,
        avg_semantic_similarity=avg_semantic,
        avg_latency_ms=avg_latency,
        avg_tokens=avg_tokens,
        avg_cost_usd=avg_cost,
        status="PASS",  # filled in after comparison
    )


def _build_trend_data(runs: list[EvalRun], window: int) -> dict:
    versions = [r.prompt_version for r in runs]
    accuracies = [r.overall_accuracy for r in runs]
    regressions = [r.regressions for r in runs]
    latencies = [r.avg_latency_ms for r in runs]
    tokens = [r.avg_tokens for r in runs]
    moving_avg = []
    for i in range(len(accuracies)):
        start = max(0, i - window + 1)
        chunk = accuracies[start:i + 1]
        moving_avg.append(sum(chunk) / len(chunk))
    return {
        "versions": versions, "accuracies": accuracies, "moving_avg": moving_avg,
        "regressions": regressions, "latencies": latencies, "tokens": tokens,
    }


def _send_alerts(run: EvalRun, comparison, drift, report_url: str, no_alerts: bool):
    if no_alerts:
        return
    should_alert = run.status != "PASS" or (drift and drift.is_drifting)
    if not should_alert:
        return
    sent = []
    if send_slack_alert(run, comparison, drift, report_url):
        sent.append("Slack")
    if send_discord_alert(run, comparison, drift, report_url):
        sent.append("Discord")
    if send_email_alert(run, comparison, drift, report_url):
        sent.append("Email")
    if sent:
        print(f"[cli] Alerts sent via: {', '.join(sent)}")


async def run_single(cfg: PromptConfig, dataset, dataset_path: str, no_alerts: bool,
                      quiet: bool = False) -> EvalRun:
    """Runs one eval and persists it. Used both by the normal single-run
    path and by the multi-provider loop (once per provider)."""
    storage.init_db()

    if not quiet:
        mode = "MOCK MODE" if settings.mock_mode or not settings.openai_api_key else f"{cfg.provider}/{cfg.model}"
        print(f"[cli] Running eval — prompt {cfg.version} on {len(dataset)} cases ({mode})...")

    case_results = await run_eval(cfg, dataset)

    baseline_run = storage.get_latest_run()
    baseline_case_results = storage.get_case_results(baseline_run.run_id) if baseline_run else None

    run = _aggregate(case_results, cfg.version, cfg.model, cfg.provider,
                      baseline_run.run_id if baseline_run else None)

    comparison = compare_runs(case_results, baseline_case_results)
    run.status = comparison.status
    run.regressions = len(comparison.regressions)
    run.improvements = len(comparison.improvements)
    run.no_change = comparison.no_change_count
    run.p_value = comparison.p_value
    run.statistically_significant = comparison.statistically_significant

    storage.save_run(run, case_results)
    print(f"[cli] Run {run.run_id} saved. Provider={run.provider} Status={run.status} "
          f"Accuracy={run.overall_accuracy:.1f}% "
          f"Regressions={run.regressions} Improvements={run.improvements}")

    all_runs = storage.get_all_runs(limit=1000)
    drift = check_drift(all_runs)
    if drift:
        print(f"[cli] {drift.message}")

    trend_data = _build_trend_data(all_runs[-7:], settings.drift_window)
    html = generate_report(
        run=run,
        baseline_run=baseline_run,
        current_cases=case_results,
        comparison=comparison if baseline_run else None,
        drift=drift,
        trend_data=trend_data,
        dataset_version=dataset_path,
    )
    report_path = save_report(html, run.run_id)
    print(f"[cli] Report written to {report_path}")

    report_url = f"{settings.report_base_url}/{run.run_id}.html"
    _send_alerts(run, comparison if baseline_run else None, drift, report_url, no_alerts)

    return run


async def main_async(prompt_path: str, dataset_path: str, no_alerts: bool,
                      provider_override: str | None, providers_list: list[str] | None) -> int:
    cfg = load_prompt_config(prompt_path)
    dataset = load_golden_dataset(dataset_path)

    if providers_list:
        # Multi-provider side-by-side: run the SAME prompt+dataset against
        # each provider in turn, tagging each resulting run distinctly so
        # they show up as separate, directly comparable rows in the
        # dashboard's Runs/Compare pages.
        print(f"[cli] Multi-provider run: {', '.join(providers_list)}")
        results = []
        worst_status = "PASS"
        for provider in providers_list:
            provider_cfg = cfg.model_copy(update={"provider": provider, "model": default_model_for(provider)})
            run = await run_single(provider_cfg, dataset, dataset_path, no_alerts)
            results.append(run)
            if run.status == "FAIL" or (run.status == "WARNING" and worst_status == "PASS"):
                worst_status = run.status

        print("\n[cli] Multi-provider summary:")
        print(f"{'Provider':<12} {'Model':<28} {'Accuracy':>10} {'Regressions':>13}")
        for r in results:
            print(f"{r.provider:<12} {r.model:<28} {r.overall_accuracy:>9.1f}% {r.regressions:>13}")

        return 1 if worst_status == "FAIL" else 0

    if provider_override:
        cfg = cfg.model_copy(update={"provider": provider_override, "model": default_model_for(provider_override)})

    run = await run_single(cfg, dataset, dataset_path, no_alerts)
    return 1 if run.status == "FAIL" else 0


def main():
    parser = argparse.ArgumentParser(description="LLM Model Regression Detection Pipeline")
    parser.add_argument("--prompt", required=True, help="Path to prompt YAML under test")
    parser.add_argument("--dataset", default=settings.dataset_path, help="Path to golden dataset JSON")
    parser.add_argument("--no-slack", "--no-alerts", dest="no_alerts", action="store_true",
                         help="Skip all alerting (Slack/Discord/email) even on FAIL")
    parser.add_argument("--provider", default=None, choices=SUPPORTED_PROVIDERS,
                         help="Override the prompt config's provider for this run "
                              "(uses that provider's default model)")
    parser.add_argument("--providers", default=None,
                         help=f"Comma-separated list of providers to run side-by-side "
                              f"(e.g. openai,anthropic,gemini). Choices: {SUPPORTED_PROVIDERS}")
    args = parser.parse_args()

    providers_list = None
    if args.providers:
        providers_list = [p.strip().lower() for p in args.providers.split(",") if p.strip()]
        invalid = [p for p in providers_list if p not in SUPPORTED_PROVIDERS]
        if invalid:
            print(f"[cli] Unknown provider(s): {invalid}. Supported: {SUPPORTED_PROVIDERS}", file=sys.stderr)
            sys.exit(2)

    exit_code = asyncio.run(main_async(args.prompt, args.dataset, args.no_alerts, args.provider, providers_list))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
