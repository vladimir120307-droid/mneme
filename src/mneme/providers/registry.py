"""Provider lookup by short name."""

from __future__ import annotations

import os

from mneme.providers.anthropic import AnthropicProvider
from mneme.providers.base import LLMProvider
from mneme.providers.ollama import OllamaProvider
from mneme.providers.openai_compat import OpenAICompatibleProvider


def get_provider(name: str, **kwargs: object) -> LLMProvider:
    """Resolve a provider by short name.

    Recognised names: ``ollama``, ``openai``, ``anthropic``,
    ``openrouter``, ``lmstudio``, ``vllm``.
    """
    name = name.lower()
    if name == "ollama":
        return OllamaProvider(
            base_url=str(kwargs.get("base_url")
                         or os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
        )
    if name == "openai":
        return OpenAICompatibleProvider(
            base_url=str(kwargs.get("base_url") or "https://api.openai.com/v1"),
            api_key=kwargs.get("api_key"),  # type: ignore[arg-type]
        )
    if name == "openrouter":
        return OpenAICompatibleProvider(
            base_url="https://openrouter.ai/api/v1",
            api_key=kwargs.get("api_key") or os.environ.get("OPENROUTER_API_KEY"),  # type: ignore[arg-type]
        )
    if name == "lmstudio":
        return OpenAICompatibleProvider(
            base_url=str(kwargs.get("base_url") or "http://localhost:1234/v1"),
            api_key="lm-studio",
        )
    if name == "vllm":
        return OpenAICompatibleProvider(
            base_url=str(kwargs.get("base_url") or "http://localhost:8000/v1"),
            api_key=kwargs.get("api_key") or "EMPTY",  # type: ignore[arg-type]
        )
    if name == "anthropic":
        return AnthropicProvider(api_key=kwargs.get("api_key"))  # type: ignore[arg-type]
    raise ValueError(
        f"Unknown provider '{name}'. "
        "Try: ollama, openai, anthropic, openrouter, lmstudio, vllm."
    )
