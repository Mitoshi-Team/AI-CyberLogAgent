"""ChromaDB manager for MITRE ATT&CK knowledge base."""

import logging
import os
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class ChromaManager:
    """
    Manages ChromaDB vector store for MITRE ATT&CK knowledge base.
    
    Handles:
    - Loading/creating embeddings
    - Connecting to ChromaDB persistence
    - Searching for relevant techniques
    """

    def __init__(
        self,
        chroma_path: Optional[str] = None,
        embedding_model: str = "sentence-transformers/rubert-base-cased",
        collection_name: str = "mitre_collection",
    ):
        """
        Initialize ChromaDB manager.
        
        Args:
            chroma_path: Path to ChromaDB persistence directory
            embedding_model: HuggingFace embedding model name
            collection_name: Name of ChromaDB collection
        """
        self.chroma_path = chroma_path or os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "chroma_db"
        )
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        self.embeddings: Optional[HuggingFaceEmbeddings] = None
        self.vectorstore: Optional[Chroma] = None
        self.is_available = False

    def initialize(self, use_local_model: bool = False, local_model_path: Optional[str] = None) -> bool:
        """
        Initialize embeddings and vectorstore.
        
        Args:
            use_local_model: Whether to use local model files
            local_model_path: Path to local model directory
            
        Returns:
            True if initialization successful
        """
        try:
            # Initialize embeddings
            if use_local_model and local_model_path:
                logger.info(f"Loading local embeddings from {local_model_path}")
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=local_model_path,
                    model_kwargs={"local_files_only": True},
                )
            else:
                logger.info(f"Loading embeddings from HuggingFace: {self.embedding_model}")
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.embedding_model,
                )
            
            # Initialize ChromaDB
            logger.info(f"Connecting to ChromaDB at {self.chroma_path}")
            self.vectorstore = Chroma(
                persist_directory=self.chroma_path,
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
            )
            
            self.is_available = True
            logger.info("ChromaDB initialized successfully")
            return True
            
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}")
            self.is_available = False
            return False

    def search(
        self, 
        query: str, 
        k: int = 5,
        filter_dict: Optional[dict] = None,
    ) -> list[dict]:
        """
        Search for relevant MITRE techniques.
        
        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filter
            
        Returns:
            List of documents with metadata
        """
        if not self.is_available or not self.vectorstore:
            logger.warning("ChromaDB not available, returning empty results")
            return []
        
        try:
            retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": k, "filter": filter_dict}
            )
            documents = retriever.invoke(query)
            
            results = []
            for doc in documents:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                })
            
            logger.info(f"RAG search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return []

    def format_context(self, results: list[dict]) -> str:
        """
        Format RAG results as context string for LLM.
        
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

    def add_documents(
        self, 
        documents: list[tuple[str, dict]],
        batch_size: int = 100,
    ):
        """
        Add documents to the knowledge base.
        
        Args:
            documents: List of (text, metadata) tuples
            batch_size: Number of documents to add in each batch
        """
        if not self.is_available or not self.vectorstore:
            raise RuntimeError("ChromaDB not initialized")
        
        from langchain_core.documents import Document
        
        langchain_docs = [
            Document(page_content=text, metadata=metadata)
            for text, metadata in documents
        ]
        
        logger.info(f"Adding {len(langchain_docs)} documents to ChromaDB")
        
        # Add in batches
        for i in range(0, len(langchain_docs), batch_size):
            batch = langchain_docs[i:i + batch_size]
            self.vectorstore.add_documents(batch)
            logger.info(f"Added batch {i // batch_size + 1}")

    def clear_collection(self):
        """Clear all documents from the collection."""
        if not self.is_available or not self.vectorstore:
            return
        
        # Get all IDs and delete
        try:
            collection = self.vectorstore._client.get_collection(
                name=self.collection_name
            )
            all_ids = collection.get()["ids"]
            if all_ids:
                self.vectorstore.delete(ids=all_ids)
                logger.info("Cleared all documents from collection")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
