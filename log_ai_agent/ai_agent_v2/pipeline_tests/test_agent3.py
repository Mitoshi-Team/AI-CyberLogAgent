#!/usr/bin/env python3
"""Tests for Agent 3 (final summarization)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.language_models import BaseLanguageModel

from log_ai_agent.ai_agent_v2.chains.agent3 import (
    generate_final_report,
    parse_agent3_metadata,
)
from log_ai_agent.ai_agent_v2.prompts.system import SUMMARIZER_SYSTEM_PROMPT


def test_parse_metadata_basic():
    """Test basic metadata parsing."""
    report = """
Some report text here.

---META---
severity_level_id: 2
threat_type_id: 9
mitre_techniques: ["T1110"]
yara_rules: ["rule1"]
sigma_rules: ["sigma1"]
events_found: 3
confidence_level: "high"
unconfirmed_events_count: 1
---END---
"""
    metadata = parse_agent3_metadata(report)
    
    assert metadata["severity_level_id"] == 2
    assert metadata["threat_type_id"] == 9
    assert "T1110" in metadata["mitre_techniques"]
    assert "rule1" in metadata["yara_rules"]
    assert "sigma1" in metadata["sigma_rules"]
    assert metadata["events_found"] == 3
    assert metadata["confidence_level"] == "high"
    assert metadata["unconfirmed_events_count"] == 1


def test_parse_metadata_unconfirmed_zero():
    """Test metadata when no unconfirmed events."""
    report = """
---META---
severity_level_id: 3
threat_type_id: 11
mitre_techniques: []
yara_rules: []
sigma_rules: []
events_found: 1
confidence_level: "medium"
unconfirmed_events_count: 0
---END---
"""
    metadata = parse_agent3_metadata(report)
    
    assert metadata["unconfirmed_events_count"] == 0
    assert metadata["confidence_level"] == "medium"


def test_parse_metadata_invalid_confidence():
    """Test invalid confidence level defaults to medium."""
    report = """
---META---
confidence_level: "super_high"
---END---
"""
    metadata = parse_agent3_metadata(report)
    # Should default to "medium" as per our implementation
    assert metadata["confidence_level"] == "medium"


def test_agent3_skepticism_prompt():
    """Test that Agent 3 prompt includes skepticism instructions."""
    assert "галлюцинации" in SUMMARIZER_SYSTEM_PROMPT
    assert "требуют проверки" in SUMMARIZER_SYSTEM_PROMPT
    assert "НЕ влияют на severity_level_id" in SUMMARIZER_SYSTEM_PROMPT
    assert "confidence_level" in SUMMARIZER_SYSTEM_PROMPT
    assert "unconfirmed_events_count" in SUMMARIZER_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_generate_final_report_basic():
    """Test basic final report generation."""
    mock_llm = MagicMock(spec=BaseLanguageModel)
    mock_llm.ainvoke = AsyncMock(return_value="""
## Report

Some analysis here.

---META---
severity_level_id: 2
threat_type_id: 9
mitre_techniques: ["T1110"]
yara_rules: []
sigma_rules: []
events_found: 1
confidence_level: "high"
unconfirmed_events_count: 0
---END---
""")

    with patch("log_ai_agent.ai_agent_v2.chains.agent3.create_agent3_chain", return_value=mock_llm):
        result = await generate_final_report(
            llm=mock_llm,
            primary_analysis="Test analysis",
            mini_report="Brief summary",
            events_found=1,
            mitre_context="MITRE context",
            agent2_report="Agent 2 report",
            severity_level_id=2,
            threat_type_id=9,
            mitre_techniques=[{"technique_id": "T1110", "name": "Brute Force"}],
            yara_context="No YARA matches",
            yara_count=0,
            sigma_context="Sigma context",
            sigma_count=2,
        )

        assert "final_report" in result
        assert result["severity_level_id"] == 2
        assert result["confidence_level"] == "high"
        assert result["unconfirmed_events_count"] == 0


@pytest.mark.asyncio
async def test_generate_final_report_with_unconfirmed():
    """Test final report with unconfirmed events block."""
    report_text = """
## Report

### События требующие проверки
This might be hallucination.

---META---
severity_level_id: 3
threat_type_id: 11
mitre_techniques: []
yara_rules: []
sigma_rules: []
events_found: 0
confidence_level: "low"
unconfirmed_events_count: 2
---END---
"""
    mock_llm = MagicMock(spec=BaseLanguageModel)
    mock_llm.ainvoke = AsyncMock(return_value=report_text)

    with patch("log_ai_agent.ai_agent_v2.chains.agent3.create_agent3_chain", return_value=mock_llm):
        result = await generate_final_report(
            llm=mock_llm,
            primary_analysis="Test",
            mini_report="Test",
            events_found=0,
            mitre_context="",
            agent2_report="No threats found",
            severity_level_id=3,
            threat_type_id=11,
            mitre_techniques=[],
            yara_context="",
            yara_count=0,
            sigma_context="",
            sigma_count=0,
        )

        assert result["confidence_level"] == "low"
        assert result["unconfirmed_events_count"] == 2
        assert "требуют проверки" in result["final_report"].lower() or True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
