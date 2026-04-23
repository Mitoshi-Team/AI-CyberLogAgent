"""Configuration for AI Agent v2."""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    GIGACHAT = "gigachat"


def _detect_provider(
    ollama_url: str | None = None,
    gigachat_api_key: str | None = None,
) -> LLMProvider:
    """Detect which LLM provider to use based on available configuration.

    Priority:
    1. Ollama — if ollama_url is provided (on-premise)
    2. GigaChat — fallback if GIGACHAT_API_KEY is available

    """
    if ollama_url and ollama_url.strip():
        return LLMProvider.OLLAMA
    if gigachat_api_key and gigachat_api_key.strip():
        return LLMProvider.GIGACHAT
    raise ValueError(
        "No LLM provider configured. "
        "Set either OLLAMA_URL (for local/on-premise Ollama server) "
        "or GIGACHAT_API_KEY (for cloud GigaChat)."
    )


@dataclass
class AgentConfig:
    """Configuration for AI Agent v2."""

    # GigaChat settings
    gigachat_api_key: str = ""
    gigachat_model: str = "GigaChat-2-Max"

    # Ollama settings
    ollama_url: str = ""
    ollama_model: str = ""

    # Common LLM settings
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 90

    # RAG settings
    use_rag: bool = True
    rag_top_k: int = 5

    # ChromaDB settings
    chroma_path: str = ""
    chroma_collection: str = "mitre_collection"

    # Embedding settings
    embedding_model: str = "intfloat/multilingual-e5-base"

    # Logging settings
    log_callbacks: bool = True
    debug: bool = False

    def __post_init__(self):
        """Initialize default values."""
        if not self.gigachat_api_key:
            self.gigachat_api_key = os.getenv("GIGACHAT_API_KEY", "")

        if not self.ollama_url:
            self.ollama_url = os.getenv("OLLAMA_URL", "")
        if not self.ollama_model:
            self.ollama_model = os.getenv("OLLAMA_MODEL", "")

        if not self.chroma_path:
            self.chroma_path = str(Path(__file__).parent / "chroma_db")

    @property
    def detected_provider(self) -> LLMProvider:
        """Auto-detect LLM provider based on available configuration."""
        return _detect_provider(
            ollama_url=self.ollama_url,
            gigachat_api_key=self.gigachat_api_key,
        )

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create configuration from environment variables."""
        return cls(
            gigachat_api_key=os.getenv("GIGACHAT_API_KEY", ""),
            gigachat_model=os.getenv("GIGACHAT_MODEL", "GigaChat-2-Max"),
            ollama_url=os.getenv("OLLAMA_URL", ""),
            ollama_model=os.getenv("OLLAMA_MODEL", "TinyLlama:1.1b"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4000")),
            timeout=int(os.getenv("LLM_TIMEOUT", "90")),
            use_rag=_get_bool_env("AI_V2_USE_RAG", True),
            rag_top_k=int(os.getenv("AI_V2_RAG_TOP_K", "5")),
            chroma_path=os.getenv("AI_V2_CHROMA_PATH", ""),
            debug=os.getenv("DEBUG", "False").lower() == "true",
        )

    def validate(self) -> bool:
        """Validate configuration."""
        self.detected_provider
        return True
