"""LangChain wrapper for GigaChat."""

import logging
from typing import Any

from langchain_gigachat.chat_models import GigaChat as LangChainGigaChat

from log_ai_agent.config.cfg import GIGACHAT_API_KEY

logger = logging.getLogger(__name__)


def create_gigachat_llm(
    api_key: str = GIGACHAT_API_KEY,
    model: str = "GigaChat",
    temperature: float = 0.1,
    max_tokens: int = 4000,
    timeout: int = 90,
    **kwargs: Any,
) -> LangChainGigaChat:
    """Create GigaChat LLM instance.

    Args:
        api_key: GigaChat API key
        model: Model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        timeout: Request timeout
        **kwargs: Additional arguments

    Returns:
        LangChain GigaChat instance

    """
    logger.info(f"Creating GigaChat LLM: model={model}, temp={temperature}")

    llm = LangChainGigaChat(
        credentials=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        verify_ssl_certs=False,
        **kwargs,
    )

    logger.info("✓ GigaChat LLM created")
    return llm
