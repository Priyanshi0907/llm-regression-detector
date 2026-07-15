"""
Slack alerting via incoming webhook. Sends a structured message with
pass/warn/fail status, headline numbers, and a link to the full HTML report.
Silently no-ops if SLACK_WEBHOOK_URL isn't configured, so local/dev runs
don't fail just because Slack isn't wired up yet.
"""
from __future__ import annotations
import requests

from src.config import settings
from src.models import EvalRun
from src.comparison import ComparisonResult
from src.drift import DriftStatus

STATUS_EMOJI = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "🚨"}


def build_slack_payload(
    run: EvalRun,
    comparison: ComparisonResult | None,
    drift: DriftStatus | None,
    report_url: str,
) -> dict:
    emoji = STATUS_EMOJI.get(run.status, "ℹ️")
    delta = comparison.overall_accuracy_delta if comparison else 0.0
    prev_accuracy = run.overall_accuracy - delta

    headline = (
        f"{run.regressions} regression(s) detected, accuracy dropped from "
        f"{prev_accuracy:.0f}% to {run.overall_accuracy:.0f}%"
        if comparison and delta < 0 else
        f"Accuracy holding steady at {run.overall_accuracy:.0f}%"
    )

    blocks = [
        {"type": "header", "text": {"type": "plain_text",
         "text": f"{emoji} Prompt Regression Bot — {run.status}"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Status:*\n{run.status}"},
            {"type": "mrkdwn", "text": f"*Prompt Version:*\n{run.prompt_version}"},
            {"type": "mrkdwn", "text": f"*Model:*\n{run.model}"},
            {"type": "mrkdwn", "text": f"*Accuracy:*\n{prev_accuracy:.0f}% → {run.overall_accuracy:.0f}% ({delta:+.0f}%)"},
            {"type": "mrkdwn", "text": f"*Regressions:*\n{run.regressions}"},
            {"type": "mrkdwn", "text": f"*Improvements:*\n{run.improvements}"},
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{headline}*"}},
    ]

    if run.statistically_significant:
        blocks.append({"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"Statistical significance: Yes (p = {run.p_value:.3f})"}
        ]})

    if drift and drift.is_drifting:
        blocks.append({"type": "section", "text": {
            "type": "mrkdwn", "text": f":hourglass_flowing_sand: *Slow drift check: WARNING* — {drift.message}"
        }})

    blocks.append({"type": "section", "text": {
        "type": "mrkdwn", "text": f"<{report_url}|View Full Report →>"
    }})

    return {"blocks": blocks}


def send_slack_alert(run: EvalRun, comparison: ComparisonResult | None,
                      drift: DriftStatus | None, report_url: str) -> bool:
    if not settings.slack_webhook_url:
        print("[slack_alert] SLACK_WEBHOOK_URL not set — skipping Slack notification.")
        return False

    payload = build_slack_payload(run, comparison, drift, report_url)
    try:
        resp = requests.post(settings.slack_webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[slack_alert] Failed to send Slack alert: {e}")
        return False
