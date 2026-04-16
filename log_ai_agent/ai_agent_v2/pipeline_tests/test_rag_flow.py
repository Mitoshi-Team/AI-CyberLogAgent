#!/usr/bin/env python3
"""Test showing full RAG flow with comparison.

This test demonstrates how Agent 1 output is compared with MITRE techniques.
"""

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
    """Run RAG flow test."""
    print("=" * 60)
    print("  AI Agent v2 - RAG Flow Test")
    print("=" * 60)

    # Sample logs (Apache syslog format)
    log_content = """
[Wed Dec 17 13:06:06 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:07 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:08 2025] [error] [client 89.23.74.19] Multiple failed login attempts detected
[Wed Dec 17 13:06:15 2025] [error] [client 45.17.158.24] SQL injection attempt: OR 1=1 DROP TABLE users
"""

    print("\n[INFO] Creating pipeline with RAG...")

    # Create pipeline with RAG enabled
    pipeline = await create_pipeline(
        use_rag=True,
    )

    print("[OK] Pipeline created\n")
    print("=" * 60)
    print("  RAG FLOW")
    print("=" * 60)

    # Step 1: Agent 1
    print("\n[1] Agent 1: Primary Analysis")
    print("-" * 60)
    print("Input: Raw log content")
    print("Output: Structured analysis in Russian")

    result = await pipeline.analyze(
        log_content=log_content,
        config=get_callback_config(show_output=False),
    )

    if result.get("success"):
        stages = result.get("stages", {})

        # Agent 1 output
        if "agent1" in stages:
            agent1 = stages["agent1"]
            print(f"\n[OK] Agent 1 found {agent1['events_found']} events:")
            print(f"\n{agent1['primary_analysis'][:300]}...")

        # RAG output
        print("\n\n[2] RAG: MITRE ATT&CK Search")
        print("-" * 60)

        if "rag" in stages:
            rag = stages["rag"]
            print("Input: Agent 1 output (used for vector search)")
            print(f"Search query: '{rag.get('search_query', 'N/A')[:100]}...'")
            print(f"\n[OK] Found {rag['techniques_count']} MITRE techniques:")

            for i, tech_id in enumerate(rag.get("technique_ids", [])[:5], 1):
                print(f"  {i}. {tech_id}")

            print("\nMITRE Context (sent to Agent 2):")
            print(f"{rag['mitre_context'][:400]}...")

        # Agent 2 output
        print("\n\n[3] Agent 2: Detailed AI report")
        print("-" * 60)

        if "agent2" in stages:
            agent2 = stages["agent2"]
            print("Input: Agent 1 output + MITRE context")
            print("\n[OK] Agent 2 Report:")
            print(f"  Severity: {agent2['severity_level_id']}/4")
            print(f"  Threat Type: {agent2['threat_type_id']}/11")
            print(f"  MITRE Techniques: {agent2['mitre_techniques']}")

        # Agent 3 output
        print("\n\n[4] Agent 3: Final summarization")
        print("-" * 60)

        if "agent3" in stages:
            agent3 = stages["agent3"]
            print("Input: Agent 2 + MITRE + YARA + Sigma")
            print("\n[OK] Agent 3 Final Report:")
            print(f"  Severity: {agent3['severity_level_id']}/4")
            print(f"  Threat Type: {agent3['threat_type_id']}/11")
            print(f"  MITRE Techniques: {agent3['mitre_techniques']}")
            print(f"  YARA Rules: {agent3.get('yara_rules', [])}")
            print(f"  Sigma Rules: {agent3.get('sigma_rules', [])}")

            print("\nReport preview:")
            print(f"{agent3['final_report'][:400]}...")

        print("\n" + "=" * 60)
        print(f"[OK] Total time: {result['total_time_sec']:.1f}s")
        print("=" * 60)

        print("\n[RAG FLOW SUMMARY]")
        print("  Agent 1 -> RAG (MITRE) -> Agent 2 ->|")
        print("  parse_logs -> YARA ----------------|-> Agent 3 -> Final Report")
        print("  parse_logs -> Sigma ---------------|")
        print("\n[OK] RAG comparison is working!")

    else:
        print(f"[X] Test failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
