#!/usr/bin/env python3
"""Tests for Description Agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.language_models import BaseLanguageModel

from log_ai_agent.ai_agent_v2.chains.description_agent import (
    parse_description_response,
    generate_group_descriptions,
)
from log_ai_agent.ai_agent_v2.models_types import EventGroup, GroupDescription


def create_mock_llm(response_text: str) -> BaseLanguageModel:
    """Create a mock LLM that returns a fixed response."""
    mock = MagicMock(spec=BaseLanguageModel)
    mock.ainvoke = AsyncMock(return_value=response_text)
    return mock


def test_parse_description_response_json():
    """Test parsing JSON description from response."""
    response = '{"description": "Brute force attack from IP 89.23.74.19", "first_seen": "2025-12-17 13:00:00", "last_seen": "2025-12-17 13:05:00", "group_id": "g1"}'
    result = parse_description_response(response, "g1", "2025-12-17 13:00:00", "2025-12-17 13:05:00")

    assert isinstance(result, dict)
    assert result["group_id"] == "g1"
    assert "Brute force" in result["description"]


def test_parse_description_response_fallback():
    """Test fallback when JSON parsing fails."""
    response = "This is a plain text description without JSON format"
    result = parse_description_response(response, "g2", "2025-12-17 14:00:00", "2025-12-17 14:05:00")

    assert isinstance(result, dict)
    assert result["group_id"] == "g2"
    assert "plain text" in result["description"]


@pytest.mark.asyncio
async def test_generate_group_descriptions_basic():
    """Test basic description generation."""
    groups = [
        EventGroup(
            group_id="g1",
            events=[
                {"description": "Auth failed", "timestamp": "2025-12-17 13:00:00", "log_line": "line1"},
                {"description": "Auth failed", "timestamp": "2025-12-17 13:01:00", "log_line": "line2"},
            ],
            first_seen="2025-12-17 13:00:00",
            last_seen="2025-12-17 13:01:00",
        )
    ]

    mock_llm = create_mock_llm(
        '{"description": "Multiple authentication failures detected", "first_seen": "2025-12-17 13:00:00", "last_seen": "2025-12-17 13:01:00", "group_id": "g1"}'
    )

    descriptions = await generate_group_descriptions(mock_llm, groups)

    assert len(descriptions) == 1
    assert descriptions[0]["group_id"] == "g1"
    assert "authentication" in descriptions[0]["description"].lower()


@pytest.mark.asyncio
async def test_generate_group_descriptions_empty():
    """Test with empty groups list."""
    mock_llm = create_mock_llm("{}")
    descriptions = await generate_group_descriptions(mock_llm, [])
    assert len(descriptions) == 0


@pytest.mark.asyncio
async def test_generate_group_descriptions_multiple():
    """Test with multiple groups using mocked chain."""
    from unittest.mock import AsyncMock, patch

    groups = [
        EventGroup(
            group_id="g1",
            events=[
                {"description": "SSH auth failed", "timestamp": "2025-12-17 13:00:00", "log_line": "line1"},
            ],
            first_seen="2025-12-17 13:00:00",
            last_seen="2025-12-17 13:00:00",
        ),
        EventGroup(
            group_id="g2",
            events=[
                {"description": "SQL injection attempt", "timestamp": "2025-12-17 13:05:00", "log_line": "line2"},
            ],
            first_seen="2025-12-17 13:05:00",
            last_seen="2025-12-17 13:05:00",
        ),
    ]

    mock_chain = AsyncMock()
    mock_chain.ainvoke = AsyncMock(
        side_effect=[
            '{"description": "SSH brute force attack", "first_seen": "2025-12-17 13:00:00", "last_seen": "2025-12-17 13:00:00", "group_id": "g1"}',
            '{"description": "SQL injection attempt", "first_seen": "2025-12-17 13:05:00", "last_seen": "2025-12-17 13:05:00", "group_id": "g2"}',
        ]
    )

    mock_llm = MagicMock(spec=BaseLanguageModel)
    mock_llm.ainvoke = AsyncMock()

    with patch("log_ai_agent.ai_agent_v2.chains.description_agent.create_description_agent_chain", return_value=mock_chain):
        descriptions = await generate_group_descriptions(mock_llm, groups)

    assert len(descriptions) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])