"""Base LLM provider factory."""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


def create_llm(
    provider: "LLMProvider",
    temperature: float = 0.1,
    max_tokens: int = 4000,
    timeout: int = 90,
    **kwargs: Any,
) -> BaseChatModel:
    """Create LLM instance based on provider type.

    Args:
        provider: LLM provider (OLLAMA)
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        timeout: Request timeout in seconds
        **kwargs: Provider-specific arguments

    Returns:
        LangChain BaseChatModel instance

    """
    # Lazy imports to avoid circular dependencies
    if provider.value == "ollama":
        from .ollama import create_ollama_llm

        return create_ollama_llm(
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )

    raise ValueError(f"Unknown LLM provider: {provider}")


# Re-export LLMProvider from config for convenience
def _get_provider_enum():
    """Lazy import of LLMProvider from config."""
    from ...config import LLMProvider

    return LLMProvider
