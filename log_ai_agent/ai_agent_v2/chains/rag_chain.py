"""RAG chain for MITRE ATT&CK retrieval."""

import logging
from typing import Any

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnableSequence

from ..knowledge_base.manager import ChromaDBManager

logger = logging.getLogger(__name__)

QUERY_ENHANCEMENT_PROMPT = """Ты - эксперт по поиску в базе знаний MITRE ATT&CK.
Извлеки ключевые слова для поиска техник.

ОПИСАНИЕ АКТИВНОСТИ:
{description}

Поисковый запрос (2-5 ключевых слов):"""


def create_query_enhancement_chain(llm: BaseLanguageModel) -> RunnableSequence:
    """Create chain for enhancing RAG query.

    Args:
        llm: Language model

    Returns:
        RunnableSequence for query enhancement

    """
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(
                "Ты - эксперт по поиску в базе знаний MITRE ATT&CK. "
                "Извлекай ключевые слова для поиска техник."
            ),
            HumanMessagePromptTemplate.from_template(QUERY_ENHANCEMENT_PROMPT),
        ]
    )

    chain: RunnableSequence = prompt | llm | StrOutputParser()
    return chain


def search_mitre_techniques(
    chroma_mgr: ChromaDBManager,
    query: str,
    k: int = 5,
) -> list[dict]:
    """Search MITRE ATT&CK techniques using vector similarity.

    Args:
        chroma_mgr: ChromaDB manager
        query: Search query (will be embedded)
        k: Number of results

    Returns:
        List of technique documents with metadata

    """
    if not chroma_mgr.is_initialized:
        logger.warning("ChromaDB not initialized, returning empty results")
        return []

    results = chroma_mgr.search(query=query, k=k)
    logger.info(f"RAG search found {len(results)} techniques")
    return results


async def rag_search_single_event(
    llm: BaseLanguageModel,
    chroma_mgr: ChromaDBManager,
    description: str,
    k: int = 3,
) -> dict[str, Any]:
    """Search for MITRE technique for a single suspicious event.

    This function:
    1. Enhances the query using LLM (without timestamp)
    2. Searches ChromaDB
    3. Returns the best match or None

    Args:
        llm: Language model for query enhancement
        chroma_mgr: ChromaDB manager for vector search
        description: Description of the suspicious event (WITHOUT timestamp)
        k: Number of techniques to retrieve

    Returns:
        Dictionary with:
        - has_match: bool
        - technique_id: str or None
        - name: str or None
        - details: dict or None (full technique info)
        - search_query: str (the query used)
        - confidence: float (similarity score)

    """
    logger.info(f"RAG search for event: {description[:100]}...")

    search_query = description[:500]

    try:
        enhancement_chain = create_query_enhancement_chain(llm)
        enhancement_result = await enhancement_chain.ainvoke(
            {"description": description[:1000]}
        )
        search_query = enhancement_result.strip()
        logger.debug(f"Enhanced query: '{search_query}'")
    except Exception as e:
        logger.warning(f"Query enhancement failed: {e}, using original")
        search_query = description[:200]

    results = search_mitre_techniques(chroma_mgr, search_query, k=k)

    if results:
        best_match = results[0]
        metadata = best_match.get("metadata", {})
        confidence = best_match.get("distance", 0)

        return {
            "has_match": True,
            "technique_id": metadata.get("technique_id", ""),
            "name": metadata.get("technique_name", ""),
            "details": best_match,
            "search_query": search_query,
            "confidence": confidence,
        }

    return {
        "has_match": False,
        "technique_id": None,
        "name": None,
        "details": None,
        "search_query": search_query,
        "confidence": 0.0,
    }


async def retrieve_mitre_context(
    llm: BaseLanguageModel,
    chroma_mgr: ChromaDBManager,
    primary_analysis: str,
    k: int = 5,
    use_query_enhancement: bool = True,
) -> dict[str, Any]:
    """Retrieve MITRE context using RAG (legacy function for compatibility).

    Flow:
    1. Extract keywords from primary_analysis using LLM
    2. Search ChromaDB with enhanced query
    3. Format context for Agent 2

    Args:
        llm: Language model
        chroma_mgr: ChromaDB manager
        primary_analysis: Primary analysis from Agent 1
        k: Number of techniques to retrieve
        use_query_enhancement: Whether to enhance query with LLM

    Returns:
        Dictionary with techniques and formatted context

    """
    logger.info("Retrieving MITRE ATT&CK context")

    search_query = primary_analysis[:500]

    if use_query_enhancement:
        try:
            logger.debug("Enhancing search query with LLM...")
            enhancement_chain = create_query_enhancement_chain(llm)
            enhancement_result = await enhancement_chain.ainvoke(
                {"description": primary_analysis[:1000]}
            )
            search_query = enhancement_result.strip()
            logger.info(f"Enhanced query: '{search_query}'")
        except Exception as e:
            logger.warning(f"Query enhancement failed: {e}, using original query")

    logger.info(f"Searching ChromaDB for: '{search_query[:100]}...'")
    results = search_mitre_techniques(chroma_mgr, search_query, k=k)

    if results:
        technique_ids = [
            r.get("metadata", {}).get("technique_id", "")
            for r in results
            if r.get("metadata", {}).get("technique_id")
        ]
        logger.info(f"Found techniques: {', '.join(technique_ids)}")
    else:
        logger.warning("No MITRE techniques found")
        technique_ids = []

    context_text = (
        chroma_mgr.format_context(results)
        if results
        else "No relevant MITRE ATT&CK techniques found."
    )

    return {
        "mitre_context": context_text,
        "mitre_techniques": results,
        "technique_ids": technique_ids,
        "search_query": search_query,
    }
