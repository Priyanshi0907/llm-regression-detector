"""
Deterministic mock provider. Used automatically whenever a real provider's
API key isn't configured, so demos (including multi-provider side-by-side
comparisons) work with zero API keys. Each provider gets a distinct-but-
deterministic bias so mock comparisons look like genuinely different model
behavior rather than three identical numbers with different labels.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import random
import time

from src.providers.base import LLMProvider, ProviderResponse

# Small per-provider bias so mock side-by-side comparisons are visually
# distinguishable — NOT a claim about real relative model quality.
_PROVIDER_BIAS = {
    "openai": {"ambiguous_error_rate": 0.35, "confidence_shift": 0},
    "anthropic": {"ambiguous_error_rate": 0.20, "confidence_shift": -4},
    "gemini": {"ambiguous_error_rate": 0.45, "confidence_shift": 3},
    "mock": {"ambiguous_error_rate": 0.35, "confidence_shift": 0},
}


class MockProvider(LLMProvider):
    def __init__(self, provider_name: str = "mock"):
        self.name = provider_name
        self.bias = _PROVIDER_BIAS.get(provider_name, _PROVIDER_BIAS["mock"])

    def is_available(self) -> bool:
        return True  # mock is always available — it's the universal fallback

    async def complete_json(self, system_prompt: str, user_message: str, model: str, task: str = "classify") -> ProviderResponse:
        start = time.perf_counter()
        if task == "judge":
            content, tokens = self._mock_judge(system_prompt, user_message)
        else:
            content, tokens = self._mock_classify(system_prompt, user_message)
        await asyncio.sleep(random.uniform(0.01, 0.05))
        latency_ms = (time.perf_counter() - start) * 1000
        return ProviderResponse(content=content, latency_ms=latency_ms, tokens_used=tokens)

    def _mock_judge(self, system_prompt: str, user_message: str) -> tuple[str, int]:
        """Deterministic stand-in for LLM-as-judge scoring. Scores by
        content-word overlap between the expected and actual summaries
        embedded in `user_message` — a cheap proxy for semantic similarity,
        good enough to make mock-mode regressions/improvements look
        realistic without ever calling a real judge model."""
        seed = int(hashlib.sha256((self.name + system_prompt + user_message).encode()).hexdigest(), 16)
        rnd = random.Random(seed)
        stopwords = {"customer", "the", "a", "an", "to", "for", "of", "and", "is", "on",
                     "their", "in", "with", "message", "regarding", "writes", "about"}
        lines = user_message.lower().split("\n")
        expected = next((l for l in lines if "expected" in l), "")
        actual = next((l for l in lines if "actual" in l), "")
        exp_tokens = {w.strip(".,!?") for w in expected.split()} - stopwords
        act_tokens = {w.strip(".,!?") for w in actual.split()} - stopwords
        if not exp_tokens or not act_tokens:
            score = round(rnd.uniform(3.0, 4.0), 1)
        else:
            overlap = len(exp_tokens & act_tokens) / max(len(exp_tokens), 1)
            base = 3.0 + overlap * 2.5
            score = round(min(5.0, max(1.0, base + rnd.uniform(-0.5, 0.5))), 1)
        rationale = f"Mock judge ({self.name}): content-word overlap heuristic, no real model call."
        tokens = len(system_prompt.split()) + len(user_message.split())
        return json.dumps({"score": score, "rationale": rationale}), tokens

    def _mock_classify(self, system_prompt: str, user_message: str) -> tuple[str, int]:
        text = user_message.lower()

        billing_kw = ["charge", "invoice", "refund", "payment", "billed", "subscription",
                      "receipt", "coupon", "discount", "price", "pricing", "plan tier",
                      "card", "card details", "prorated", "overage", "annual billing"]
        technical_kw = ["error", "bug", "crash", "not working", "won't load", "wont load",
                        "500", "broken", "freeze", "freezes", "spinning", "spining",
                        "search bar", "zero results", "stale data", "blank", "disconnect",
                        "slow", "loading", "export button", "checklist", "notification",
                        "greyed out", "api is", "integration"]
        account_kw = ["password", "log in", "login", "account locked", "delete my account",
                      "update my email", "username", "verification email", "two-factor",
                      "2fa", "merge two accounts", "transfer account", "team member",
                      "login history", "account language", "email address associated"]

        if any(k in text for k in billing_kw):
            category = "billing"
        elif any(k in text for k in technical_kw):
            category = "technical"
        elif any(k in text for k in account_kw):
            category = "account"
        else:
            category = "general"

        seed = int(hashlib.sha256((self.name + system_prompt + user_message).encode()).hexdigest(), 16)
        rnd = random.Random(seed)

        if "concise" in system_prompt.lower() and category == "account" and rnd.random() < self.bias["ambiguous_error_rate"]:
            category = "general"

        summary = self._mock_summary(user_message)
        confidence = self._mock_confidence(seed, category, text)
        tokens = len(system_prompt.split()) + len(user_message.split()) + len(summary.split())
        content = json.dumps({"category": category, "summary": summary, "confidence": confidence})
        return content, tokens

    @staticmethod
    def _mock_summary(user_message: str) -> str:
        words = user_message.strip().rstrip("?!.").split()
        snippet = " ".join(words[:16]).lower()
        return f"Customer message regarding: {snippet}"

    def _mock_confidence(self, seed: int, category: str, text: str) -> float:
        rnd = random.Random(seed + 1)
        word_count = len(text.split())
        if word_count <= 3:
            base = rnd.uniform(45, 65)
        elif category == "general":
            base = rnd.uniform(55, 80)
        else:
            base = rnd.uniform(82, 99)
        base += self.bias["confidence_shift"]
        return round(min(99.0, max(30.0, base)), 1)
