"""
Anthropic (Claude) provider adapter.

Claude doesn't have a strict JSON-mode flag like OpenAI's response_format,
so we instruct it firmly in the prompt (the existing prompt YAMLs already
say "Respond ONLY with JSON") and strip common wrapping (markdown code
fences) before handing the text back. Parsing/validation still happens
one layer up in llm_feature.py, same as every other provider.
"""
from __future__ import annotations
import time

from src.providers.base import LLMProvider, ProviderResponse
from src.config import settings

try:
    from anthropic import AsyncAnthropic
except ImportError:  # pragma: no cover
    AsyncAnthropic = None


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self):
        self._client = None
        if AsyncAnthropic is not None and settings.anthropic_api_key:
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    def is_available(self) -> bool:
        return self._client is not None

    async def complete_json(self, system_prompt: str, user_message: str, model: str, task: str = "classify") -> ProviderResponse:
        start = time.perf_counter()
        response = await self._client.messages.create(
            model=model,
            max_tokens=500,
            temperature=0,
            system=system_prompt + '\n\nRespond with ONLY the raw JSON object, no markdown formatting, no code fences.',
            messages=[{"role": "user", "content": user_message}],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        content = _strip_code_fence(response.content[0].text)
        tokens = (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
        return ProviderResponse(content=content, latency_ms=latency_ms, tokens_used=tokens)
