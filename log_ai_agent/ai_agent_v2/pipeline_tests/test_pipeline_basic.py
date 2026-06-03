#!/usr/bin/env python3
"""Basic pipeline tests."""

import pytest
import asyncio
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from log_ai_agent.ai_agent_v2 import create_pipeline
from log_ai_agent.ai_agent_v2.callbacks import get_callback_config


def test_basic_flow():
    """Test basic pipeline flow with simple logs."""
    log_content = """
[Wed Dec 17 13:06:06 2025] [error] Authentication failed for user admin
[Wed Dec 17 13:06:07 2025] [error] Multiple failed login attempts
"""

    async def run():
        pipeline = await create_pipeline(use_rag=False)
        results = await pipeline.analyze(
            log_content=log_content,
            config=get_callback_config(show_output=False),
        )
        assert results["success"] is True
        assert results["events_found"] >= 0
        return results

    results = asyncio.run(run())
    assert "stages" in results


def test_empty_logs():
    """Test pipeline with empty logs."""
    async def run():
        pipeline = await create_pipeline(use_rag=False)
        results = await pipeline.analyze(
            log_content="",
            config=get_callback_config(show_output=False),
        )
        # Should not crash
        assert results["success"] is True or results["success"] is False  # Either way, no crash
        return results

    asyncio.run(run())


def test_no_rag():
    """Test pipeline with RAG disabled."""
    log_content = "[Wed Dec 17 13:06:06 2025] [error] Authentication failed"

    async def run():
        pipeline = await create_pipeline(use_rag=False)
        results = await pipeline.analyze(
            log_content=log_content,
            config=get_callback_config(show_output=False),
        )
        assert results["success"] is True
        # Should complete without RAG
        return results

    asyncio.run(run())


def test_no_yara_sigma():
    """Test pipeline with YARA/Sigma disabled."""
    log_content = "[Wed Dec 17 13:06:06 2025] [error] Authentication failed"

    async def run():
        pipeline = await create_pipeline(
            use_rag=False,
            yara_rules_path=None,  # Disable YARA
            sigma_rules_path=None,  # Disable Sigma
        )
        results = await pipeline.analyze(
            log_content=log_content,
            config=get_callback_config(show_output=False),
        )
        assert results["success"] is True
        return results

    asyncio.run(run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
