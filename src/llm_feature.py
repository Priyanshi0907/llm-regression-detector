"""
The LLM-powered feature under test: a customer support email classifier.

This is intentionally a single, simple function — the point of the project
isn't the feature itself, it's the eval/regression harness wrapped around it.
The prompt AND the provider are both externalized (see /prompts/*.yaml), so
swapping prompt versions or swapping providers (OpenAI/Anthropic/Gemini)
never requires touching this code.
"""
from __future__ import annotations
import json
import yaml
from pathlib import Path

from src.providers.registry import get_provider
from src.models import PromptConfig, ClassifierOutput, FewShotExample


def load_prompt_config(path: str | Path) -> PromptConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return PromptConfig(**raw)


def _build_system_prompt(cfg: PromptConfig) -> str:
    prompt = cfg.system_prompt.strip()
    if cfg.few_shot_examples:
        examples_txt = "\n\n".join(
            f"Example input: {ex.input}\nExample output: {ex.output}"
            for ex in cfg.few_shot_examples
        )
        prompt = f"{prompt}\n\nFew-shot examples:\n{examples_txt}"
    return prompt


async def classify_email(email_text: str, cfg: PromptConfig) -> tuple[ClassifierOutput | None, float, int, str | None]:
    """
    Runs one email through the classifier feature, via whichever provider
    the prompt config specifies (cfg.provider — openai/anthropic/gemini).
    Returns (output, latency_ms, tokens_used, error).
    """
    system_prompt = _build_system_prompt(cfg)
    provider = get_provider(cfg.provider)
    try:
        resp = await provider.complete_json(system_prompt, email_text, model=cfg.model, task="classify")
        data = json.loads(resp.content)
        output = ClassifierOutput(
            category=data["category"],
            summary=data["summary"],
            confidence=float(data.get("confidence", 0.0)),
        )
        return output, resp.latency_ms, resp.tokens_used, None
    except Exception as e:  # noqa: BLE001 - we want to capture and record ANY failure
        return None, 0.0, 0, str(e)

