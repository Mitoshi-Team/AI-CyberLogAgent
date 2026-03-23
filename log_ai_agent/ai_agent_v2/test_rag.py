#!/usr/bin/env python3
"""Test script with detailed RAG logging."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Enable debug logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)

from log_ai_agent.ai_agent_v2 import create_pipeline
from log_ai_agent.ai_agent_v2.callbacks import get_callback_config


async def main():
    """Run test with RAG logging."""
    print("=" * 60)
    print("  AI Agent v2 - RAG Test with Detailed Logging")
    print("=" * 60)

    # Sample logs with clear attack patterns
    log_content = """
2026-03-21 10:15:45 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:46 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:47 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:48 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:16:00 ERROR SQL syntax error near 'SELECT * FROM users WHERE id=1 OR 1=1--'
"""

    print("\n1. Creating pipeline with RAG enabled...")
    pipeline = await create_pipeline(
        use_rag=True,  # Enable RAG
    )
    print("✓ Pipeline created\n")

    print("2. Analyzing logs...\n")
    print("-" * 60)

    results = await pipeline.analyze(
        log_content=log_content,
        config=get_callback_config(show_output=False),
    )

    print("-" * 60)
    print("\n3. Results:")

    if results.get("success"):
        stages = results.get("stages", {})

        # Agent 1
        if "agent1" in stages:
            agent1 = stages["agent1"]
            print(f"\n✓ Agent 1 Output ({agent1.get('events_found', 0)} events):")
            print(f"  {agent1.get('primary_analysis', '')[:200]}...")

        # RAG
        if "rag" in stages:
            rag = stages["rag"]
            print("\n✓ RAG Search:")
            print(f"  Techniques found: {rag.get('techniques_count', 0)}")
            print(f"  Technique IDs: {rag.get('technique_ids', [])}")
            print("\n  MITRE Context:")
            print(f"  {rag.get('mitre_context', '')[:300]}...")

        # Agent 2
        if "agent2" in stages:
            agent2 = stages["agent2"]
            print("\n✓ Agent 2 Output:")
            print(f"  Severity: {agent2.get('severity_level_id')}/4")
            print(f"  Threat: {agent2.get('threat_type_id')}/11")
            print(f"  MITRE Techniques: {agent2.get('mitre_techniques', [])}")

        print(f"\n✓ Total time: {results.get('total_time_sec', 0):.1f}s")
        print("\n" + "=" * 60)
        print("  TEST COMPLETE")
        print("=" * 60)

    else:
        print(f"✗ Analysis failed: {results.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
