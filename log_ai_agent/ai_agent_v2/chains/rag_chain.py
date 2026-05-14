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

QUERY_ENHANCEMENT_PROMPT = """Ты — эксперт по базе знаний MITRE ATT&CK.
Сгенерируй оптимальный поисковый запрос на РУССКОМ для поиска релевантных техник.

ОПИСАНИЕ СОБЫТИЯ:
{description}

ИНСТРУКЦИИ:
1. Определи основной тип техники атаки (брутфорс, SQL-инъекция и т.д.)
2. Держи запрос кратким (3-5 ключевых терминов)
3. Фокусируйся на цели и назначении атаки, а не на кодировании или обфускации
4. Для PowerShell-команд используй термины типа 'выполнение команды PowerShell'

ПОИСКОВЫЙ ЗАПРОС (на русском, 3-5 терминов):"""

RERANK_PROMPT = """Ты — эксперт по базе знаний MITRE ATT&CK, специализирующийся на точном сопоставлении техник.

ЗАДАЧА: Выбери ЕДИНУЮ лучшую подходящую технику MITRE из списка ниже.

ОПИСАНИЕ СОБЫТИЯ:
{description}

НАЙДЕННЫЕ ТЕХНИКИ (топ-{k}):
{techniques}

КРИТИЧЕСКИЕ ИНСТРУКЦИИ:
1. Список отсортирован по релевантности (наиболее релевантная первой).
2. Если ПЕРВАЯ техника чётко подходит событию — выбери её.
3. Выбирай технику с более низким рангом ТОЛЬКО если первая явно неверна.
4. НЕ заменяй хорошее совпадение общей или нерелевантной техникой.
5. Если топ-результат соответствует типу описанной атаки — это твой ответ.
6. Отвечай ТОЛЬКО ID техники (например T1110) или NONE если ничего не подходит."""


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
                "Ты — эксперт по поиску в базе знаний MITRE ATT&CK. "
                "Извлекай ключевые слова для поиска техник."
            ),
            HumanMessagePromptTemplate.from_template(QUERY_ENHANCEMENT_PROMPT),
        ]
    )

    chain: RunnableSequence = prompt | llm | StrOutputParser()
    return chain


def format_query_for_e5(query: str) -> str:
    """Format query for e5 embeddings with 'query:' prefix.

    Args:
        query: Original search query

    Returns:
        Formatted query with e5 prefix

    """
    return f"query: {query}"


def search_mitre_techniques(
    chroma_mgr: ChromaDBManager,
    query: str,
    k: int = 5,
    score_threshold: float = 0.7,
    use_hybrid: bool = True,
) -> list[dict]:
    """Search MITRE ATT&CK techniques using hybrid vector + BM25 search.

    Args:
        chroma_mgr: ChromaDB manager
        query: Search query (will be embedded)
        k: Number of results
        score_threshold: Minimum similarity threshold (0.0-1.0). Only results with
            similarity >= threshold will be returned. Default: 0.7
        use_hybrid: If True, combine vector + BM25 (default: True)

    Returns:
        List of technique documents with metadata

    """
    if not chroma_mgr.is_initialized:
        logger.warning("ChromaDB not initialized, returning empty results")
        return []

    if use_hybrid and hasattr(chroma_mgr, 'hybrid_search'):
        results = chroma_mgr.hybrid_search(
            query=query,
            k=k,
            vector_weight=0.6,
            bm25_weight=0.4,
            score_threshold=score_threshold,
        )
        logger.info(f"Hybrid search found {len(results)} techniques (threshold: {score_threshold})")
    else:
        results = chroma_mgr.search(query=query, k=k, score_threshold=score_threshold)
        logger.info(f"Vector search found {len(results)} techniques (threshold: {score_threshold})")

    return results


async def rag_search_single_event(
    llm: BaseLanguageModel,
    chroma_mgr: ChromaDBManager,
    description: str,
    keywords: list[str] | None = None,
    k: int = 3,
    score_threshold: float = 0.7,
    use_reranking: bool = True,
) -> dict[str, Any]:
    """Search for MITRE technique for a single suspicious event.

    This function:
    1. Enhances the query using LLM
    2. Optionally adds keywords to the search query
    3. Searches ChromaDB
    4. (Optional) Re-ranks results using LLM
    5. Returns the best match or None

    Args:
        llm: Language model for query enhancement
        chroma_mgr: ChromaDB manager for vector search
        description: English description of the suspicious event
        keywords: Optional list of English keywords to include in search
        k: Number of techniques to retrieve
        score_threshold: Minimum similarity threshold (0.0-1.0). Default: 0.7
        use_reranking: Whether to use LLM re-ranking. Default: True.

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

    # Add keywords to search query if provided
    if keywords:
        keywords_str = ", ".join(keywords[:10])
        search_query = f"{search_query}. Keywords: {keywords_str}"
        logger.debug(f"Added keywords to query: {keywords_str[:100]}")

    try:
        enhancement_chain = create_query_enhancement_chain(llm)
        enhancement_result = await enhancement_chain.ainvoke(
            {"description": search_query[:1000]}
        )
        search_query = enhancement_result.strip()
        logger.debug(f"Enhanced query: '{search_query}'")
    except Exception as e:
        logger.warning(f"Query enhancement failed: {e}, using original")
        search_query = description[:200]

    # Format for e5 embeddings with query: prefix
    search_query = format_query_for_e5(search_query)
    logger.debug(f"Formatted query for e5: '{search_query[:100]}...'")

    results = search_mitre_techniques(chroma_mgr, search_query, k=k, score_threshold=score_threshold)

    if not results:
        return {
            "has_match": False,
            "technique_id": None,
            "name": None,
            "details": None,
            "search_query": search_query,
            "confidence": 0.0,
        }

    # Re-ranking step
    if use_reranking and len(results) > 1:
        try:
            reranked_id = await rerank_techniques(
                llm=llm,
                description=description,
                techniques=results,
                k=min(k, 5),
            )

            if reranked_id:
                # Find the reranked technique in results
                for r in results:
                    if r.get("metadata", {}).get("technique_id") == reranked_id:
                        best_match = r
                        break
                else:
                    best_match = results[0]
            else:
                best_match = results[0]
        except Exception as e:
            logger.warning(f"Re-ranking failed: {e}, using top result")
            best_match = results[0]
    else:
        best_match = results[0]

    metadata = best_match.get("metadata", {})
    distance = best_match.get("score", 1.0)

    return {
        "has_match": True,
        "technique_id": metadata.get("technique_id", ""),
        "name": metadata.get("technique_name", ""),
        "details": best_match,
        "search_query": search_query,
        "confidence": distance,
    }


async def rerank_techniques(
    llm: BaseLanguageModel,
    description: str,
    techniques: list[dict],
    k: int = 5,
) -> str | None:
    """Re-rank retrieved techniques using LLM and return best match.

    Args:
        llm: Language model for re-ranking
        description: Description of the suspicious event
        techniques: List of retrieved techniques from vector search
        k: Number of top techniques to consider

    Returns:
        Best matching technique_id or None
    """
    if not techniques:
        return None

    # Prepare techniques list for LLM
    tech_list = []
    for i, tech in enumerate(techniques[:k], 1):
        metadata = tech.get("metadata", {})
        tech_id = metadata.get("technique_id", "Unknown")
        tech_name = metadata.get("technique_name", "")
        tech_list.append(f"{i}. {tech_id} ({tech_name})")

    techniques_text = "\n".join(tech_list)

    prompt = RERANK_PROMPT.format(
        description=description[:500],
        k=k,
        techniques=techniques_text,
    )

    try:
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        rerank_chain = (
            ChatPromptTemplate.from_messages(
                [
                    HumanMessagePromptTemplate.from_template(RERANK_PROMPT),
                ]
            )
            | llm
            | StrOutputParser()
        )

        result = await rerank_chain.ainvoke(
            {
                "description": description[:500],
                "k": k,
                "techniques": techniques_text,
            }
        )

        result = result.strip().upper()

        if result == "NONE" or not result.startswith("T"):
            return None

        # Validate that result is in our techniques list
        valid_ids = [t.get("metadata", {}).get("technique_id", "") for t in techniques]
        if result in valid_ids:
            return result

        return None

    except Exception as e:
        logger.warning(f"Re-ranking failed: {e}")
        return None


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
    results = search_mitre_techniques(chroma_mgr, search_query, k=k, score_threshold=0.7)

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
