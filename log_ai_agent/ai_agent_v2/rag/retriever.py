"""RAG retriever for MITRE ATT&CK knowledge base."""

import logging
from typing import Optional

from ..gigachat_client import GigaChatClient
from .chroma_manager import ChromaManager
from ..prompts.system import RAG_MITRE_QUERY_PROMPT

logger = logging.getLogger(__name__)


class MitreRAGRetriever:
    """
    RAG retriever for MITRE ATT&CK knowledge base.
    
    Uses LLM to enhance query formulation and ChromaDB for retrieval.
    """

    def __init__(
        self,
        chroma_manager: ChromaManager,
        gigachat_client: Optional[GigaChatClient] = None,
        top_k: int = 5,
    ):
        """
        Initialize RAG retriever.
        
        Args:
            chroma_manager: Initialized ChromaManager instance
            gigachat_client: Optional GigaChat client for query enhancement
            top_k: Number of results to retrieve
        """
        self.chroma_manager = chroma_manager
        self.gigachat_client = gigachat_client
        self.top_k = top_k

    async def retrieve(
        self,
        query: str,
        use_llm_enhancement: bool = True,
    ) -> list[dict]:
        """
        Retrieve relevant MITRE techniques.
        
        Args:
            query: Search query (e.g., primary analysis report)
            use_llm_enhancement: Whether to use LLM to enhance query
            
        Returns:
            List of relevant technique documents
        """
        # Optionally enhance query with LLM
        if use_llm_enhancement and self.gigachat_client:
            enhanced_query = await self._enhance_query(query)
        else:
            enhanced_query = query
        
        # Search ChromaDB
        results = self.chroma_manager.search(
            query=enhanced_query,
            k=self.top_k,
        )
        
        return results

    async def _enhance_query(self, analysis_text: str) -> str:
        """
        Use LLM to extract key search terms from analysis.
        
        Args:
            analysis_text: Primary analysis report
            
        Returns:
            Enhanced search query
        """
        try:
            # Extract key terms for MITRE search
            prompt = RAG_MITRE_QUERY_PROMPT.format(
                primary_analysis=analysis_text[:2000]  # Limit context
            )
            
            response = await self.gigachat_client.chat(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200,
            )
            
            logger.info(f"Enhanced query: {response[:200]}...")
            return response
            
        except Exception as e:
            logger.warning(f"Query enhancement failed: {e}, using original query")
            return analysis_text

    def format_results(self, results: list[dict]) -> str:
        """
        Format RAG results as context string for LLM.
        
        Args:
            results: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        return self.chroma_manager.format_context(results)

    async def retrieve_and_format(
        self,
        query: str,
        use_llm_enhancement: bool = True,
    ) -> str:
        """
        Retrieve and format results as context string.
        
        Args:
            query: Search query
            use_llm_enhancement: Whether to enhance query with LLM
            
        Returns:
            Formatted context string
        """
        results = await self.retrieve(query, use_llm_enhancement)
        return self.format_results(results)
