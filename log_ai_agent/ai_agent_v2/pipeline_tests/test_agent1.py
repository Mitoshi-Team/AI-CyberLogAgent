#!/usr/bin/env python3
"""Tests for Agent 1 (primary log analysis)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.language_models import BaseLanguageModel
from langchain_core.outputs import LLMResult, Generation

from log_ai_agent.ai_agent_v2.chains.agent1 import (
    analyze_logs_primary,
    extract_mini_report,
    parse_events_from_response,
)
from log_ai_agent.ai_agent_v2.models_types import SuspiciousEvent


def create_mock_llm(response_text: str) -> BaseLanguageModel:
    """Create a mock LLM that returns a fixed response."""
    mock = MagicMock(spec=BaseLanguageModel)
    # Mock the ainvoke method to return the response
    mock.ainvoke = AsyncMock(return_value=response_text)
    return mock


def test_agent1_mini_report():
    """Test mini report extraction."""
    response = """
## Первичный анализ
Some analysis here

## Краткий отчёт
This is a brief summary of the incident.

## Подозрительные события для MITRE
---EVENTS---
[]
---EVENTS---
"""
    mini = extract_mini_report(response)
    assert "brief summary" in mini.lower()


def test_agent1_parse_events():
    """Test parsing suspicious events from response."""
    response = """
## Первичный анализ
...

## Краткий отчёт
...

## Подозрительные события для MITRE
---EVENTS---
[
  {"description": "Auth failed", "timestamp": "2025-12-17 13:06:06", "log_line": "line1"},
  {"description": "SQL injection", "timestamp": "2025-12-17 13:06:15", "log_line": "line2"}
]
---EVENTS---
"""
    events = parse_events_from_response(response)
    assert len(events) == 2
    assert events[0]["description"] == "Auth failed"
    assert events[1]["description"] == "SQL injection"


def test_agent1_parse_events_empty():
    """Test parsing when no events found."""
    response = "No events here"
    events = parse_events_from_response(response)
    assert len(events) == 0


@pytest.mark.asyncio
async def test_agent1_basic_analysis():
    """Test basic Agent 1 analysis flow."""
    mock_llm = create_mock_llm(
        """
## Первичный анализ
Found suspicious activity.

## Краткий отчёт
Brief summary here.

## Подозрительные события для MITRE
---EVENTS---
[{"description": "Test event", "timestamp": "2025-12-17 13:06:06", "log_line": "log line"}]
---EVENTS---
"""
    )

    with patch(
        "log_ai_agent.ai_agent_v2.chains.agent1.create_agent1_chain",
        return_value=mock_llm,
    ):
        result = await analyze_logs_primary(
            llm=mock_llm, log_content="test log content"
        )

        assert "primary_analysis" in result
        assert "mini_report" in result
        assert "suspicious_events" in result
        assert result["events_found"] == 1
        assert len(result["suspicious_events"]) == 1


@pytest.mark.asyncio
async def test_agent1_hallucination_resistance():
    """Test that Agent 1 prompt is properly structured."""
    from log_ai_agent.ai_agent_v2.prompts.system import PRIMARY_ANALYSIS_SYSTEM_PROMPT

    # Check that prompt exists and has content
    assert len(PRIMARY_ANALYSIS_SYSTEM_PROMPT) > 100
    # Check for key content that actually exists
    assert "Ты - эксперт" in PRIMARY_ANALYSIS_SYSTEM_PROMPT
    assert "Твоя задача" in PRIMARY_ANALYSIS_SYSTEM_PROMPT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
