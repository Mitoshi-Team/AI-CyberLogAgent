"""Embedding manager — local model only, no network calls."""

import logging
import os
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

# Force transformers to never make network requests
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"


class EmbeddingManager:
    """Loads embeddings from a local model directory.

    Model must be pre-downloaded into a local folder.
    If not found, raises RuntimeError with instructions
    to run the download script.
    """

    DEFAULT_MODEL = "intfloat/multilingual-e5-base"

    def __init__(
        self,
        model_name: str | None = None,
        cache_dir: str | None = None,
    ):
        self.model_name = model_name or self.DEFAULT_MODEL

        # Resolve path to local model directory
        if cache_dir:
            self.model_dir = Path(cache_dir)
        else:
            # Project-internal local model
            self.model_dir = (
                Path(__file__).parent.parent
                / "embedding"
                / "models"
                / "multilingual-e5-base"
            )

        self._embeddings: HuggingFaceEmbeddings | None = None

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        """Get or create embeddings instance."""
        if self._embeddings is None:
            self._embeddings = self._load_embeddings()
        return self._embeddings

    def _load_embeddings(self) -> HuggingFaceEmbeddings:
        """Load embeddings from local directory.

        Raises:
            RuntimeError: If local model directory does not exist.

        """
        logger.info(f"Loading embeddings model from: {self.model_dir}")

        if not self.model_dir.exists():
            raise RuntimeError(
                f"Embedding model not found at: {self.model_dir}\n\n"
                "Run the download script first:\n"
                "  download_embedding_model.bat\n\n"
                f"or manually with:\n"
                "  uv run huggingface-cli download "
                "intfloat/multilingual-e5-base "
                "--local-dir log_ai_agent/ai_agent_v2/embedding/models/multilingual-e5-base"
            )

        logger.info("Loading local model (offline mode)...")

        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=str(self.model_dir),
                model_kwargs={"device": "cpu"},
                encode_kwargs={
                    "normalize_embeddings": True,
                    "batch_size": 32,
                },
            )
            logger.info("✓ Embeddings model loaded from local directory")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            raise RuntimeError(
                f"Failed to load embedding model from {self.model_dir}: {e}\n"
                "The model files may be corrupted. Re-run download_embedding_model.bat"
            ) from e

    def test_embedding(self, text: str = "Тест") -> list[float]:
        """Test embeddings by embedding a sample text."""
        embedding = self.embeddings.embed_query(text)
        logger.info(f"✓ Test embedding successful: {len(embedding)} dimensions")
        return embedding


def get_embeddings(
    model_name: str | None = None,
    cache_dir: str | None = None,
) -> HuggingFaceEmbeddings:
    """Convenience function to get embeddings instance."""
    manager = EmbeddingManager(model_name=model_name, cache_dir=cache_dir)
    return manager.embeddings
