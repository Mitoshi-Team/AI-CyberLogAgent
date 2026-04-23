"""GigaChat LLM provider."""

import logging
from typing import Any

from langchain_gigachat.chat_models import GigaChat as LangChainGigaChat

logger = logging.getLogger(__name__)


def create_gigachat_llm(
    api_key: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int | None = None,
    **kwargs: Any,
) -> LangChainGigaChat:
    """Create GigaChat LLM instance.

    Args:
        api_key: GigaChat API key
        model: Model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        timeout: Request timeout in seconds
        **kwargs: Additional arguments

    Returns:
        LangChain GigaChat instance

    """
    from ...config import AgentConfig

    cfg = AgentConfig.from_env()
    api_key = api_key or cfg.gigachat_api_key
    model = model or cfg.gigachat_model
    temperature = cfg.temperature if temperature is None else temperature
    max_tokens = cfg.max_tokens if max_tokens is None else max_tokens
    timeout = cfg.timeout if timeout is None else timeout

    logger.info(
        "Creating GigaChat LLM: model=%s, temp=%s, timeout=%ss",
        model,
        temperature,
        timeout,
    )

    llm = LangChainGigaChat(
        credentials=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        verify_ssl_certs=False,
        **kwargs,
    )

    logger.info("✓ GigaChat LLM created")
    return llm
