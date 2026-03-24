"""Callback handlers for LangChain logging."""

import logging
import time
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


class ConsoleCallbackHandler(BaseCallbackHandler):
    """Callback handler for console output.

    Prints chain execution steps to console with timing.
    """

    def __init__(self, show_output: bool = False):
        """Initialize callback handler.

        Args:
            show_output: Whether to show full output (default: False)

        """
        super().__init__()
        self.show_output = show_output
        self._chain_start_times: dict[UUID, float] = {}

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run when chain starts."""
        self._chain_start_times[run_id] = time.time()

        chain_name = serialized.get("name", "Unknown") if serialized else "Unknown"
        if not parent_run_id:  # Only show top-level chains
            logger.info(f"▶ Starting: {chain_name}")

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run when chain ends."""
        start_time = self._chain_start_times.get(run_id)
        duration = time.time() - start_time if start_time else 0

        chain_name = "Unknown"  # serialized not available in on_chain_end
        if not parent_run_id:  # Only show top-level chains
            logger.info(f"✓ Completed: {chain_name} ({duration:.2f}s)")

        if self.show_output and outputs:
            for key, value in outputs.items():
                if isinstance(value, str) and len(value) > 200:
                    value = value[:200] + "..."
                logger.debug(f"  {key}: {value}")

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run when chain errors."""
        if not parent_run_id:
            logger.error(
                "✗ Error: Chain failed - %s (%r)",
                type(error).__name__,
                error,
            )

    def on_llm_start(
        self,
        serialized: dict[str, Any] | None,
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run when LLM starts."""
        if not parent_run_id:
            logger.debug("▶ LLM call started")

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run when LLM ends."""
        if not parent_run_id:
            logger.debug("✓ LLM call completed")

    def on_retriever_start(
        self,
        serialized: dict[str, Any] | None,
        query: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run when retriever starts."""
        if not parent_run_id:
            logger.info(f"▶ RAG search: {query[:50]}...")

    def on_retriever_end(
        self,
        documents: Sequence[Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run when retriever ends."""
        if not parent_run_id:
            logger.info(f"✓ RAG found {len(documents)} documents")


def get_callback_config(show_output: bool = False) -> dict:
    """Get callback configuration for LangChain.

    Args:
        show_output: Whether to show full output

    Returns:
        Config dict with callbacks

    """
    return {
        "callbacks": [ConsoleCallbackHandler(show_output=show_output)],
    }
