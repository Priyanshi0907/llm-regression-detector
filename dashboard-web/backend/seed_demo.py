"""
Auto-seed the DB with realistic demo data when it is empty.

Called by main.py on startup so the deployed dashboard always has
something to show, even on Render's ephemeral filesystem.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from src import storage
from src.models import EvalRun, CaseResult, Category, Difficulty


def _ts(days_ago: int) -> str:
    """ISO timestamp N days in the past."""
    return (datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- Golden dataset cases (subset for demo) ----
_CASES = [
    ("TC001", "I was charged $49.99 twice this month, can you refund the duplicate charge?", "billing", "Customer requests a refund for a duplicate subscription charge.", "easy"),
    ("TC002", "My invoice from last month shows the wrong plan tier, I'm on Basic not Pro.", "billing", "Customer reports their invoice reflects the wrong subscription tier.", "easy"),
    ("TC003", "Can you send me a copy of my receipt from March for tax purposes?", "billing", "Customer requests a copy of a past receipt.", "easy"),
    ("TC004", "Why did my subscription price go up without any warning?", "billing", "Customer is asking why their subscription price increased unexpectedly.", "easy"),
    ("TC005", "I want to cancel my subscription and get a prorated refund for the unused days.", "billing", "Customer wants to cancel and receive a prorated refund.", "easy"),
    ("TC006", "The coupon code SPRING20 isn't applying at checkout.", "billing", "Customer's discount coupon code is not applying at checkout.", "medium"),
    ("TC007", "My card on file expired, how do I update my payment method?", "billing", "Customer needs to update an expired payment method.", "easy"),
    ("TC008", "I never authorized this charge, this looks like fraud on my card.", "billing", "Customer disputes an unauthorized charge, suspecting fraud.", "medium"),
    ("TC009", "Do you offer annual billing with a discount instead of monthly?", "billing", "Customer asks about annual billing discount options.", "easy"),
    ("TC010", "I upgraded my plan yesterday but I'm still being billed at the old rate.", "billing", "Customer's plan upgrade isn't reflected in their billing rate.", "medium"),
    ("TC011", "The dashboard crashes every time I try to export a CSV file.", "technical", "Customer's dashboard crashes when exporting a CSV file.", "easy"),
    ("TC012", "I'm getting a 500 error whenever I try to upload a profile picture.", "technical", "Customer receives a 500 error uploading a profile picture.", "easy"),
    ("TC013", "The search bar returns zero results even for terms I know exist in my data.", "technical", "Customer's search feature returns no results for valid terms.", "easy"),
    ("TC014", "Your mobile app freezes on the loading screen after the latest update.", "technical", "Customer's mobile app freezes on load after an update.", "easy"),
    ("TC015", "The API is returning stale data, it hasn't updated in 3 days.", "technical", "Customer reports the API is returning outdated data.", "medium"),
    ("TC016", "Charts on my analytics page are rendering blank, just white space.", "technical", "Customer's analytics charts render as blank white space.", "easy"),
    ("TC017", "Notifications stopped working after I changed my timezone setting.", "technical", "Customer's notifications stopped after changing timezone settings.", "medium"),
    ("TC018", "The integration with Slack keeps disconnecting every few hours.", "technical", "Customer's Slack integration disconnects intermittently.", "easy"),
    ("TC019", "Bulk delete only removes half the selected items and then errors out.", "technical", "Customer's bulk delete feature partially fails with an error.", "easy"),
    ("TC020", "The site is painfully slow, pages take 10+ seconds to load today.", "technical", "Customer reports significant site-wide slowness.", "easy"),
    ("TC021", "I can't log in, it keeps saying my password is incorrect even after resetting it twice.", "account", "Customer cannot log in despite resetting their password twice.", "easy"),
    ("TC022", "How do I change the email address associated with my account?", "account", "Customer wants to update their account email address.", "easy"),
    ("TC023", "My account got locked after too many failed login attempts, please unlock it.", "account", "Customer's account is locked and needs to be unlocked.", "easy"),
    ("TC024", "I want to permanently delete my account and all associated data.", "account", "Customer requests permanent account and data deletion.", "easy"),
    ("TC025", "Can I merge two accounts I accidentally created with different emails?", "account", "Customer wants to merge two duplicate accounts.", "medium"),
    ("TC026", "Two-factor authentication isn't sending codes to my phone anymore.", "account", "Customer isn't receiving two-factor authentication codes.", "medium"),
    ("TC027", "I need to transfer account ownership to a coworker before I leave the company.", "account", "Customer wants to transfer account ownership to a coworker.", "medium"),
    ("TC028", "My username shows up as 'undefined' on my public profile.", "account", "Customer's username displays incorrectly as 'undefined' on their profile.", "hard"),
    ("TC029", "How do I add a second team member to manage the account with me?", "account", "Customer wants to add a team member to manage the account.", "easy"),
    ("TC030", "I never got the verification email when I signed up.", "account", "Customer did not receive their account verification email.", "medium"),
    ("TC031", "Just wanted to say the new dashboard redesign looks great, nice work!", "general", "Customer compliments the new dashboard redesign.", "easy"),
    ("TC032", "Do you have a public roadmap I can follow for upcoming features?", "general", "Customer asks whether a public product roadmap exists.", "easy"),
    ("TC033", "What are your support hours? I'm in the PST timezone.", "general", "Customer asks about support availability for PST timezone.", "easy"),
    ("TC034", "Is there a community forum or Slack group I can join?", "general", "Customer asks about community channels for users.", "easy"),
    ("TC035", "Could you add dark mode to the web app?", "general", "Customer requests a dark mode feature.", "easy"),
    ("TC036", "Do you have an affiliate or referral program?", "general", "Customer asks about a referral or affiliate program.", "easy"),
    ("TC037", "I'd love to schedule a demo for our team of 15 before deciding.", "general", "Customer requests a product demo for their team.", "easy"),
    ("TC038", "Where can I find your API documentation?", "general", "Customer asks for the location of API documentation.", "easy"),
    ("TC039", "Is your product HIPAA compliant for healthcare use cases?", "general", "Customer asks about HIPAA compliance.", "medium"),
    ("TC040", "We need a formal SOC 2 report before our procurement team can approve.", "general", "Customer requests a SOC 2 compliance report.", "medium"),
]

# Which test cases should *fail* per version (to create a realistic regression story)
_FAIL_MAP = {
    "v1": {"TC006", "TC008", "TC010", "TC015", "TC017", "TC025", "TC026", "TC027", "TC028", "TC030", "TC039", "TC040"},
    "v2": {"TC008", "TC010", "TC017", "TC025", "TC026", "TC028", "TC030", "TC039", "TC040"},
    "v3": {"TC008", "TC010", "TC017", "TC025", "TC026", "TC028", "TC030", "TC039", "TC040", "TC006"},
    "v4": {"TC008", "TC025", "TC028", "TC030", "TC039", "TC040"},
    "v5": {"TC008", "TC028", "TC039", "TC040"},
    "v6": {"TC028", "TC039", "TC040"},
    "v7": {"TC028", "TC039"},
    "v8": {"TC001", "TC005", "TC015", "TC025", "TC028", "TC039"},  # regression — more failures
}

_WRONG_CAT = {
    "billing": "general",
    "technical": "account",
    "account": "general",
    "general": "technical",
}

_RUN_CONFIGS = [
    # (version, provider, model, days_ago)
    ("v1", "openai", "gpt-4o-mini", 42),
    ("v2", "openai", "gpt-4o-mini", 35),
    ("v3", "openai", "gpt-4o-mini", 28),
    ("v4", "openai", "gpt-4o-mini", 21),
    ("v5", "openai", "gpt-4o-mini", 14),
    ("v6", "openai", "gpt-4o-mini", 7),
    ("v7", "openai", "gpt-4o-mini", 3),
    ("v8", "openai", "gpt-4o-mini", 1),
    ("v8", "anthropic", "claude-sonnet-4-20250514", 1),
    ("v8", "gemini", "gemini-2.5-flash", 0),
]


def _build_cases(version: str, run_id: str) -> list[CaseResult]:
    fails = _FAIL_MAP.get(version, set())
    results = []
    for i, (cid, inp, cat, summary, diff) in enumerate(_CASES):
        passed = cid not in fails
        actual_cat = cat if passed else _WRONG_CAT.get(cat, "general")
        results.append(CaseResult(
            case_id=cid,
            input=inp,
            expected_category=Category(cat),
            actual_category=Category(actual_cat),
            expected_summary=summary,
            actual_summary=summary if passed else f"Customer has a general inquiry about their {cat} issue.",
            expected_difficulty=Difficulty(diff),
            category_match=passed,
            summary_score=round(3.8 + (i % 5) * 0.2, 1) if passed else round(1.5 + (i % 4) * 0.3, 1),
            judge_rationale=(
                "Correctly classified; summary captures the primary intent and key entities."
                if passed else
                f"Category mismatch: expected '{cat}' but got '{actual_cat}'. Summary lost specificity."
            ),
            semantic_similarity=0.88 + (i % 10) * 0.01 if passed else 0.45 + (i % 10) * 0.02,
            semantic_similarity_is_real=False,
            confidence=82.0 + (i % 15) if passed else 42.0 + (i % 20),
            latency_ms=round(280 + (i * 17) % 200, 1),
            tokens_used=200 + (i * 23) % 150,
            passed=passed,
        ))
    return results


def seed_demo_data():
    """Insert demo runs + cases if the DB is empty."""
    existing = storage.get_all_runs(limit=1)
    if existing:
        return  # DB already has data, nothing to do

    prev_run_id = None
    for version, provider, model, days_ago in _RUN_CONFIGS:
        run_id = f"demo-{version}-{provider}-{_ts(days_ago)[:10]}"
        cases = _build_cases(version, run_id)

        passed = sum(1 for c in cases if c.passed)
        total = len(cases)
        accuracy = round(passed / total * 100, 1)

        cat_groups: dict[str, list[bool]] = {}
        for c in cases:
            cat_groups.setdefault(c.expected_category.value, []).append(c.category_match)
        cat_accuracy = {k: round(sum(v) / len(v) * 100, 1) for k, v in cat_groups.items()}

        diff_groups: dict[str, dict[str, int]] = {}
        for c in cases:
            d = c.expected_difficulty.value
            diff_groups.setdefault(d, {"passed": 0, "total": 0})
            diff_groups[d]["total"] += 1
            if c.passed:
                diff_groups[d]["passed"] += 1

        avg_latency = round(sum(c.latency_ms for c in cases) / total, 1)
        avg_tokens = round(sum(c.tokens_used for c in cases) / total, 1)
        avg_summary = round(sum(c.summary_score for c in cases) / total, 2)
        avg_cost = round(avg_tokens * 0.015 / 1000, 4)

        regressions = total - passed
        status = "PASS" if accuracy >= 90 else ("WARNING" if accuracy >= 80 else "FAIL")

        run = EvalRun(
            run_id=run_id,
            prompt_version=version,
            model=model,
            provider=provider,
            baseline_run_id=prev_run_id,
            timestamp=_ts(days_ago),
            total_cases=total,
            overall_accuracy=accuracy,
            category_accuracy=cat_accuracy,
            difficulty_breakdown=diff_groups,
            avg_summary_relevance=avg_summary,
            avg_semantic_similarity=0.82,
            avg_latency_ms=avg_latency,
            avg_tokens=avg_tokens,
            avg_cost_usd=avg_cost,
            status=status,
            regressions=regressions,
            improvements=0,
            no_change=passed,
            p_value=0.03 if regressions > 3 else 0.25,
            statistically_significant=regressions > 3,
        )

        storage.save_run(run, cases)
        prev_run_id = run_id

    print(f"[seed] Inserted {len(_RUN_CONFIGS)} demo runs with {len(_CASES)} cases each.")
