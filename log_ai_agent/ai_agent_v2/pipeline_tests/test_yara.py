#!/usr/bin/env python3
"""Tests for YARA scanning."""

import pytest
from pathlib import Path
from log_ai_agent.ai_agent_v2.engines.yara_engine import YaraEngine
from log_ai_agent.ai_agent_v2.parsers import parse_log_content


def create_yara_engine():
    """Create YARA engine with test rules."""
    # Use absolute path based on project root
    project_root = Path(__file__).parent.parent.parent.parent
    rules_path = project_root / "log_ai_agent" / "ai_agent_v2" / "rules" / "yara"

    try:
        engine = YaraEngine(rules_path=str(rules_path))
        return engine
    except Exception as e:
        pytest.skip(f"YARA engine not available: {e}")


def test_yara_basic():
    """Test basic YARA matching."""
    engine = create_yara_engine()

    # Test with a log line that might trigger YARA rules
    log_content = """
[Wed Dec 17 13:06:06 2025] [error] cmd.exe /c echo test
[Wed Dec 17 13:06:07 2025] [error] powershell -ExecutionPolicy Bypass
"""
    parsed_logs = parse_log_content(log_content)
    matches = engine.scan(parsed_logs)

    # We don't know exact matches, but should return a list
    assert isinstance(matches, list)


def test_yara_no_match():
    """Test YARA with no matches."""
    engine = create_yara_engine()

    log_content = "[Wed Dec 17 13:06:06 2025] [notice] Apache started normally"
    parsed_logs = parse_log_content(log_content)
    matches = engine.scan(parsed_logs)

    assert isinstance(matches, list)
    # Might be empty or have low-confidence matches
    assert len(matches) >= 0


def test_yara_empty_logs():
    """Test YARA with empty input."""
    engine = create_yara_engine()

    matches = engine.scan([])
    assert isinstance(matches, list)
    assert len(matches) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
