"""ChromaDB manager with automatic MITRE ATT&CK initialization."""

import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from ..embedding.manager import EmbeddingManager

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Manages ChromaDB vector store with automatic initialization.

    Features:
    - Auto-create ChromaDB if not exists
    - Auto-load MITRE ATT&CK techniques
    - Persistent storage
    - Search and retrieve techniques
    """

    DEFAULT_COLLECTION = "mitre_collection"

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = DEFAULT_COLLECTION,
        embedding_model: str | None = None,
    ):
        """Initialize ChromaDB manager.

        Args:
            persist_directory: Directory to store ChromaDB data
            collection_name: Name of the collection
            embedding_model: Optional embedding model name

        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embedding_model = embedding_model

        self._vectorstore: Chroma | None = None
        self._embedding_manager: EmbeddingManager | None = None

    def initialize(self) -> bool:
        """Initialize ChromaDB.

        Creates database if not exists.
        Loads MITRE ATT&CK if collection is empty.

        Returns:
            True if initialization successful

        """
        try:
            logger.info(f"Initializing ChromaDB at {self.persist_directory}")

            # Create persist directory
            self.persist_directory.mkdir(parents=True, exist_ok=True)

            # Load embeddings
            self._embedding_manager = EmbeddingManager(model_name=self.embedding_model)

            # Initialize or load ChromaDB
            self._vectorstore = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self._embedding_manager.embeddings,
                collection_name=self.collection_name,
            )

            # Check if collection is empty
            collection = self._vectorstore._client.get_collection(
                name=self.collection_name
            )
            count = collection.count()

            if count == 0:
                logger.info("ChromaDB is empty, will load MITRE ATT&CK on first use")
                return False  # Signal that MITRE needs to be loaded
            else:
                logger.info(f"✓ ChromaDB loaded with {count} documents")
                return True

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def load_mitre_techniques(self, techniques: list[dict]) -> int:
        """Load MITRE ATT&CK techniques into ChromaDB.

        Args:
            techniques: List of technique dicts with id, name, description, tactic

        Returns:
            Number of techniques loaded

        """
        if not self._vectorstore:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")

        logger.info(f"Loading {len(techniques)} MITRE techniques into ChromaDB")

        # Prepare documents
        documents = []
        for tech in techniques:
            # Create searchable text
            searchable_text = (
                f"{tech['technique_id']} {tech['technique_name']}\n"
                f"Тактика: {tech['tactic']}\n"
                f"Описание: {tech['description']}\n"
                f"Платформы: {', '.join(tech.get('platforms', [])) or 'N/A'}\n"
                f"Источники данных: {', '.join(tech.get('data_sources', [])) or 'N/A'}"
            )

            metadata = {
                "technique_id": tech["technique_id"],
                "technique_name": tech["technique_name"],
                "tactic": tech["tactic"],
            }

            doc = Document(page_content=searchable_text, metadata=metadata)
            documents.append(doc)

        # Add to vectorstore
        self._vectorstore.add_documents(documents)

        logger.info(f"✓ Loaded {len(documents)} MITRE techniques")
        return len(documents)

    def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: dict | None = None,
    ) -> list[dict]:
        """Search for relevant MITRE techniques.

        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            List of documents with metadata

        """
        if not self._vectorstore:
            raise RuntimeError("ChromaDB not initialized")

        try:
            retriever = self._vectorstore.as_retriever(
                search_kwargs={"k": k, "filter": filter_dict}
            )
            documents = retriever.invoke(query)

            results = []
            for doc in documents:
                results.append(
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                    }
                )

            logger.debug(f"RAG search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return []

    def format_context(self, results: list[dict]) -> str:
        """Format RAG results as context string for LLM.

        Args:
            results: List of search results

        Returns:
            Formatted context string

        """
        if not results:
            return "Нет релевантных техник MITRE ATT&CK в базе знаний."

        context_parts = []
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})

            technique_id = metadata.get("technique_id", "")
            technique_name = metadata.get("technique_name", "")
            tactic = metadata.get("tactic", "")

            context_parts.append(
                f"[{i}] {technique_id} {technique_name}\n"
                f"Тактика: {tactic}\n"
                f"Описание: {content}\n"
            )

        return "\n---\n".join(context_parts)

    @property
    def vectorstore(self) -> Chroma | None:
        """Get ChromaDB vectorstore."""
        return self._vectorstore

    @property
    def is_initialized(self) -> bool:
        """Check if ChromaDB is initialized."""
        return self._vectorstore is not None
