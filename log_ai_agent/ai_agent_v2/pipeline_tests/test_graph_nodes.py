#!/usr/bin/env python3
"""Tests for PipelineNodes (graph_nodes.py)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from log_ai_agent.ai_agent_v2.chains.graph_nodes import PipelineNodes
from log_ai_agent.ai_agent_v2.models_types import AnalysisState, EventGroup, GroupDescription


def create_mock_llm():
    """Create a mock LLM."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value="mock response")
    return mock


def create_mock_chroma_mgr():
    """Create a mock ChromaDB manager."""
    mock = MagicMock()
    mock.is_initialized = True
    mock.hybrid_search = MagicMock(return_value=[])
    mock.search = MagicMock(return_value=[])
    return mock


def create_mock_yara_engine():
    """Create a mock YARA engine."""
    mock = MagicMock()
    mock.scan = MagicMock(return_value=[])
    return mock


def create_mock_sigma_engine():
    """Create a mock Sigma engine."""
    mock = MagicMock()
    mock.scan = MagicMock(return_value=[])
    return mock


class TestPipelineNodesInit:
    """Test PipelineNodes initialization."""

    def test_init_with_all_params(self):
        """Test that PipelineNodes initializes with all parameters."""
        llm = create_mock_llm()
        chroma = create_mock_chroma_mgr()
        yara = create_mock_yara_engine()
        sigma = create_mock_sigma_engine()

        nodes = PipelineNodes(
            llm=llm,
            chroma_mgr=chroma,
            yara_engine=yara,
            sigma_engine=sigma,
            use_rag=True,
            rag_top_k=5,
            rag_score_threshold=0.7,
            rag_parallelism=3,
        )

        assert nodes.llm is llm
        assert nodes.chroma_mgr is chroma
        assert nodes.yara_engine is yara
        assert nodes.sigma_engine is sigma
        assert nodes.use_rag is True
        assert nodes.rag_top_k == 5
        assert nodes.rag_score_threshold == 0.7

    def test_init_without_optional_params(self):
        """Test that PipelineNodes initializes with required params only."""
        llm = create_mock_llm()

        nodes = PipelineNodes(llm=llm)

        assert nodes.llm is llm
        assert nodes.chroma_mgr is None
        assert nodes.use_rag is False  # Disabled because no chroma_mgr

    def test_use_rag_disabled_when_no_chroma(self):
        """Test that use_rag is disabled when chroma_mgr is None."""
        llm = create_mock_llm()

        nodes = PipelineNodes(llm=llm, use_rag=True)
        assert nodes.use_rag is False  # Forced off because chroma_mgr is None

    def test_rag_semaphore_created(self):
        """Test that RAG semaphore is created for parallelism."""
        llm = create_mock_llm()

        nodes = PipelineNodes(llm=llm, rag_parallelism=5)
        assert nodes._rag_semaphore is not None
        assert isinstance(nodes._rag_semaphore, asyncio.Semaphore)


class TestPrefilterNode:
    """Test prefilter_node functionality."""

    @pytest.mark.asyncio
    async def test_prefilter_node_basic(self):
        """Test that prefilter_node filters logs."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm)

        state = AnalysisState(
            log_content="[error] Authentication failed\n[notice] Apache started",
        )

        result = await nodes.prefilter_node(state)

        assert "log_content" in result
        assert "prefilter_stats" in result
        assert isinstance(result["prefilter_stats"], dict)

    @pytest.mark.asyncio
    async def test_prefilter_node_empty_logs(self):
        """Test that prefilter_node handles empty logs."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm)

        state = AnalysisState(log_content="")

        result = await nodes.prefilter_node(state)

        assert "log_content" in result
        assert "prefilter_stats" in result

    @pytest.mark.asyncio
    async def test_prefilter_node_preserves_stats(self):
        """Test that prefilter_node preserves stats keys."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm)

        state = AnalysisState(
            log_content="[error] Test error\n[error] Another error",
        )

        result = await nodes.prefilter_node(state)

        stats = result["prefilter_stats"]
        assert "original_lines" in stats
        assert "kept_lines" in stats
        assert "filtered_lines" in stats


class TestParseLogsNode:
    """Test parse_logs_node functionality."""

    @pytest.mark.asyncio
    async def test_parse_logs_node_basic(self):
        """Test that parse_logs_node parses log content."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm)

        state = AnalysisState(
            log_content="[Wed Dec 17 13:06:06 2025] [error] Authentication failed",
        )

        result = await nodes.parse_logs_node(state)

        assert "parsed_logs" in result
        assert isinstance(result["parsed_logs"], list)

    @pytest.mark.asyncio
    async def test_parse_logs_node_empty(self):
        """Test that parse_logs_node handles empty logs."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm)

        state = AnalysisState(log_content="")

        result = await nodes.parse_logs_node(state)

        assert "parsed_logs" in result
        assert isinstance(result["parsed_logs"], list)


class TestDescriptionAgentNode:
    """Test description_agent_node functionality."""

    @pytest.mark.asyncio
    async def test_description_agent_empty_groups(self):
        """Test that description_agent handles empty groups."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm)

        state = AnalysisState(groups=[])

        result = await nodes.description_agent_node(state)

        assert result["group_descriptions"] == []

    @pytest.mark.asyncio
    async def test_description_agent_no_groups_key(self):
        """Test that description_agent handles missing groups key."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm)

        state = AnalysisState()

        result = await nodes.description_agent_node(state)

        assert result["group_descriptions"] == []


class TestYaraScanNode:
    """Test yara_scan_node functionality."""

    @pytest.mark.asyncio
    async def test_yara_scan_no_engine(self):
        """Test that yara_scan_node handles missing engine."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm)  # No yara_engine

        state = AnalysisState(parsed_logs=[])

        result = await nodes.yara_scan_node(state)

        assert result["yara_matches"] == []
        assert result["yara_rules_matched"] == []
        assert "not configured" in result["yara_context"].lower()

    @pytest.mark.asyncio
    async def test_yara_scan_with_engine(self):
        """Test that yara_scan_node uses engine when available."""
        llm = create_mock_llm()
        yara = create_mock_yara_engine()
        yara.scan = MagicMock(return_value=[
            {"rule": "TestRule", "description": "Test match", "matched_strings": ["test"]}
        ])

        nodes = PipelineNodes(llm=llm, yara_engine=yara)

        state = AnalysisState(parsed_logs=[{"raw": "test log"}])

        result = await nodes.yara_scan_node(state)

        assert "yara_matches" in result
        yara.scan.assert_called_once()


class TestSigmaScanNode:
    """Test sigma_scan_node functionality."""

    @pytest.mark.asyncio
    async def test_sigma_scan_no_engine(self):
        """Test that sigma_scan_node handles missing engine."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm)  # No sigma_engine

        state = AnalysisState(parsed_logs=[])

        result = await nodes.sigma_scan_node(state)

        assert result["sigma_matches"] == []
        assert result["sigma_rules_matched"] == []
        assert "not configured" in result["sigma_context"].lower()

    @pytest.mark.asyncio
    async def test_sigma_scan_with_engine(self):
        """Test that sigma_scan_node uses engine when available."""
        llm = create_mock_llm()
        sigma = create_mock_sigma_engine()
        sigma.scan = MagicMock(return_value=[
            {"rule_id": "sigma_test", "title": "Test Sigma", "description": "Test", "severity": "medium"}
        ])

        nodes = PipelineNodes(llm=llm, sigma_engine=sigma)

        state = AnalysisState(parsed_logs=[{"raw": "test log"}])

        result = await nodes.sigma_scan_node(state)

        assert "sigma_matches" in result
        sigma.scan.assert_called_once()


class TestAgent2Node:
    """Test agent2_node functionality (RAG)."""

    @pytest.mark.asyncio
    async def test_agent2_node_rag_disabled(self):
        """Test that agent2_node handles disabled RAG."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm, use_rag=False)

        state = AnalysisState(group_descriptions=[])

        result = await nodes.agent2_node(state)

        assert result["mitre_context"] == "RAG (MITRE ATT&CK) is disabled."
        assert result["mitre_techniques_final"] == []
        assert result["technique_ids"] == []

    @pytest.mark.asyncio
    async def test_agent2_node_no_chroma(self):
        """Test that agent2_node handles missing chroma_mgr."""
        llm = create_mock_llm()
        nodes = PipelineNodes(llm=llm, use_rag=True)  # RAG requested but no chroma

        state = AnalysisState(group_descriptions=[])

        result = await nodes.agent2_node(state)

        assert "disabled" in result["mitre_context"].lower() or "not" in result["mitre_context"].lower()


class TestFormatContexts:
    """Test _format_yara_context and _format_sigma_context."""

    def test_format_yara_context_empty(self):
        """Test that _format_yara_context handles empty matches."""
        result = PipelineNodes._format_yara_context([])
        assert "no" in result.lower()
        assert "matches" in result.lower()

    def test_format_yara_context_with_matches(self):
        """Test that _format_yara_context formats matches correctly."""
        matches = [
            {"rule": "SQLInjection", "description": "SQL injection detected", "matched_strings": ["OR 1=1"]},
            {"rule": "XSSAttack", "description": "XSS attack", "matched_strings": ["<script>"]},
        ]
        result = PipelineNodes._format_yara_context(matches)
        assert "SQLInjection" in result
        assert "XSSAttack" in result
        assert "SQL injection detected" in result

    def test_format_sigma_context_empty(self):
        """Test that _format_sigma_context handles empty matches."""
        result = PipelineNodes._format_sigma_context([])
        assert "no" in result.lower()
        assert "matches" in result.lower()

    def test_format_sigma_context_with_matches(self):
        """Test that _format_sigma_context formats matches correctly."""
        matches = [
            {"title": "Brute Force", "description": "Multiple login failures", "severity": "high"},
        ]
        result = PipelineNodes._format_sigma_context(matches)
        assert "Brute Force" in result
        assert "Multiple login failures" in result
        assert "high" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])