#!/usr/bin/env python3
"""Test script with detailed RAG logging."""

import asyncio
import logging
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

    # Sample logs with clear attack patterns (Apache syslog format)
    log_content = """
[Wed Dec 17 13:06:06 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:07 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:08 2025] [error] [client 89.23.74.19] Multiple failed login attempts detected
[Wed Dec 17 13:06:10 2025] [error] [client 89.23.74.19] Possible brute force attack from 89.23.74.19
[Wed Dec 17 13:06:15 2025] [error] [client 45.17.158.24] SQL injection attempt: OR 1=1 DROP TABLE users
"""

    print("\n1. Creating pipeline with RAG enabled...")
    pipeline = await create_pipeline(
        use_rag=True,  # Enable RAG
    )
    print("[OK] Pipeline created\n")

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
            print(f"\n[OK] Agent 1 Output ({agent1.get('events_found', 0)} events):")
            print(f"  {agent1.get('primary_analysis', '')[:200]}...")

        # RAG
        if "rag" in stages:
            rag = stages["rag"]
            print("\n[OK] RAG Search:")
            print(f"  Techniques found: {rag.get('techniques_count', 0)}")
            print(f"  Technique IDs: {rag.get('technique_ids', [])}")
            print("\n  MITRE Context:")
            print(f"  {rag.get('mitre_context', '')[:300]}...")

        # Agent 2
        if "agent2" in stages:
            agent2 = stages["agent2"]
            print("\n[OK] Agent 2 Output (detailed):")
            print(f"  Severity: {agent2.get('severity_level_id')}/4")
            print(f"  Threat: {agent2.get('threat_type_id')}/11")
            print(f"  MITRE Techniques: {agent2.get('mitre_techniques', [])}")

        # Agent 3 (final)
        if "agent3" in stages:
            agent3 = stages["agent3"]
            print("\n[OK] Agent 3 Output (final summarization):")
            print(f"  Severity: {agent3.get('severity_level_id')}/4")
            print(f"  Threat: {agent3.get('threat_type_id')}/11")
            print(f"  MITRE Techniques: {agent3.get('mitre_techniques', [])}")
            print(f"  YARA Rules: {agent3.get('yara_rules', [])}")
            print(f"  Sigma Rules: {agent3.get('sigma_rules', [])}")

        print(f"\n[OK] Total time: {results.get('total_time_sec', 0):.1f}s")
        print("\n" + "=" * 60)
        print("  TEST COMPLETE")
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
