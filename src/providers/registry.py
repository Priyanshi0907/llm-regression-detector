"""
Provider registry. get_provider(name) returns the real adapter if it has
credentials configured, otherwise transparently falls back to a mock
adapter tagged with that provider's name — this is what lets a
multi-provider side-by-side comparison run in Demo Mode with zero API
keys, while still behaving identically (same call signatures, same
downstream code path) once real keys are added.
"""
from __future__ import annotations

from src.config import settings
from src.providers.base import LLMProvider
from src.providers.mock_provider import MockProvider
from src.providers.openai_provider import OpenAIProvider
from src.providers.anthropic_provider import AnthropicProvider
from src.providers.gemini_provider import GeminiProvider

SUPPORTED_PROVIDERS = ["openai", "anthropic", "gemini"]

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    "gemini": "gemini-2.0-flash",
}

_REAL_ADAPTERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}

_cache: dict[str, LLMProvider] = {}


def get_provider(name: str) -> LLMProvider:
    """Returns a real provider adapter if credentials are configured and
    MOCK_MODE is off; otherwise returns a mock adapter tagged with `name`
    so downstream code (run metadata, comparisons) still reflects which
    provider was requested, even though the call itself is simulated."""
    name = name.lower()
    if name not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unknown provider '{name}'. Supported: {SUPPORTED_PROVIDERS}")

    cache_key = name
    if cache_key in _cache:
        return _cache[cache_key]

    force_mock = settings.mock_mode
    adapter: LLMProvider
    if not force_mock:
        real = _REAL_ADAPTERS[name]()
        adapter = real if real.is_available() else MockProvider(provider_name=name)
    else:
        adapter = MockProvider(provider_name=name)

    _cache[cache_key] = adapter
    return adapter


def default_model_for(provider: str) -> str:
    return DEFAULT_MODELS.get(provider.lower(), DEFAULT_MODELS["openai"])
