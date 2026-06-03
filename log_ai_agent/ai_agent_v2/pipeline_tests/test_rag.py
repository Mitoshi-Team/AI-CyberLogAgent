#!/usr/bin/env python3
"""Tests for RAG (Agent 2) functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.language_models import BaseLanguageModel

from log_ai_agent.ai_agent_v2.chains.rag_chain import (
    search_mitre_techniques,
    rag_search_single_event,
)
from log_ai_agent.ai_agent_v2.knowledge_base.manager import ChromaDBManager


def create_mock_chroma_mgr(results: list[dict]) -> ChromaDBManager:
    """Create a mock ChromaDB manager."""
    mock = MagicMock(spec=ChromaDBManager)
    mock.is_initialized = True
    # rag_chain now uses hybrid_search when use_hybrid=True
    mock.hybrid_search = MagicMock(return_value=results)
    mock.search = MagicMock(return_value=results)
    return mock


def test_rag_search_basic():
    """Test basic RAG search with threshold."""
    mock_mgr = create_mock_chroma_mgr([
        {"content": "T1078: Valid Accounts", "metadata": {"technique_id": "T1078", "technique_name": "Valid Accounts"}},
    ])

    results = search_mitre_techniques(mock_mgr, "authentication failure", k=3, score_threshold=0.7)
    assert len(results) == 1
    assert results[0]["metadata"]["technique_id"] == "T1078"


def test_rag_search_threshold():
    """Test that threshold filters low-similarity results."""
    # Simulate ChromaDB returning results with different distances
    mock_mgr = MagicMock(spec=ChromaDBManager)
    mock_mgr.is_initialized = True

    # Mock search to return results with scores
    def mock_search(query, k=5, score_threshold=0.7):
        # Return different results based on threshold
        if score_threshold <= 0.7:
            return [
                {"content": "T1110: Brute Force", "metadata": {"technique_id": "T1110"}},
            ]
        return []

    mock_mgr.search = MagicMock(side_effect=mock_search)

    results = search_mitre_techniques(mock_mgr, "brute force", k=3, score_threshold=0.7)
    assert len(results) <= 1


def test_rag_search_no_results():
    """Test RAG search with no results."""
    mock_mgr = create_mock_chroma_mgr([])

    results = search_mitre_techniques(mock_mgr, "unknown attack", k=3, score_threshold=0.7)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_rag_search_single_event():
    """Test single event RAG search."""
    mock_llm = MagicMock(spec=BaseLanguageModel)
    mock_llm.ainvoke = AsyncMock(return_value="T1110 brute force")

    mock_mgr = create_mock_chroma_mgr([
        {"content": "T1110: Brute Force", "metadata": {"technique_id": "T1110", "technique_name": "Brute Force"}},
    ])

    result = await rag_search_single_event(
        llm=mock_llm,
        chroma_mgr=mock_mgr,
        description="Multiple failed login attempts",
        k=3,
        score_threshold=0.7,
    )

    assert result["has_match"] == True
    assert result["technique_id"] == "T1110"


@pytest.mark.asyncio
async def test_rag_search_single_event_no_match():
    """Test single event with no RAG match."""
    mock_llm = MagicMock(spec=BaseLanguageModel)
    mock_llm.ainvoke = AsyncMock(return_value="No relevant technique")

    mock_mgr = create_mock_chroma_mgr([])

    result = await rag_search_single_event(
        llm=mock_llm,
        chroma_mgr=mock_mgr,
        description="Normal user login",
        k=3,
        score_threshold=0.7,
    )

    assert result["has_match"] == False
    assert result["technique_id"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
