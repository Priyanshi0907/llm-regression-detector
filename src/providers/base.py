"""
Provider abstraction so the eval engine doesn't care whether it's talking
to OpenAI, Anthropic, Gemini, or the deterministic mock. Every adapter
implements this same interface; src/eval_runner.py and src/llm_feature.py
only ever talk to this interface, never to a specific SDK directly.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResponse:
    content: str  # raw text — caller is responsible for JSON parsing
    latency_ms: float
    tokens_used: int


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def complete_json(self, system_prompt: str, user_message: str, model: str, task: str = "classify") -> ProviderResponse:
        """Call the model and return its raw text response, which the
        caller expects to be a JSON object (per the prompt's instructions).
        Providers are responsible for requesting JSON output however their
        SDK supports it, but NOT for parsing it — that's the caller's job,
        so parsing errors surface consistently regardless of provider.

        `task` is "classify" (the feature under test) or "judge" (scoring).
        Real providers ignore it — they just send whatever prompt they're
        given. The mock provider uses it to pick the right heuristic, since
        it can't actually reason about either task."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """True if this provider has the credentials/SDK needed to make
        real calls. False means the caller should fall back to mock
        behavior for this provider rather than erroring out — this is
        what lets a side-by-side provider comparison run in Demo Mode
        without requiring three separate API keys."""
        ...
