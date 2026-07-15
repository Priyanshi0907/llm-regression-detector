"""OpenAI provider adapter."""
from __future__ import annotations
import time

from src.providers.base import LLMProvider, ProviderResponse
from src.config import settings

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover
    AsyncOpenAI = None


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self):
        self._client = None
        if AsyncOpenAI is not None and settings.openai_api_key:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    def is_available(self) -> bool:
        return self._client is not None

    async def complete_json(self, system_prompt: str, user_message: str, model: str, task: str = "classify") -> ProviderResponse:
        start = time.perf_counter()
        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        return ProviderResponse(content=content, latency_ms=latency_ms, tokens_used=tokens)
