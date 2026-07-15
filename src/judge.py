"""
LLM-as-judge scoring, now driven by a configurable rubric instead of a
hardcoded prompt, plus an optional second scoring dimension: embeddings-
based semantic similarity. These are deliberately kept as two separate
scores rather than merged into one number — they measure different things
(judge = holistic reasoning about correctness; semantic similarity = raw
distributional closeness of the text) and disagreement between them is
itself a useful signal.
"""
from __future__ import annotations
import json
import math
from functools import lru_cache
from pathlib import Path

import yaml

from src.config import settings
from src.providers.registry import get_provider


@lru_cache(maxsize=1)
def load_rubric(path: str | None = None) -> dict:
    rubric_path = Path(path or settings.rubric_path)
    if not rubric_path.exists():
        # Fall back to a minimal built-in rubric rather than crashing —
        # a missing rubric file shouldn't take down the whole eval run.
        return {
            "criteria": [
                {"name": "Overall relevance", "description": "Does the summary capture the customer's intent?", "weight": 1.0}
            ],
            "scoring_scale": "1 (unrelated) to 5 (equivalent meaning)",
        }
    with open(rubric_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_judge_prompt(expected: str, actual: str, rubric: dict) -> str:
    criteria_lines = "\n".join(
        f"- {c['name']} (weight {c.get('weight', 1.0)}): {c['description']}"
        for c in rubric.get("criteria", [])
    )
    scale = rubric.get("scoring_scale", "1 (unrelated) to 5 (equivalent meaning)")
    return (
        "You are a strict evaluator scoring how well an actual summary "
        "captures the same meaning as an expected summary, using this rubric:\n\n"
        f"{criteria_lines}\n\n"
        f"Score on a scale of {scale}, weighing the criteria above according "
        "to their weights.\n\n"
        f"Expected summary: {expected}\n"
        f"Actual summary: {actual}\n\n"
        'Respond ONLY with JSON: {"score": <number 1-5>, "rationale": "<one sentence citing which criteria drove the score>"}'
    )


async def score_summary(expected: str, actual: str, rubric_path: str | None = None) -> tuple[float, str]:
    """Returns (score, rationale) using the configured judge provider and rubric."""
    if not actual:
        return 1.0, "No summary was generated."

    rubric = load_rubric(rubric_path)
    prompt = _build_judge_prompt(expected, actual, rubric)
    provider = get_provider(settings.judge_provider)

    response = await provider.complete_json(
        system_prompt="You are a rubric-driven evaluation judge. Follow the rubric exactly.",
        user_message=prompt,
        model=settings.judge_model,
        task="judge",
    )
    try:
        data = json.loads(response.content)
        return float(data.get("score", 3.0)), data.get("rationale", "")
    except (json.JSONDecodeError, TypeError, ValueError):
        return 3.0, "Judge response could not be parsed; defaulted to 3.0."


# ---------------------------------------------------------------------------
# Optional second dimension: embeddings-based semantic similarity.
# Disabled by default (SEMANTIC_SIMILARITY_ENABLED=false) since it's an
# extra API call per case. When disabled, or in mock mode, falls back to a
# deterministic token-overlap approximation so the field is never just
# absent from the schema — it's clearly labeled as an approximation instead.
# ---------------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _token_overlap_fallback(expected: str, actual: str) -> float:
    exp_tokens = set(expected.lower().split())
    act_tokens = set(actual.lower().split())
    if not exp_tokens or not act_tokens:
        return 0.0
    return len(exp_tokens & act_tokens) / len(exp_tokens | act_tokens)


async def semantic_similarity(expected: str, actual: str) -> tuple[float, bool]:
    """Returns (similarity 0-1, used_real_embeddings). Real embeddings only
    fire when semantic_similarity_enabled is on AND an OpenAI key is
    configured (embeddings currently only routed through OpenAI regardless
    of the feature/judge provider, since it's a separate, cheap endpoint)."""
    if not actual:
        return 0.0, False

    if not settings.semantic_similarity_enabled or settings.mock_mode or not settings.openai_api_key:
        return _token_overlap_fallback(expected, actual), False

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.embeddings.create(model=settings.embedding_model, input=[expected, actual])
        vec_expected = resp.data[0].embedding
        vec_actual = resp.data[1].embedding
        return _cosine_similarity(vec_expected, vec_actual), True
    except Exception:  # noqa: BLE001 — never let an embeddings hiccup kill the eval run
        return _token_overlap_fallback(expected, actual), False
