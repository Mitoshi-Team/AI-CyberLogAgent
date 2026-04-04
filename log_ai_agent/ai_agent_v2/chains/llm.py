"""LLM factory — unified entry point for creating language models."""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

from ..config import AgentConfig, LLMProvider
from .providers.base import create_llm as _create_llm_by_provider

logger = logging.getLogger(__name__)


def create_llm(
    provider: LLMProvider | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Create LLM instance based on configuration.

    Auto-detects provider based on available environment variables:
    - If OLLAMA_URL is set → uses Ollama (on-premise)
    - Otherwise → falls back to GigaChat (cloud)

    Args:
        provider: Force specific provider (optional)
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        timeout: Request timeout in seconds
        **kwargs: Provider-specific arguments

    Returns:
        LangChain BaseChatModel instance

    """
    cfg = AgentConfig.from_env()

    # Use provided provider or auto-detect
    if provider is None:
        provider = cfg.detected_provider

    temperature = cfg.temperature if temperature is None else temperature
    max_tokens = cfg.max_tokens if max_tokens is None else max_tokens
    timeout = cfg.timeout if timeout is None else timeout

    logger.info("Creating LLM: provider=%s", provider.value)

    return _create_llm_by_provider(
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        **kwargs,
    )


# Backward compatibility alias — old code imports create_gigachat_llm
def create_gigachat_llm(
    api_key: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Create GigaChat LLM instance (backward compatibility).

    Deprecated: Use create_llm() instead for provider-agnostic code.

    """
    from .providers.gigachat import create_gigachat_llm as _create_gigachat

    return _create_gigachat(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        **kwargs,
    )
