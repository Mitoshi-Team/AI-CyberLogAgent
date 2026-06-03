"""LLM provider implementations.

Lazy imports to avoid requiring all provider dependencies at once.
"""

__all__ = [
    "create_llm",
    "create_ollama_llm",
]


def __getattr__(name: str):
    """Lazy attribute access for provider functions."""
    if name == "create_ollama_llm":
        from .ollama import create_ollama_llm

        return create_ollama_llm
    if name == "create_llm":
        from .base import create_llm

        return create_llm
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
