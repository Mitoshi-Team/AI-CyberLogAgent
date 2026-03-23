#!/usr/bin/env python3
r"""Basic example of AI Agent v2 usage.

This example shows how to:
1. Create a pipeline
2. Analyze log content
3. Get results

Usage:
    cd C:\Users\litsu\PycharmProjects\AI-CyberLogAgent
    uv run -m log_ai_agent.ai_agent_v2.examples.basic
"""

import asyncio
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from log_ai_agent.ai_agent_v2.callbacks import get_callback_config
from log_ai_agent.ai_agent_v2.pipeline.full_pipeline import create_pipeline


async def main():
    """Run basic analysis example."""
    print("=" * 60)
    print("  AI Agent v2 - Basic Example")
    print("=" * 60)

    # Sample log content
    log_content = """
2026-03-21 10:15:45 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:46 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:47 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:16:00 ERROR SQL syntax error near 'SELECT * FROM users WHERE id=1 OR 1=1--'
2026-03-21 10:16:30 ERROR Unauthorized API request from 10.0.0.55
"""

    print("\n1. Creating pipeline...")
    pipeline = await create_pipeline(
        use_rag=True,  # Set to False to disable RAG
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

        # Agent 1
        if "agent1" in stages:
            print(f"\nAgent 1: Found {stages['agent1'].get('events_found', 0)} events")

        # RAG
        if "rag" in stages:
            rag = stages["rag"]
            if rag.get("success"):
                print(f"RAG: Found {rag.get('techniques_count', 0)} MITRE techniques")
            else:
                print("RAG: Disabled or unavailable")

        # Agent 2
        if "agent2" in stages:
            agent2 = stages["agent2"]
            print("\nAgent 2:")
            print(f"  Severity: {agent2.get('severity_level_id')}/4")
            print(f"  Threat: {agent2.get('threat_type_id')}/11")
            print(f"  MITRE: {agent2.get('mitre_techniques', [])}")

            print("\n" + "-" * 60)
            print("Final Report:")
            print("-" * 60)
            print(agent2.get("final_report", "")[:500])  # First 500 chars

        print("\n" + "=" * 60)
        print(f"Total time: {results.get('total_time_sec', 0):.1f}s")
        print("=" * 60)

    else:
        print(f"✗ Analysis failed: {results.get('error', 'Unknown error')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
