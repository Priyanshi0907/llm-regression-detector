"""
Email alerting via plain SMTP (stdlib smtplib — no extra dependency).
Same trigger conditions as Slack/Discord. Configure EMAIL_SMTP_* and
EMAIL_TO in .env; EMAIL_TO accepts a comma-separated list for multiple
recipients (e.g. a whole team's distribution list).
"""
from __future__ import annotations
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import settings
from src.models import EvalRun
from src.comparison import ComparisonResult
from src.drift import DriftStatus

STATUS_EMOJI = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "🚨"}


def build_email_body(
    run: EvalRun,
    comparison: ComparisonResult | None,
    drift: DriftStatus | None,
    report_url: str,
) -> tuple[str, str]:
    """Returns (subject, plain-text body)."""
    emoji = STATUS_EMOJI.get(run.status, "ℹ️")
    delta = comparison.overall_accuracy_delta if comparison else 0.0
    prev_accuracy = run.overall_accuracy - delta

    subject = f"{emoji} [{run.status}] Prompt eval — {run.prompt_version} ({run.provider}/{run.model})"

    lines = [
        f"Status: {run.status}",
        f"Prompt version: {run.prompt_version}",
        f"Provider / model: {run.provider} / {run.model}",
        f"Accuracy: {prev_accuracy:.0f}% -> {run.overall_accuracy:.0f}% ({delta:+.0f}%)",
        f"Regressions: {run.regressions}",
        f"Improvements: {run.improvements}",
    ]
    if run.statistically_significant and run.p_value is not None:
        lines.append(f"Statistical significance: Yes (p = {run.p_value:.3f})")
    if drift and drift.is_drifting:
        lines.append(f"\nSlow drift check: {drift.message}")
    lines.append(f"\nFull report: {report_url}")

    return subject, "\n".join(lines)


def send_email_alert(run: EvalRun, comparison: ComparisonResult | None,
                      drift: DriftStatus | None, report_url: str) -> bool:
    if not (settings.email_smtp_host and settings.email_from and settings.email_to):
        print("[email_alert] EMAIL_SMTP_HOST / EMAIL_FROM / EMAIL_TO not fully set — skipping email notification.")
        return False

    subject, body = build_email_body(run, comparison, drift, report_url)
    recipients = [addr.strip() for addr in settings.email_to.split(",") if addr.strip()]

    msg = MIMEMultipart()
    msg["From"] = settings.email_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port, timeout=10) as server:
            server.starttls()
            if settings.email_smtp_user and settings.email_smtp_password:
                server.login(settings.email_smtp_user, settings.email_smtp_password)
            server.sendmail(settings.email_from, recipients, msg.as_string())
        return True
    except Exception as e:  # noqa: BLE001 — never let alerting take down the eval run
        print(f"[email_alert] Failed to send email alert: {e}")
        return False
