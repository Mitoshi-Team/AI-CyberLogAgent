"""Ollama LLM provider."""

import logging
from typing import Any

from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


def create_ollama_llm(
    model: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int | None = None,
    **kwargs: Any,
) -> ChatOllama:
    """Create Ollama LLM instance.

    Args:
        model: Model name (e.g. qwen2.5:7b, llama3.1:8b)
        base_url: Ollama server URL (e.g. http://192.168.1.100:11434)
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        timeout: Request timeout in seconds
        **kwargs: Additional arguments passed to ChatOllama

    Returns:
        LangChain ChatOllama instance

    """
    from ...config import AgentConfig

    cfg = AgentConfig.from_env()

    model = model or cfg.ollama_model
    base_url = base_url or cfg.ollama_url
    temperature = cfg.temperature if temperature is None else temperature
    max_tokens = cfg.max_tokens if max_tokens is None else max_tokens
    timeout = cfg.timeout if timeout is None else timeout

    logger.info(
        "Creating Ollama LLM: model=%s, base_url=%s, temp=%s, timeout=%ss",
        model,
        base_url,
        temperature,
        timeout,
    )

    llm = ChatOllama(
        model=model,
        base_url=base_url,
        temperature=temperature,
        num_predict=max_tokens,
        timeout=timeout,
        **kwargs,
    )

    logger.info("✓ Ollama LLM created: %s @ %s", model, base_url)
    return llm
