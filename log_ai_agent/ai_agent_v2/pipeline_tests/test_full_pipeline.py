#!/usr/bin/env python3
"""Full pipeline test — RAG + YARA + Sigma all active.

Tests the complete LangGraph pipeline with all branches:
  Agent 1 → RAG (MITRE) → Agent 2 ┐
  YARA Scan ───────────────────────┤→ Agent 3 → Final Report
  Sigma Scan ──────────────────────┘
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


def _resolve_rules_path(subdir: str) -> str:
    """Resolve rules path relative to the ai_agent_v2 package."""
    base = Path(__file__).parent.parent
    return str((base / "rules" / subdir).resolve())


# Log with diverse attack patterns to trigger all branches (Apache syslog format)
_ATTACK_LOG = """
[Wed Dec 17 13:06:06 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:07 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:08 2025] [error] [client 89.23.74.19] Multiple failed login attempts detected
[Wed Dec 17 13:06:10 2025] [error] [client 89.23.74.19] Possible brute force attack from 89.23.74.19
[Wed Dec 17 13:06:15 2025] [error] [client 45.17.158.24] SQL injection attempt: OR 1=1 DROP TABLE users
[Wed Dec 17 13:06:20 2025] [error] [client 45.17.158.24] UNION ALL SELECT FROM credentials
[Wed Dec 17 13:06:25 2025] [error] [client 45.17.158.24] XSS attempt: <script>alert(1)</script>
"""


async def main():
    """Run full pipeline test with RAG + YARA + Sigma."""
    print("=" * 60)
    print("  Full Pipeline Test — RAG + YARA + Sigma")
    print("=" * 60)

    yara_path = _resolve_rules_path("yara")
    sigma_path = _resolve_rules_path("sigma")

    print("\n1. Creating pipeline (RAG + YARA + Sigma)...")
    pipeline = await create_pipeline(
        use_rag=True,
        yara_rules_path=yara_path,
        sigma_rules_path=sigma_path,
    )
    print("   Pipeline created")
    print(f"   RAG: enabled")
    print(
        f"   YARA: {pipeline._nodes.yara_engine.rules_count if pipeline._nodes.yara_engine else 0} rules"
    )
    print(
        f"   Sigma: {len(pipeline._nodes.sigma_engine._rules) if pipeline._nodes.sigma_engine else 0} rules"
    )

    print("\n2. Analyzing logs...")
    print("-" * 60)

    results = await pipeline.analyze(
        log_content=_ATTACK_LOG,
        config=get_callback_config(show_output=False),
    )

    print("-" * 60)
    print("\n3. Results:")

    if not results.get("success"):
        print(f"   Analysis failed: {results.get('error', 'Unknown error')}")
        sys.exit(1)

    stages = results.get("stages", {})

    # --- Agent 1 ---
    if "agent1" in stages:
        agent1 = stages["agent1"]
        events = agent1.get("events_found", 0)
        print(f"\n   [OK] Agent 1 - {events} events found")

    # --- RAG ---
    if "rag" in stages:
        rag = stages["rag"]
        tech_count = rag.get("techniques_count", 0)
        tech_ids = rag.get("technique_ids", [])
        print(f"   [OK] RAG - {tech_count} MITRE techniques")
        if tech_ids:
            print(f"       IDs: {tech_ids}")

    # --- Agent 2 ---
    if "agent2" in stages:
        agent2 = stages["agent2"]
        print(
            f"   [OK] Agent 2 - severity={agent2.get('severity_level_id')}/4, "
            f"threat={agent2.get('threat_type_id')}/11"
        )

    # --- YARA ---
    if "yara" in stages:
        yara = stages["yara"]
        matches = yara.get("matches", [])
        print(f"   [OK] YARA - {len(matches)} rules matched")
        for m in matches:
            print(f"       - {m.get('rule', 'Unknown')} ({m.get('severity', '')})")

    # --- Sigma ---
    if "sigma" in stages:
        sigma = stages["sigma"]
        matches = sigma.get("matches", [])
        print(f"   [OK] Sigma - {len(matches)} rules matched")
        for m in matches:
            print(f"       - {m.get('title', 'Unknown')} ({m.get('severity', '')})")

    # --- Agent 3 ---
    if "agent3" in stages:
        agent3 = stages["agent3"]
        print(
            f"\n   [OK] Agent 3 (final) - severity={agent3.get('severity_level_id')}/4, "
            f"threat={agent3.get('threat_type_id')}/11"
        )
        print(f"       MITRE techniques: {agent3.get('mitre_techniques', [])}")
        print(f"       YARA rules: {agent3.get('yara_rules', [])}")
        print(f"       Sigma rules: {agent3.get('sigma_rules', [])}")
        print(f"\n   Report preview:")
        print(f"   {agent3.get('final_report', '')[:400]}...")

    print(f"\n   Total time: {results.get('total_time_sec', 0):.1f}s")
    print("\n" + "=" * 60)
    print("  TEST PASSED — Full pipeline (RAG + YARA + Sigma)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
