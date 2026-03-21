"""Tests for AI Agent v2 pipeline."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from log_ai_agent.ai_agent_v2.gigachat_client import GigaChatClient, GigaChatAPIError
from log_ai_agent.ai_agent_v2.models.schemas import (
    PrimaryAnalysisResult,
    MITREResult,
    FinalAnalysisResult,
    FullPipelineResult,
)


# =============================================================================
# Tests for GigaChatClient
# =============================================================================

class TestGigaChatClient:
    """Tests for GigaChat API client."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return GigaChatClient(
            api_key="test_key",
            temperature=0.1,
            max_tokens=1000,
            rate_limit_delay=0,  # Disable for tests
        )

    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client initializes with correct settings."""
        assert client.temperature == 0.1
        assert client.max_tokens == 1000
        assert client.rate_limit_delay == 0

    @pytest.mark.asyncio
    async def test_chat_request_format(self, client):
        """Test chat method formats request correctly."""
        # Mock the _make_request method
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Test response"
                    }
                }
            ]
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            response = await client.chat(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful",
            )
            
            assert response == "Test response"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_empty_response(self, client):
        """Test chat handles empty response."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"choices": []}
            
            with pytest.raises(GigaChatAPIError):
                await client.chat(messages=[{"role": "user", "content": "Hello"}])

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager."""
        async with client as c:
            assert c is client
        
        # Session should be closed after exit
        assert client._session is None or client._session.closed


# =============================================================================
# Tests for Pipeline Models
# =============================================================================

class TestPipelineModels:
    """Tests for Pydantic models."""

    def test_primary_analysis_result_success(self):
        """Test PrimaryAnalysisResult with success."""
        result = PrimaryAnalysisResult(
            success=True,
            analysis_text="Found 3 suspicious events",
            events_found=3,
            processing_time_ms=1500.0,
        )
        
        assert result.success is True
        assert result.events_found == 3
        assert "suspicious" in result.analysis_text

    def test_primary_analysis_result_failure(self):
        """Test PrimaryAnalysisResult with failure."""
        result = PrimaryAnalysisResult(
            success=False,
            analysis_text="",
            error_message="API timeout",
        )
        
        assert result.success is False
        assert result.error_message == "API timeout"

    def test_mitre_result_success(self):
        """Test MITREResult with techniques."""
        result = MITREResult(
            success=True,
            techniques=[
                {"id": "T1059", "name": "Command and Scripting Interpreter"},
                {"id": "T1078", "name": "Valid Accounts"},
            ],
            context_text="Found 2 techniques",
        )
        
        assert result.success is True
        assert len(result.techniques) == 2

    def test_final_analysis_result_validation(self):
        """Test FinalAnalysisResult field validation."""
        result = FinalAnalysisResult(
            success=True,
            report_text="Detailed report...",
            severity_level_id=2,
            threat_type_id=5,
            mitre_techniques=["T1059", "T1078"],
        )
        
        assert result.severity_level_id == 2
        assert result.threat_type_id == 5
        assert len(result.mitre_techniques) == 2

    def test_final_analysis_result_invalid_severity(self):
        """Test FinalAnalysisResult rejects invalid severity."""
        with pytest.raises(Exception):  # Validation error
            FinalAnalysisResult(
                success=True,
                report_text="Report",
                severity_level_id=10,  # Invalid: must be 1-4
                threat_type_id=5,
            )

    def test_full_pipeline_result_properties(self):
        """Test FullPipelineResult helper properties."""
        final_result = FinalAnalysisResult(
            success=True,
            report_text="Final report",
            severity_level_id=1,
            threat_type_id=2,
            mitre_techniques=["T1059"],
        )
        
        full_result = FullPipelineResult(
            success=True,
            primary_analysis=None,
            mitre_result=None,
            final_result=final_result,
            log_size_bytes=5000,
        )
        
        assert full_result.report_text == "Final report"
        assert full_result.severity_level_id == 1
        assert full_result.threat_type_id == 2


# =============================================================================
# Integration Tests (Mocked)
# =============================================================================

class TestPipelineIntegration:
    """Integration tests for complete pipeline."""

    @pytest.fixture
    def mock_gigachat(self):
        """Create mock GigaChat client."""
        mock = AsyncMock(spec=GigaChatClient)
        mock.chat = AsyncMock(return_value="Mock response")
        return mock

    @pytest.fixture
    def mock_chroma(self):
        """Create mock ChromaDB manager."""
        mock = MagicMock()
        mock.is_available = True
        mock.search = MagicMock(return_value=[
            {
                "content": "T1059 description",
                "metadata": {"technique_id": "T1059", "tactic": "Execution"}
            }
        ])
        return mock

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, mock_gigachat, mock_chroma):
        """Test pipeline initializes correctly."""
        from log_ai_agent.ai_agent_v2.pipeline.analyzer import LogAnalysisPipeline
        
        pipeline = LogAnalysisPipeline(
            gigachat_client=mock_gigachat,
            chroma_manager=mock_chroma,
            use_rag=True,
        )
        
        assert pipeline.use_rag is True
        assert pipeline.rag_retriever is not None

    @pytest.mark.asyncio
    async def test_pipeline_without_rag(self, mock_gigachat):
        """Test pipeline works without RAG."""
        from log_ai_agent.ai_agent_v2.pipeline.analyzer import LogAnalysisPipeline
        
        pipeline = LogAnalysisPipeline(
            gigachat_client=mock_gigachat,
            chroma_manager=None,
            use_rag=False,
        )
        
        assert pipeline.use_rag is False
        assert pipeline.rag_retriever is None

    @pytest.mark.asyncio
    async def test_analyze_log_success(self, mock_gigachat):
        """Test successful log analysis."""
        from log_ai_agent.ai_agent_v2.pipeline.analyzer import LogAnalysisPipeline
        
        # Setup mock responses
        mock_gigachat.chat.side_effect = [
            # Agent 1 response
            "## Обнаруженные события\n\n### Событие 1: SQL Injection attempt",
            # Agent 2 response  
            "## Отчёт\n\nОписание...\n\n---META---\nseverity_level_id: 2\nthreat_type_id: 7\n---END---",
        ]
        
        pipeline = LogAnalysisPipeline(
            gigachat_client=mock_gigachat,
            chroma_manager=None,
            use_rag=False,
        )
        
        result = await pipeline.analyze_log("Sample log content")
        
        assert result.success is True
        assert result.final_result is not None
        assert result.final_result.severity_level_id == 2
        assert result.final_result.threat_type_id == 7

    @pytest.mark.asyncio
    async def test_analyze_log_timeout(self, mock_gigachat):
        """Test pipeline handles timeout."""
        from log_ai_agent.ai_agent_v2.pipeline.analyzer import LogAnalysisPipeline
        
        # Simulate timeout
        mock_gigachat.chat = AsyncMock(side_effect=asyncio.TimeoutError())
        
        pipeline = LogAnalysisPipeline(
            gigachat_client=mock_gigachat,
            chroma_manager=None,
            use_rag=False,
        )
        
        result = await pipeline.analyze_log("Sample log", timeout_seconds=1)
        
        assert result.success is False
        assert result.final_result.error_message is not None


# =============================================================================
# Prompt Tests
# =============================================================================

class TestPrompts:
    """Tests for prompt templates."""

    def test_primary_analysis_prompt_format(self):
        """Test primary analysis prompt formatting."""
        from log_ai_agent.ai_agent_v2.prompts.log_analysis import (
            PRIMARY_ANALYSIS_USER_PROMPT,
        )
        
        formatted = PRIMARY_ANALYSIS_USER_PROMPT.format(
            log_content="Test log content"
        )
        
        assert "Test log content" in formatted
        assert "ЛОГ-ФАЙЛ:" in formatted
        assert "ЗАДАЧА:" in formatted

    def test_system_prompts_exist(self):
        """Test system prompts are defined."""
        from log_ai_agent.ai_agent_v2.prompts.system import (
            PRIMARY_ANALYSIS_SYSTEM_PROMPT,
            FINAL_REPORT_SYSTEM_PROMPT,
        )
        
        assert "эксперт по анализу логов" in PRIMARY_ANALYSIS_SYSTEM_PROMPT
        assert "старший эксперт по кибербезопасности" in FINAL_REPORT_SYSTEM_PROMPT
        assert "---META---" in FINAL_REPORT_SYSTEM_PROMPT


# =============================================================================
# Metadata Parsing Tests
# =============================================================================

class TestMetadataParsing:
    """Tests for metadata parsing from Agent 2 responses."""

    @pytest.fixture
    def pipeline(self, mock_gigachat):
        """Create pipeline for testing metadata parsing."""
        from log_ai_agent.ai_agent_v2.pipeline.analyzer import LogAnalysisPipeline
        
        return LogAnalysisPipeline(
            gigachat_client=mock_gigachat,
            chroma_manager=None,
            use_rag=False,
        )

    def test_parse_metadata_complete(self, pipeline):
        """Test parsing complete metadata block."""
        response = """
        ## Отчёт
        
        Описание инцидента...
        
        ---META---
        severity_level_id: 1
        threat_type_id: 2
        mitre_techniques: ["T1059", "T1078"]
        ---END---
        """
        
        severity, threat, techniques = pipeline._parse_metadata(response)
        
        assert severity == 1
        assert threat == 2
        assert "T1059" in techniques
        assert "T1078" in techniques

    def test_parse_metadata_defaults(self, pipeline):
        """Test parsing uses defaults when metadata missing."""
        response = "## Отчёт\n\nОписание без метаданных..."
        
        severity, threat, techniques = pipeline._parse_metadata(response)
        
        assert severity == 3  # Default: Medium
        assert threat == 11   # Default: Other
        assert techniques == []

    def test_parse_metadata_invalid_values(self, pipeline):
        """Test parsing handles invalid values."""
        response = """
        ---META---
        severity_level_id: 999
        threat_type_id: invalid
        ---END---
        """
        
        severity, threat, techniques = pipeline._parse_metadata(response)
        
        assert severity == 3  # Falls back to default (out of range)
        assert threat == 11   # Falls back to default (invalid)
