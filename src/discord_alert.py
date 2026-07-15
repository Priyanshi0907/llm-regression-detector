"""
Discord alerting via incoming webhook. Same trigger conditions as Slack
(WARNING/FAIL status, or a PASS run that still crossed the slow-drift
line) — this and slack_alert.py are intentionally structured identically
so adding a third channel later is a copy-paste-adapt job, not a rewrite.
"""
from __future__ import annotations
import requests

from src.config import settings
from src.models import EvalRun
from src.comparison import ComparisonResult
from src.drift import DriftStatus

STATUS_COLOR = {"PASS": 0x16A34A, "WARNING": 0xD97706, "FAIL": 0xDC2626}
STATUS_EMOJI = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "🚨"}


def build_discord_payload(
    run: EvalRun,
    comparison: ComparisonResult | None,
    drift: DriftStatus | None,
    report_url: str,
) -> dict:
    emoji = STATUS_EMOJI.get(run.status, "ℹ️")
    delta = comparison.overall_accuracy_delta if comparison else 0.0
    prev_accuracy = run.overall_accuracy - delta

    fields = [
        {"name": "Status", "value": run.status, "inline": True},
        {"name": "Prompt Version", "value": run.prompt_version, "inline": True},
        {"name": "Provider / Model", "value": f"{run.provider} / {run.model}", "inline": True},
        {"name": "Accuracy", "value": f"{prev_accuracy:.0f}% → {run.overall_accuracy:.0f}% ({delta:+.0f}%)", "inline": True},
        {"name": "Regressions", "value": str(run.regressions), "inline": True},
        {"name": "Improvements", "value": str(run.improvements), "inline": True},
    ]
    if run.statistically_significant and run.p_value is not None:
        fields.append({"name": "Statistical significance", "value": f"Yes (p = {run.p_value:.3f})", "inline": False})
    if drift and drift.is_drifting:
        fields.append({"name": "⏳ Slow drift check", "value": drift.message, "inline": False})

    embed = {
        "title": f"{emoji} Prompt Regression Bot — {run.status}",
        "url": report_url,
        "color": STATUS_COLOR.get(run.status, 0x6B7280),
        "fields": fields,
        "footer": {"text": "View full report → " + report_url},
    }
    return {"embeds": [embed]}


def send_discord_alert(run: EvalRun, comparison: ComparisonResult | None,
                        drift: DriftStatus | None, report_url: str) -> bool:
    if not settings.discord_webhook_url:
        print("[discord_alert] DISCORD_WEBHOOK_URL not set — skipping Discord notification.")
        return False

    payload = build_discord_payload(run, comparison, drift, report_url)
    try:
        resp = requests.post(settings.discord_webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[discord_alert] Failed to send Discord alert: {e}")
        return False
