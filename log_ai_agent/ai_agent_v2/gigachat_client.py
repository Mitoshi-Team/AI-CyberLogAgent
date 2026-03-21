"""Async client for GigaChat API using official SDK."""

import asyncio
import logging
from typing import Optional

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from log_ai_agent.config.cfg import GIGACHAT_API_KEY

logger = logging.getLogger(__name__)


class GigaChatAPIError(Exception):
    """Exception raised for GigaChat API errors."""

    pass


class GigaChatClient:
    """
    Async wrapper for GigaChat SDK.
    
    Features:
    - Uses official GigaChat SDK
    - Async support via asyncio.to_thread
    - Retry logic
    - Rate limiting
    """

    def __init__(
        self,
        api_key: str = GIGACHAT_API_KEY,
        model: str = "GigaChat",
        temperature: float = 0.1,
        max_tokens: int = 4000,
        timeout: int = 60,
        max_retries: int = 3,
        rate_limit_delay: float = 0.5,
    ):
        """
        Initialize GigaChat client.

        Args:
            api_key: GigaChat API key (credentials)
            model: Model name to use
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            rate_limit_delay: Delay between requests to avoid rate limiting
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay

    async def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send chat request to GigaChat.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt override
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override
            
        Returns:
            Assistant response text
        """
        # Rate limiting
        await asyncio.sleep(self.rate_limit_delay)
        
        # Build messages array
        chat_messages = []
        
        if system_prompt:
            chat_messages.append(Messages(role=MessagesRole.SYSTEM, content=system_prompt))
        
        # Add user/assistant messages
        for msg in messages:
            role = MessagesRole.USER if msg.get("role") == "user" else MessagesRole.ASSISTANT
            chat_messages.append(Messages(role=role, content=msg["content"]))
        
        # Create chat request
        chat_request = Chat(
            model=self.model,
            messages=chat_messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )
        
        logger.debug(f"GigaChat request: {len(messages)} messages, temp={temperature or self.temperature}")
        
        # Run sync SDK call in thread pool
        def _sync_chat():
            with GigaChat(
                credentials=self.api_key,
                scope="GIGACHAT_API_PERS",
                verify_ssl_certs=False,
            ) as giga:
                response = giga.chat(chat_request)
                return response.choices[0].message.content
        
        try:
            response = await asyncio.to_thread(_sync_chat)
            logger.info(f"GigaChat response: {len(response)} chars")
            return response
            
        except Exception as e:
            logger.error(f"GigaChat chat error: {e}")
            raise GigaChatAPIError(f"GigaChat API error: {e}")

    async def chat_with_retry(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> str:
        """
        Send chat request with explicit retry control.
        
        Args:
            messages: List of message dicts
            system_prompt: Optional system prompt
            temperature: Optional temperature
            max_tokens: Optional max tokens
            max_retries: Override default max retries
            
        Returns:
            Assistant response text
        """
        retries = max_retries or self.max_retries
        
        for attempt in range(retries + 1):
            try:
                return await self.chat(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except GigaChatAPIError as e:
                if attempt == retries:
                    logger.error(f"GigaChat failed after {retries + 1} attempts: {e}")
                    raise
                logger.warning(f"GigaChat attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # Should never reach here
        raise GigaChatAPIError("Unexpected retry loop exit")

    async def close(self):
        """Close client resources (no-op for SDK)."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
