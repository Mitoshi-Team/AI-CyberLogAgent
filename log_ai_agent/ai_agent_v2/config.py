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
    AITUNNEL = "aitunnel"


def _detect_provider(
    ollama_url: str | None = None,
    aitunnel_api_key: str | None = None,
) -> LLMProvider:
    """Detect which LLM provider to use based on available configuration.

    Priority:
    1. Ollama — if ollama_url is provided (on-premise)
    2. AITUNNEL — if aitunnel_api_key is provided (cloud API)

    """
    if ollama_url and ollama_url.strip():
        return LLMProvider.OLLAMA
    if aitunnel_api_key and aitunnel_api_key.strip():
        return LLMProvider.AITUNNEL
    raise ValueError(
        "No LLM provider configured. "
        "Set OLLAMA_URL (for local Ollama) or AITUNNEL_API_KEY (for cloud API)."
    )


@dataclass
class AgentConfig:
    """Configuration for AI Agent v2."""

    # Ollama settings
    ollama_url: str = ""
    ollama_model: str = ""

    # AITUNNEL settings
    aitunnel_api_key: str = ""
    aitunnel_base_url: str = "https://api.aitunnel.ru/v1"
    aitunnel_model: str = "deepseek-v4-flash"

    # Common LLM settings
    temperature: float = 0.1
    max_tokens: int = 16384
    timeout: int = 90

    # RAG settings
    use_rag: bool = True
    rag_top_k: int = 5
    rag_score_threshold: float = 0.5

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
        if not self.ollama_url:
            self.ollama_url = os.getenv("OLLAMA_URL", "")
        if not self.ollama_model:
            self.ollama_model = os.getenv("OLLAMA_MODEL", "")

        if not self.aitunnel_api_key:
            self.aitunnel_api_key = os.getenv("AITUNNEL_API_KEY", "")
        if not self.aitunnel_base_url:
            self.aitunnel_base_url = os.getenv("AITUNNEL_BASE_URL", "https://api.aitunnel.ru/v1")
        if not self.aitunnel_model:
            self.aitunnel_model = os.getenv("AITUNNEL_MODEL", "deepseek-v4-flash")

        if not self.chroma_path:
            self.chroma_path = str(Path(__file__).parent / "chroma_db")

    @property
    def detected_provider(self) -> LLMProvider:
        """Auto-detect LLM provider based on available configuration."""
        return _detect_provider(
            ollama_url=self.ollama_url,
            aitunnel_api_key=self.aitunnel_api_key,
        )

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create configuration from environment variables."""
        return cls(
            ollama_url=os.getenv("OLLAMA_URL", ""),
            ollama_model=os.getenv("OLLAMA_MODEL", "TinyLlama:1.1b"),
            aitunnel_api_key=os.getenv("AITUNNEL_API_KEY", ""),
            aitunnel_base_url=os.getenv("AITUNNEL_BASE_URL", "https://api.aitunnel.ru/v1"),
            aitunnel_model=os.getenv("AITUNNEL_MODEL", "deepseek-v4-flash"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "8192")),
            timeout=int(os.getenv("LLM_TIMEOUT", "90")),
            use_rag=_get_bool_env("AI_V2_USE_RAG", True),
            rag_top_k=int(os.getenv("AI_V2_RAG_TOP_K", "5")),
            rag_score_threshold=float(os.getenv("AI_V2_RAG_THRESHOLD", "0.5")),
            chroma_path=os.getenv("AI_V2_CHROMA_PATH", ""),
            debug=os.getenv("DEBUG", "False").lower() == "true",
        )

    def validate(self) -> bool:
        """Validate configuration."""
        self.detected_provider
        return True
