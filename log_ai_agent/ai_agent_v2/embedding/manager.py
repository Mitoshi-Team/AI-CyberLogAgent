"""Embedding manager with automatic HuggingFace model download."""

import logging
import os
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages HuggingFace embeddings with automatic download and caching.

    Features:
    - Auto-download model from HuggingFace if not cached
    - Cache model in ~/.cache/huggingface (or custom dir)
    - Support for local model files
    - Reuses cached model on subsequent runs
    """

    # Multilingual model with open access (works in Russia)
    DEFAULT_MODEL = "intfloat/multilingual-e5-base"

    def __init__(
        self,
        model_name: str | None = None,
        cache_dir: str | None = None,
    ):
        """Initialize embedding manager.

        Args:
            model_name: HuggingFace model name (default: multilingual-e5-base)
            cache_dir: Directory to cache model (default: ~/.cache/huggingface)

        """
        self.model_name = model_name or self.DEFAULT_MODEL

        # Use HuggingFace default cache dir (~/.cache/huggingface)
        # or custom dir if specified
        self.cache_dir = cache_dir or os.getenv(
            "HF_HOME", str(Path.home() / ".cache" / "huggingface")
        )

        self._embeddings: HuggingFaceEmbeddings | None = None

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        """Get or create embeddings instance."""
        if self._embeddings is None:
            self._embeddings = self._load_embeddings()
        return self._embeddings

    def _load_embeddings(self) -> HuggingFaceEmbeddings:
        """Load embeddings model.

        Downloads from HuggingFace if not cached.
        Subsequent loads use cached model.

        Returns:
            HuggingFaceEmbeddings instance

        """
        logger.info(f"Loading embeddings model: {self.model_name}")
        logger.info(f"Cache directory: {self.cache_dir}")

        try:
            # HuggingFace automatically caches models
            # First download, subsequent loads use cache
            embeddings = HuggingFaceEmbeddings(
                model_name=self.model_name,
                cache_folder=self.cache_dir,
                model_kwargs={
                    "device": "cpu",  # Can be changed to "cuda" if available
                },
                encode_kwargs={
                    "normalize_embeddings": True,
                    "batch_size": 32,
                },
            )

            logger.info(f"✓ Embeddings model loaded: {self.model_name}")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            raise

    def test_embedding(self, text: str = "Тест") -> list[float]:
        """Test embeddings by embedding a sample text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        """
        try:
            embedding = self.embeddings.embed_query(text)
            logger.info(f"✓ Test embedding successful: {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Test embedding failed: {e}")
            raise


def get_embeddings(
    model_name: str | None = None,
    cache_dir: str | None = None,
) -> HuggingFaceEmbeddings:
    """Convenience function to get embeddings instance.

    Args:
        model_name: Optional model name override
        cache_dir: Optional cache directory override

    Returns:
        HuggingFaceEmbeddings instance

    """
    manager = EmbeddingManager(model_name=model_name, cache_dir=cache_dir)
    return manager.embeddings
