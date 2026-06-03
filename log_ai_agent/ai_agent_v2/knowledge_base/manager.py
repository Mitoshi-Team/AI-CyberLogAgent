"""ChromaDB manager with automatic MITRE ATT&CK initialization."""

import logging
import re
from collections import defaultdict
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from ..embedding.manager import EmbeddingManager

logger = logging.getLogger(__name__)


class BM25Searcher:
    """Simple BM25 implementation for keyword matching."""

    def __init__(self):
        self.documents: list[dict] = []
        self.doc_freq: dict[str, int] = defaultdict(int)
        self.avgdl: float = 0
        self.k1 = 1.5
        self.b = 0.75

    def add_documents(self, docs: list[dict]):
        """Add documents for BM25 search.

        Args:
            docs: List of dicts with 'id', 'text', 'technique_id', 'technique_name'
        """
        self.documents = docs
        doc_lens = []

        for doc in docs:
            tokens = self._tokenize(doc.get("text", ""))
            doc_lens.append(len(tokens))
            for term in set(tokens):
                self.doc_freq[term] += 1

        self.avgdl = sum(doc_lens) / len(doc_lens) if doc_lens else 0
        logger.info(f"BM25 index built: {len(docs)} documents, {len(self.doc_freq)} terms")

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text for BM25."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens

    def _calc_idf(self, term: str) -> float:
        """Calculate IDF for a term."""
        df = self.doc_freq.get(term, 0)
        if df == 0:
            return 0
        return max(0, (len(self.documents) - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        """Search BM25 index.

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of (doc_index, score) tuples
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = []
        for i, doc in enumerate(self.documents):
            doc_tokens = self._tokenize(doc.get("text", ""))
            if not doc_tokens:
                continue

            score = 0
            doc_len = len(doc_tokens)

            for qt in query_tokens:
                tf = doc_tokens.count(qt)
                if tf == 0:
                    continue

                idf = self._calc_idf(qt)
                tf_norm = (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                )
                score += idf * tf_norm

            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


class ChromaDBManager:
    """Manages ChromaDB vector store with automatic initialization.

    Features:
    - Auto-create ChromaDB if not exists
    - Auto-load MITRE ATT&CK techniques
    - Persistent storage
    - Search and retrieve techniques
    - BM25 hybrid search for better keyword matching
    """

    DEFAULT_COLLECTION = "mitre_collection"

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = DEFAULT_COLLECTION,
        embedding_model: str | None = None,
        distance_metric: str = "cosine",
    ):
        """Initialize ChromaDB manager.

        Args:
            persist_directory: Directory to store ChromaDB data
            collection_name: Name of the collection
            embedding_model: Optional embedding model name
            distance_metric: Distance metric for similarity search.
                Options: "cosine" (recommended for embeddings), "l2", "ip".
                Default: "cosine"

        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.distance_metric = distance_metric

        self._vectorstore: Chroma | None = None
        self._embedding_manager: EmbeddingManager | None = None
        self._bm25: BM25Searcher | None = None
        self._technique_docs: list[dict] = []

    def initialize(self) -> bool:
        """Initialize ChromaDB.

        Creates database if not exists with specified distance metric.
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

            # Initialize or load ChromaDB with specified distance metric
            self._vectorstore = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self._embedding_manager.embeddings,
                collection_name=self.collection_name,
                collection_metadata={"hnsw:space": self.distance_metric},
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
                logger.info(f"ChromaDB loaded with {count} documents (distance: {self.distance_metric})")
                return True

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def load_mitre_techniques(
        self,
        techniques: list[dict],
        use_summaries: bool = False,
    ) -> int:
        """Load MITRE ATT&CK techniques into ChromaDB.

        Args:
            techniques: List of technique dicts with id, name, description, tactic
            use_summaries: If True, expects 'summary' field and uses it instead of full description

        Returns:
            Number of techniques loaded

        """
        if not self._vectorstore:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")

        logger.info(f"Loading {len(techniques)} MITRE techniques into ChromaDB")
        if use_summaries:
            logger.info("Using summarized descriptions for better search quality")

        # Prepare documents
        documents = []
        technique_docs = []

        for tech in techniques:
            description_text = tech.get("description", "")

            keywords_ru = tech.get("keywords_ru", [])
            keywords_str = " ".join(keywords_ru) if keywords_ru else ""

            keywords_en = tech.get("keywords_en", [])
            keywords_en_str = " ".join(keywords_en) if keywords_en else ""

            tech_name_en = tech.get("technique_name", "")

            # Create searchable text with both Russian and English keywords
            all_keywords = " ".join(filter(None, [keywords_str, keywords_en_str]))

            if all_keywords:
                searchable_text = f"passage: {description_text} {tech_name_en} {all_keywords}"
            else:
                searchable_text = f"passage: {description_text} {tech_name_en}"

            metadata = {
                "technique_id": tech["technique_id"],
                "technique_name": tech["technique_name"],
                "tactic": tech["tactic"],
                "keywords_ru": keywords_str,
                "keywords_en": keywords_en_str,
            }

            doc = Document(page_content=searchable_text, metadata=metadata)
            documents.append(doc)

            # Store for BM25
            technique_docs.append({
                "id": len(documents) - 1,
                "technique_id": tech["technique_id"],
                "technique_name": tech["technique_name"],
                "tactic": tech["tactic"],
                "text": f"{description_text} {tech_name_en} {all_keywords}".lower(),
            })

        # Add to vectorstore
        self._vectorstore.add_documents(documents)

        # Build BM25 index
        self._bm25 = BM25Searcher()
        self._bm25.add_documents(technique_docs)
        self._technique_docs = technique_docs

        logger.info(f"✓ Loaded {len(documents)} MITRE techniques")
        return len(documents)

    def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: dict | None = None,
        score_threshold: float = 0.7,
    ) -> list[dict]:
        """Search for relevant MITRE techniques.

        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filter
            score_threshold: Minimum similarity threshold (0.0-1.0). Only results with
                similarity >= threshold will be returned. Default: 0.7

        Returns:
            List of documents with metadata

        """
        if not self._vectorstore:
            raise RuntimeError("ChromaDB not initialized")

        try:
            # Use similarity_search_with_score to get distance scores
            # For ChromaDB cosine: "distance" = 1 - cosine_similarity
            # Convert to actual similarity: similarity = 1 - distance
            docs_with_scores = self._vectorstore.similarity_search_with_score(
                query,
                k=k,
                filter=filter_dict,
            )

            results = []
            filtered_count = 0
            for doc, score in docs_with_scores:
                # Convert ChromaDB "distance" to cosine similarity
                actual_similarity = 1.0 - score
                if actual_similarity >= score_threshold:
                    results.append(
                        {
                            "content": doc.page_content,
                            "metadata": doc.metadata,
                            "score": actual_similarity,
                        }
                    )
                else:
                    filtered_count += 1

            if filtered_count > 0:
                logger.info(
                    f"RAG: filtered {filtered_count} results below "
                    f"threshold {score_threshold}"
                )

            logger.debug(f"RAG search returned {len(results)} results (threshold: {score_threshold})")
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
            return "No relevant MITRE ATT&CK techniques found."

        context_parts = []
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})

            technique_id = metadata.get("technique_id", "")
            technique_name = metadata.get("technique_name", "")
            tactic = metadata.get("tactic", "")

            context_parts.append(
                f"[{i}] {technique_id} {technique_name}\n"
                f"Tactic: {tactic}\n"
                f"Description: {content}\n"
            )

        return "\n---\n".join(context_parts)

    def hybrid_search(
        self,
        query: str,
        k: int = 10,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
        score_threshold: float = 0.3,
    ) -> list[dict]:
        """Hybrid search combining vector similarity and BM25 keyword matching.

        Args:
            query: Search query text
            k: Number of results to return
            vector_weight: Weight for vector similarity (0-1)
            bm25_weight: Weight for BM25 score (0-1)
            score_threshold: Minimum combined score threshold

        Returns:
            List of documents with combined scores, sorted by relevance
        """
        if not self._vectorstore:
            raise RuntimeError("ChromaDB not initialized")

        if not self._bm25 or not self._technique_docs:
            logger.warning("BM25 not initialized, falling back to vector search")
            return self.search(query, k=k, score_threshold=score_threshold)

        try:
            vec_results = self._vectorstore.similarity_search_with_score(query, k=k * 2)

            bm25_results = self._bm25.search(query, k=k * 2)

            if not vec_results and not bm25_results:
                return []

            vec_max_score = max((1.0 - score) for _, score in vec_results) if vec_results else 1.0
            bm25_max_score = max(score for _, score in bm25_results) if bm25_results else 1.0

            combined_scores: dict[str, float] = {}
            technique_map: dict[str, int] = {}

            for doc, score in vec_results:
                tid = doc.metadata.get("technique_id", "")
                if not tid:
                    continue
                if tid not in technique_map:
                    technique_map[tid] = len(technique_map)
                norm_sim = (1.0 - score) / vec_max_score if vec_max_score > 0 else 0
                combined_scores[tid] = combined_scores.get(tid, 0) + norm_sim * vector_weight

            for doc_idx, bm25_score in bm25_results:
                if doc_idx < len(self._technique_docs):
                    tid = self._technique_docs[doc_idx]["technique_id"]
                    norm_bm25 = bm25_score / bm25_max_score if bm25_max_score > 0 else 0
                    combined_scores[tid] = combined_scores.get(tid, 0) + norm_bm25 * bm25_weight

            results = []
            for tid, combined_score in sorted(
                combined_scores.items(), key=lambda x: x[1], reverse=True
            )[:k]:
                if combined_score < score_threshold:
                    continue
                for doc in self._technique_docs:
                    if doc["technique_id"] == tid:
                        results.append({
                            "content": f"passage: {doc['text']}",
                            "metadata": {
                                "technique_id": doc["technique_id"],
                                "technique_name": doc["technique_name"],
                                "tactic": doc["tactic"],
                            },
                            "score": combined_score,
                        })
                        break

            return results

        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            return self.search(query, k=k, score_threshold=score_threshold)

    @property
    def vectorstore(self) -> Chroma | None:
        """Get ChromaDB vectorstore."""
        return self._vectorstore

    @property
    def is_initialized(self) -> bool:
        """Check if ChromaDB is initialized."""
        return self._vectorstore is not None
