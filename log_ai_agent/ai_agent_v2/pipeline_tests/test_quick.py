#!/usr/bin/env python3
"""Quick test script for AI Agent v2."""

import asyncio
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from log_ai_agent.ai_agent_v2 import create_pipeline
from log_ai_agent.ai_agent_v2.callbacks import get_callback_config


async def main():
    """Run quick test."""
    print("=" * 60)
    print("  AI Agent v2 - Quick Test")
    print("=" * 60)

    # Sample logs (Apache syslog format)
    log_content = """
[Wed Dec 17 13:06:06 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:07 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:08 2025] [error] [client 89.23.74.19] Multiple failed login attempts detected
[Wed Dec 17 13:06:15 2025] [error] [client 45.17.158.24] SQL injection attempt: OR 1=1 DROP TABLE users
"""

    print("\n1. Creating pipeline...")
    pipeline = await create_pipeline(
        use_rag=False,  # Disable RAG for quick test
    )
    print("[OK] Pipeline created")

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
                f"\n[OK] Agent 1: Found {stages['agent1'].get('events_found', 0)} events"
            )

        if "agent2" in stages:
            agent2 = stages["agent2"]
            print(
                f"[OK] Agent 2: severity={agent2.get('severity_level_id')}, threat={agent2.get('threat_type_id')}"
            )

        if "agent3" in stages:
            agent3 = stages["agent3"]
            print(
                f"[OK] Agent 3 (final): severity={agent3.get('severity_level_id')}, threat={agent3.get('threat_type_id')}"
            )
            print("\nReport preview:")
            print(agent3.get("final_report", "")[:300])

        print(f"\n[OK] Total time: {results.get('total_time_sec', 0):.1f}s")
        print("\n" + "=" * 60)
        print("  TEST PASSED")
        print("=" * 60)

    else:
        print(f"[X] Analysis failed: {results.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
