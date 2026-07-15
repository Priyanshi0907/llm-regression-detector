"""
The test runner: takes a PromptConfig + golden dataset, runs every case
through the LLM feature, and scores each one across multiple dimensions.

Uses async batching (bounded by MAX_CONCURRENCY) to keep wall-clock time
and cost down on larger datasets.
"""
from __future__ import annotations
import asyncio
import json

from src.config import settings
from src.llm_feature import classify_email
from src.judge import score_summary, semantic_similarity
from src.models import TestCase, CaseResult, PromptConfig


def load_golden_dataset(path: str) -> list[TestCase]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [TestCase(**c) for c in raw["cases"]]


async def _run_one_case(case: TestCase, cfg: PromptConfig, semaphore: asyncio.Semaphore) -> CaseResult:
    async with semaphore:
        output, latency_ms, tokens, error = await classify_email(case.input, cfg)

        if error or output is None:
            return CaseResult(
                case_id=case.id,
                input=case.input,
                expected_category=case.expected_category,
                actual_category=None,
                expected_summary=case.expected_summary,
                actual_summary=None,
                expected_difficulty=case.expected_difficulty,
                category_match=False,
                summary_score=1.0,
                judge_rationale=None,
                semantic_similarity=None,
                semantic_similarity_is_real=False,
                confidence=0.0,
                latency_ms=latency_ms,
                tokens_used=tokens,
                passed=False,
                error=error,
            )

        category_match = output.category == case.expected_category
        summary_score, rationale = await score_summary(case.expected_summary, output.summary)
        sem_sim, sem_is_real = await semantic_similarity(case.expected_summary, output.summary)
        passed = category_match and summary_score >= 3.0

        return CaseResult(
            case_id=case.id,
            input=case.input,
            expected_category=case.expected_category,
            actual_category=output.category,
            expected_summary=case.expected_summary,
            actual_summary=output.summary,
            expected_difficulty=case.expected_difficulty,
            category_match=category_match,
            summary_score=summary_score,
            judge_rationale=rationale,
            semantic_similarity=sem_sim,
            semantic_similarity_is_real=sem_is_real,
            confidence=output.confidence,
            latency_ms=latency_ms,
            tokens_used=tokens,
            passed=passed,
            error=None,
        )


async def run_eval(cfg: PromptConfig, dataset: list[TestCase]) -> list[CaseResult]:
    semaphore = asyncio.Semaphore(settings.max_concurrency)
    tasks = [_run_one_case(case, cfg, semaphore) for case in dataset]
    return await asyncio.gather(*tasks)
