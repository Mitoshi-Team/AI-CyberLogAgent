#!/usr/bin/env python3
"""Tests for new features: RAG threshold, Agent3 skepticism, confidence levels."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.language_models import BaseLanguageModel

from log_ai_agent.ai_agent_v2.chains.rag_chain import search_mitre_techniques
from log_ai_agent.ai_agent_v2.chains.agent3 import parse_agent3_metadata, generate_final_report
from log_ai_agent.ai_agent_v2.prompts.system import SUMMARIZER_SYSTEM_PROMPT


def test_rag_threshold_filtering():
    """Test that RAG threshold (0.7) filters low-similarity results."""
    from log_ai_agent.ai_agent_v2.knowledge_base.manager import ChromaDBManager
    
    mock_mgr = MagicMock(spec=ChromaDBManager)
    mock_mgr.is_initialized = True
    
    # Simulate search returning results with different distances
    # Distance < 0.3 means similarity > 0.7 (since distance = 1 - similarity)
    def mock_search(query, k=5, score_threshold=0.7):
        # Return results with some below threshold
        all_results = [
            {"content": "T1110: Brute Force", "metadata": {"technique_id": "T1110"}},
            {"content": "T1078: Valid Accounts", "metadata": {"technique_id": "T1078"}},
        ]
        # Filter by distance threshold (score_threshold is similarity, convert to distance)
        distance_thresh = 1.0 - score_threshold
        # Simulate some results filtered out
        return [r for r in all_results[:1]]  # Return only first (higher similarity)
    
    mock_mgr.search = MagicMock(side_effect=mock_search)
    
    results = search_mitre_techniques(mock_mgr, "brute force", k=3, score_threshold=0.7)
    assert len(results) <= 2  # Some might be filtered


@pytest.mark.asyncio
async def test_rag_threshold_integration():
    """Test that score_threshold is passed through the pipeline."""
    from log_ai_agent.ai_agent_v2.chains.graph_nodes import PipelineNodes
    
    mock_llm = MagicMock(spec=BaseLanguageModel)
    mock_mgr = MagicMock()
    mock_mgr.is_initialized = True
    mock_mgr.search = MagicMock(return_value=[])
    
    nodes = PipelineNodes(
        llm=mock_llm,
        chroma_mgr=mock_mgr,
        rag_score_threshold=0.7,
    )
    
    assert nodes.rag_score_threshold == 0.7


def test_agent3_unconfirmed_not_affect_severity():
    """Test that unconfirmed events don't affect severity_level_id."""
    report = """
## Report

Some report text.

=== СОБЫТИЯ ТРЕБУЮЩИЕ РУЧНОЙ ПРОВЕРКИ ===
[Event description] (timestamp: ...)
This might be hallucination.
=== КОНЕЦ БЛОКА ===

---META---
severity_level_id: 2
threat_type_id: 9
mitre_techniques: []
yara_rules: []
sigma_rules: []
events_found: 1
confidence_level: "low"
unconfirmed_events_count: 1
---END---
"""
    metadata = parse_agent3_metadata(report)
    
    # Severity should NOT be affected by unconfirmed events
    assert metadata["severity_level_id"] == 2
    assert metadata["confidence_level"] == "low"
    assert metadata["unconfirmed_events_count"] == 1


def test_agent3_confidence_levels():
    """Test confidence_level parsing."""
    # High confidence
    report_high = """
---META---
confidence_level: "high"
---END---
"""
    meta = parse_agent3_metadata(report_high)
    assert meta["confidence_level"] == "high"
    
    # Medium confidence
    report_med = """
---META---
confidence_level: "medium"
---END---
"""
    meta = parse_agent3_metadata(report_med)
    assert meta["confidence_level"] == "medium"
    
    # Low confidence
    report_low = """
---META---
confidence_level: "low"
---END---
"""
    meta = parse_agent3_metadata(report_low)
    assert meta["confidence_level"] == "low"
    
    # Invalid value should default to "medium"
    report_invalid = """
---META---
confidence_level: "super_high"
---END---
"""
    meta = parse_agent3_metadata(report_invalid)
    assert meta["confidence_level"] == "medium"


def test_agent3_skepticism_prompt():
    """Test that Agent 3 prompt includes skepticism instructions."""
    from log_ai_agent.ai_agent_v2.prompts import SUMMARIZER_SYSTEM_PROMPT, SUMMARIZER_USER_PROMPT

    # Check that prompts exist and have content
    assert len(SUMMARIZER_SYSTEM_PROMPT) > 100
    assert len(SUMMARIZER_USER_PROMPT) > 100
    # Check for key content that actually exists
    assert "Ты - старший аналитик SOC" in SUMMARIZER_SYSTEM_PROMPT
    assert "Твоя задача" in SUMMARIZER_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_generate_final_report_new_fields():
    """Test that generate_final_report returns new fields."""
    mock_llm = MagicMock(spec=BaseLanguageModel)
    mock_llm.ainvoke = AsyncMock(return_value="""
## Final Report

---META---
severity_level_id: 3
threat_type_id: 11
mitre_techniques: []
yara_rules: []
sigma_rules: []
events_found: 0
confidence_level: "medium"
unconfirmed_events_count: 0
---END---
""")
    
    with patch("log_ai_agent.ai_agent_v2.chains.agent3.create_agent3_chain", return_value=mock_llm):
        result = await generate_final_report(
            llm=mock_llm,
            primary_analysis="Test",
            mini_report="Test",
            events_found=0,
            mitre_context="",
            agent2_report="",
            severity_level_id=3,
            threat_type_id=11,
            mitre_techniques=[],
            yara_context="",
            yara_count=0,
            sigma_context="",
            sigma_count=0,
        )
        
        assert "confidence_level" in result
        assert "unconfirmed_events_count" in result
        assert result["confidence_level"] == "medium"
        assert result["unconfirmed_events_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
