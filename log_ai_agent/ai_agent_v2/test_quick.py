#!/usr/bin/env python3
"""Quick test script for AI Agent v2."""

import asyncio
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from log_ai_agent.ai_agent_v2 import create_pipeline
from log_ai_agent.ai_agent_v2.callbacks import get_callback_config


async def main():
    """Run quick test."""
    print("=" * 60)
    print("  AI Agent v2 - Quick Test")
    print("=" * 60)

    # Sample logs
    log_content = """
2026-03-21 10:15:45 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:46 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:47 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:16:00 ERROR SQL syntax error near 'SELECT * FROM users WHERE id=1 OR 1=1--'
2026-03-21 10:16:30 ERROR Unauthorized API request from 10.0.0.55
"""

    print("\n1. Creating pipeline...")
    pipeline = await create_pipeline(
        use_rag=False,  # Disable RAG for quick test
    )
    print("✓ Pipeline created")

    print("\n2. Analyzing logs...")
    results = await pipeline.analyze(
        log_content=log_content,
        config=get_callback_config(show_output=False),
    )

    print("\n3. Results:")
    print("-" * 60)

    if results.get("success"):
        stages = results.get("stages", {})

        if "agent1" in stages:
            print(
                f"\n✓ Agent 1: Found {stages['agent1'].get('events_found', 0)} events"
            )

        if "agent2" in stages:
            agent2 = stages["agent2"]
            print(
                f"✓ Agent 2: severity={agent2.get('severity_level_id')}, threat={agent2.get('threat_type_id')}"
            )
            print("\nReport preview:")
            print(agent2.get("final_report", "")[:300])

        print(f"\n✓ Total time: {results.get('total_time_sec', 0):.1f}s")
        print("\n" + "=" * 60)
        print("  TEST PASSED")
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
