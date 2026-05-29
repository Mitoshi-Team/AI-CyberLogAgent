"""LLM factory — unified entry point for creating language models."""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

from ..config import AgentConfig, LLMProvider
from .providers.base import create_llm as _create_llm_by_provider

logger = logging.getLogger(__name__)

_active_model: str | None = None


def set_active_model(model: str | None) -> None:
    """Override LLM model name at runtime (no restart needed)."""
    global _active_model
    _active_model = model
    if model:
        logger.info("Runtime model set: %s", model)
    else:
        logger.info("Runtime model cleared, using env default")


def get_active_model() -> str | None:
    """Return runtime model override, or None to use env default."""
    return _active_model


def get_effective_model() -> str:
    """Return the model name that will be used by the LLM.

    Priority: runtime override > env var > config default.

    """
    runtime = get_active_model()
    if runtime:
        return runtime
    cfg = AgentConfig.from_env()
    if cfg.detected_provider == LLMProvider.AITUNNEL:
        return cfg.aitunnel_model
    return cfg.ollama_model


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
    - If AITUNNEL_API_KEY is set → uses AITUNNEL (cloud API)

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

    if provider is None:
        provider = cfg.detected_provider

    temperature = cfg.temperature if temperature is None else temperature
    max_tokens = cfg.max_tokens if max_tokens is None else max_tokens
    timeout = cfg.timeout if timeout is None else timeout

    runtime_model = get_active_model()
    if runtime_model:
        if provider == LLMProvider.AITUNNEL:
            kwargs.setdefault("model", runtime_model)
            logger.info("Using runtime model for AITUNNEL: %s", runtime_model)
        elif provider == LLMProvider.OLLAMA:
            kwargs.setdefault("model", runtime_model)
            logger.info("Using runtime model for Ollama: %s", runtime_model)

    logger.info("Creating LLM: provider=%s", provider.value)

    return _create_llm_by_provider(
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        **kwargs,
    )


