#!/usr/bin/env python3
"""Tests for Agent 1 (primary log analysis with grouping)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.language_models import BaseLanguageModel
from langchain_core.outputs import LLMResult, Generation

from log_ai_agent.ai_agent_v2.chains.agent1 import (
    analyze_logs_primary,
    extract_mini_report,
    parse_groups_from_response,
    parse_events_from_response,
)
from log_ai_agent.ai_agent_v2.models_types import EventGroup, SuspiciousEvent


def create_mock_llm(response_text: str) -> BaseLanguageModel:
    """Create a mock LLM that returns a fixed response."""
    mock = MagicMock(spec=BaseLanguageModel)
    mock.ainvoke = AsyncMock(return_value=response_text)
    return mock


def test_agent1_mini_report():
    """Test mini report extraction."""
    response = """
## Первичный анализ
Some analysis here

## Краткий отчёт
This is a brief summary of the incident.

## Группы событий для MITRE
---GROUPS---
[]
---GROUPS---
"""
    mini = extract_mini_report(response)
    assert "brief summary" in mini.lower()


def test_agent1_parse_groups():
    """Test parsing event groups from response."""
    response = """
## Первичный анализ
...

## Краткий отчёт
...

## Группы событий для MITRE
---GROUPS---
[
  {
    "group_id": "g1",
    "events": [
      {"description": "Auth failed", "timestamp": "2025-12-17 13:06:06", "log_line": "line1"},
      {"description": "Auth failed again", "timestamp": "2025-12-17 13:06:15", "log_line": "line2"}
    ],
    "first_seen": "2025-12-17 13:06:06",
    "last_seen": "2025-12-17 13:06:15"
  },
  {
    "group_id": "g2",
    "events": [
      {"description": "SQL injection attempt", "timestamp": "2025-12-17 13:07:00", "log_line": "line3"}
    ],
    "first_seen": "2025-12-17 13:07:00",
    "last_seen": "2025-12-17 13:07:00"
  }
]
---GROUPS---
"""
    groups = parse_groups_from_response(response)
    assert len(groups) == 2
    assert groups[0]["group_id"] == "g1"
    assert len(groups[0]["events"]) == 2
    assert groups[1]["group_id"] == "g2"
    assert len(groups[1]["events"]) == 1


def test_agent1_parse_groups_empty():
    """Test parsing when no groups found."""
    response = "No groups here"
    groups = parse_groups_from_response(response)
    assert len(groups) == 0


def test_parse_groups_with_brackets_in_log_lines():
    """Test parsing groups when log_lines contain brackets (Apache format).

    This was broken by the old regex: the non-greedy match stopped at the
    first ']' inside a log_line value, producing truncated invalid JSON.
    """
    response = """## Группы событий для MITRE
---GROUPS---
[
  {
    "group_id": "g1",
    "events": [
      {
        "description": "File descriptor limit reached",
        "timestamp": "2025-12-17 01:15:29",
        "log_line": "[Wed Dec 17 01:15:29 2025] [crit] File descriptor limit reached, cannot accept connections"
      },
      {
        "description": "MaxClients reached",
        "timestamp": "2025-12-17 01:16:20",
        "log_line": "[Wed Dec 17 01:16:20 2025] [crit] Server reached MaxClients setting, refusing new connections"
      }
    ],
    "first_seen": "2025-12-17 01:15:29",
    "last_seen": "2025-12-17 01:16:20",
    "keywords": ["file descriptor", "MaxClients", "отказ в обслуживании"],
    "description": "Обнаружено исчерпание ресурсов сервера."
  }
]
---GROUPS---
"""
    groups = parse_groups_from_response(response)
    assert len(groups) == 1
    assert groups[0]["group_id"] == "g1"
    assert len(groups[0]["events"]) == 2
    assert "File descriptor" in groups[0]["events"][0]["description"]
    assert "MaxClients" in groups[0]["events"][1]["description"]


def test_parse_groups_multiple_brackets_in_log_line():
    """Test parsing groups with many bracket pairs in log lines."""
    response = """---GROUPS---
[
  {
    "group_id": "g1",
    "events": [
      {
        "description": "Auth failed",
        "timestamp": "2025-12-17 13:06:06",
        "log_line": "[Wed Dec 17 13:06:06 2025] [error] [client 89.23.74.19] Authentication failed for user 'admin'"
      }
    ],
    "first_seen": "2025-12-17 13:06:06",
    "last_seen": "2025-12-17 13:06:06",
    "keywords": ["брутфорс", "аутентификация"],
    "description": "Зафиксирована неудачная попытка аутентификации."
  }
]
---GROUPS---
"""
    groups = parse_groups_from_response(response)
    assert len(groups) == 1
    assert len(groups[0]["events"]) == 1
    assert "89.23.74.19" in groups[0]["events"][0]["log_line"]


def test_parse_groups_with_nested_braces_in_description():
    """Test parsing groups with JSON-like text in description."""
    response = """---GROUPS---
[
  {
    "group_id": "g1",
    "events": [
      {
        "description": "SQL injection with payload: {'OR': '1=1'}",
        "timestamp": "2025-12-17 13:06:06",
        "log_line": "GET /search?q='OR'1'='1 HTTP/1.1"
      }
    ],
    "first_seen": "2025-12-17 13:06:06",
    "last_seen": "2025-12-17 13:06:06",
    "keywords": ["sql injection"],
    "description": "Обнаружена SQL-инъекция."
  }
]
---GROUPS---
"""
    groups = parse_groups_from_response(response)
    assert len(groups) == 1
    assert "1=1" in groups[0]["events"][0]["description"]


def test_parse_groups_missing_optional_fields():
    """Test parsing groups with missing optional fields."""
    response = """---GROUPS---
[
  {
    "group_id": "g1",
    "events": [
      {"description": "Event", "timestamp": "2025-12-17 13:06:06", "log_line": "line1"}
    ]
  }
]
---GROUPS---
"""
    groups = parse_groups_from_response(response)
    assert len(groups) == 1
    assert groups[0]["group_id"] == "g1"
    assert groups[0]["events"] == [{"description": "Event", "timestamp": "2025-12-17 13:06:06", "log_line": "line1"}]
    assert groups[0].get("first_seen") == ""
    assert groups[0].get("last_seen") == ""
    assert groups[0].get("keywords") == []
    assert groups[0].get("description") == ""


def test_parse_groups_empty_array():
    """Test parsing empty groups array."""
    response = """---GROUPS---
[]
---GROUPS---
"""
    groups = parse_groups_from_response(response)
    assert len(groups) == 0


def test_parse_groups_malformed_json():
    """Test parsing groups with malformed JSON returns empty."""
    response = """---GROUPS---
[{bad json here}]
---GROUPS---
"""
    groups = parse_groups_from_response(response)
    assert len(groups) == 0


def test_parse_groups_no_closing_marker():
    """Test parsing when closing marker is missing — uses raw_decode fallback."""
    response = """---GROUPS---
[{"group_id": "g1", "events": []}]
"""
    groups = parse_groups_from_response(response)
    assert len(groups) == 1
    assert groups[0]["group_id"] == "g1"


def test_parse_groups_keywords_ru_fallback():
    """Test that keywords_ru is used as fallback when keywords missing."""
    response = """---GROUPS---
[
  {
    "group_id": "g1",
    "events": [{"description": "Test", "timestamp": "2025-12-17 13:06:06", "log_line": "line1"}],
    "first_seen": "2025-12-17 13:06:06",
    "last_seen": "2025-12-17 13:06:06",
    "keywords_ru": ["тест", "проверка"],
    "description": "Тестовое событие."
  }
]
---GROUPS---
"""
    groups = parse_groups_from_response(response)
    assert len(groups) == 1
    assert groups[0]["keywords"] == ["тест", "проверка"]


def test_agent1_parse_events_from_groups():
    """Test that parse_events_from_response flattens groups."""
    response = """
## Группы событий для MITRE
---GROUPS---
[
  {
    "group_id": "g1",
    "events": [
      {"description": "Event 1", "timestamp": "2025-12-17 13:06:06", "log_line": "line1"},
      {"description": "Event 2", "timestamp": "2025-12-17 13:06:15", "log_line": "line2"}
    ],
    "first_seen": "2025-12-17 13:06:06",
    "last_seen": "2025-12-17 13:06:15"
  }
]
---GROUPS---
"""
    events = parse_events_from_response(response)
    assert len(events) == 2
    assert events[0]["description"] == "Event 1"
    assert events[1]["description"] == "Event 2"


@pytest.mark.asyncio
async def test_agent1_basic_analysis():
    """Test basic Agent 1 analysis flow with groups."""
    mock_llm = create_mock_llm(
        """
## Первичный анализ
Found suspicious activity.

## Краткий отчёт
Brief summary here.

## Группы событий для MITRE
---GROUPS---
[
  {
    "group_id": "g1",
    "events": [
      {"description": "Test event", "timestamp": "2025-12-17 13:06:06", "log_line": "log line"}
    ],
    "first_seen": "2025-12-17 13:06:06",
    "last_seen": "2025-12-17 13:06:06"
  }
]
---GROUPS---
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
        assert "groups" in result
        assert result["events_found"] == 1
        assert len(result["groups"]) == 1
        assert result["groups"][0]["group_id"] == "g1"


@pytest.mark.asyncio
async def test_agent1_multiple_events_in_group():
    """Test that multiple events in group are counted correctly."""
    mock_llm = create_mock_llm(
        """
## Первичный анализ
Found brute force attack.

## Краткий отчёт
Multiple auth failures detected.

## Группы событий для MITRE
---GROUPS---
[
  {
    "group_id": "g1",
    "events": [
      {"description": "Auth failed", "timestamp": "2025-12-17 13:00:00", "log_line": "line1"},
      {"description": "Auth failed", "timestamp": "2025-12-17 13:01:00", "log_line": "line2"},
      {"description": "Auth failed", "timestamp": "2025-12-17 13:02:00", "log_line": "line3"},
      {"description": "Auth failed", "timestamp": "2025-12-17 13:03:00", "log_line": "line4"},
      {"description": "Auth failed", "timestamp": "2025-12-17 13:04:00", "log_line": "line5"}
    ],
    "first_seen": "2025-12-17 13:00:00",
    "last_seen": "2025-12-17 13:04:00"
  }
]
---GROUPS---
"""
    )

    with patch(
        "log_ai_agent.ai_agent_v2.chains.agent1.create_agent1_chain",
        return_value=mock_llm,
    ):
        result = await analyze_logs_primary(
            llm=mock_llm, log_content="test log content"
        )

        assert result["events_found"] == 5
        assert len(result["groups"]) == 1
        assert result["groups"][0]["first_seen"] == "2025-12-17 13:00:00"
        assert result["groups"][0]["last_seen"] == "2025-12-17 13:04:00"


@pytest.mark.asyncio
async def test_agent1_hallucination_resistance():
    """Test that Agent 1 prompt is properly structured."""
    from log_ai_agent.ai_agent_v2.prompts.system import PRIMARY_ANALYSIS_SYSTEM_PROMPT

    assert len(PRIMARY_ANALYSIS_SYSTEM_PROMPT) > 100
    assert "Ты — эксперт" in PRIMARY_ANALYSIS_SYSTEM_PROMPT
    assert "Твоя задача" in PRIMARY_ANALYSIS_SYSTEM_PROMPT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])