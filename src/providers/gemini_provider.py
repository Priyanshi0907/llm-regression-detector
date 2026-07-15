"""
Google Gemini provider adapter, via the official `google-genai` SDK.
Uses response_mime_type='application/json' for structured output, which
Gemini supports natively (similar guarantee level to OpenAI's JSON mode).
"""
from __future__ import annotations
import time

from src.providers.base import LLMProvider, ProviderResponse
from src.config import settings

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover
    genai = None
    genai_types = None


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self):
        self._client = None
        if genai is not None and settings.gemini_api_key:
            self._client = genai.Client(api_key=settings.gemini_api_key)

    def is_available(self) -> bool:
        return self._client is not None

    async def complete_json(self, system_prompt: str, user_message: str, model: str, task: str = "classify") -> ProviderResponse:
        start = time.perf_counter()
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0,
            ),
        )
        latency_ms = (time.perf_counter() - start) * 1000
        content = response.text
        usage = response.usage_metadata
        tokens = (usage.prompt_token_count + usage.candidates_token_count) if usage else 0
        return ProviderResponse(content=content, latency_ms=latency_ms, tokens_used=tokens)
