"""Configuration for AI Agent v2."""

import os
from dataclasses import dataclass
from pathlib import Path


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass
class AgentConfig:
    """Configuration for AI Agent v2."""

    # GigaChat settings
    gigachat_api_key: str = ""
    gigachat_model: str = "GigaChat-2-Max"
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
    embedding_model: str = "answerdotai/ModernBERT-base"  # "intfloat/multilingual-e5-base"  # Multilingual, open access

    # Logging settings
    log_callbacks: bool = True
    debug: bool = False

    def __post_init__(self):
        """Initialize default values."""
        # Load API key from environment if not provided
        if not self.gigachat_api_key:
            self.gigachat_api_key = os.getenv("GIGACHAT_API_KEY", "")

        # Set default ChromaDB path if not provided
        if not self.chroma_path:
            self.chroma_path = str(Path(__file__).parent / "chroma_db")

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create configuration from environment variables.

        Returns:
            AgentConfig instance

        """
        return cls(
            gigachat_api_key=os.getenv("GIGACHAT_API_KEY", ""),
            gigachat_model=os.getenv("GIGACHAT_MODEL", "GigaChat-2-Max"),
            temperature=float(os.getenv("GIGACHAT_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("GIGACHAT_MAX_TOKENS", "4000")),
            timeout=int(os.getenv("GIGACHAT_TIMEOUT", "90")),
            use_rag=_get_bool_env("AI_V2_USE_RAG", True),
            rag_top_k=int(os.getenv("AI_V2_RAG_TOP_K", "5")),
            chroma_path=os.getenv("AI_V2_CHROMA_PATH", ""),
            debug=os.getenv("DEBUG", "False").lower() == "true",
        )

    def validate(self) -> bool:
        """Validate configuration.

        Returns:
            True if configuration is valid

        """
        if not self.gigachat_api_key:
            raise ValueError("GIGACHAT_API_KEY is required")
        return True
