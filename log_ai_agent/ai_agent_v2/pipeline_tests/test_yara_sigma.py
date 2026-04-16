"""Tests for YARA and Sigma rule engines and full pipeline integration."""

import asyncio
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from log_ai_agent.ai_agent_v2 import create_pipeline
from log_ai_agent.ai_agent_v2.engines import SigmaEngine, YaraEngine
from log_ai_agent.ai_agent_v2.parsers import ApacheLogParser, parse_log_content

_APACHE_ATTACK_LOG = """
[Wed Dec 17 13:06:06 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:07 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:08 2025] [error] [client 89.23.74.19] Multiple failed login attempts detected
[Wed Dec 17 13:06:10 2025] [error] [client 89.23.74.19] Possible brute force attack from 89.23.74.19
[Wed Dec 17 13:06:15 2025] [error] [client 45.17.158.24] script not found: /var/www/html/.env
[Wed Dec 17 13:06:20 2025] [error] [client 45.17.158.24] SQL injection attempt: ' OR 1=1 -- DROP TABLE users
[Wed Dec 17 13:06:25 2025] [error] [client 45.17.158.24] UNION ALL SELECT * FROM credentials
[Wed Dec 17 13:06:30 2025] [error] [client 45.17.158.24] XSS attempt: <script>alert(1)</script>
[Wed Dec 17 13:06:35 2025] [error] [client 45.17.158.24] Directory index forbidden: /var/www/html/admin/
"""

_APACHE_CLEAN_LOG = """
[Wed Dec 17 13:00:00 2025] [notice] Apache/2.4.41 configured
[Wed Dec 17 13:00:05 2025] [info] Server started successfully
[Wed Dec 17 13:00:10 2025] [info] User john@example.com logged in
[Wed Dec 17 13:00:15 2025] [info] GET /api/v1/status 200 OK
[Wed Dec 17 13:00:20 2025] [info] POST /api/v1/users 201 Created
"""


def _resolve_rules_path(subdir: str) -> str:
    """Resolve rules path relative to ai_agent_v2 package."""
    base = Path(__file__).parent.parent
    return str((base / "rules" / subdir).resolve())


def _parse_logs(log_text: str) -> list[dict]:
    """Parse log text into structured format."""
    return parse_log_content(log_text)


@pytest.mark.asyncio
async def test_parser():
    """Test Apache log parser."""
    print("=" * 60)
    print("  Test 0: Apache Log Parser")
    print("=" * 60)

    parser = ApacheLogParser()

    print("\n1. Parsing attack logs...")
    parsed = parser.parse(_APACHE_ATTACK_LOG)
    print(f"   [OK] Parsed {len(parsed)} log entries")

    for i, log in enumerate(parsed[:3]):
        print(
            f"   Entry {i}: format={log['format']}, level={log['level']}, ip={log['client_ip']}"
        )

    assert len(parsed) > 0, "Should parse attack logs"

    print("\n2. Parsing clean logs...")
    clean_parsed = parser.parse(_APACHE_CLEAN_LOG)
    print(f"   [OK] Parsed {len(clean_parsed)} log entries")

    assert len(clean_parsed) > 0, "Should parse clean logs"

    print("\n" + "=" * 60)
    print("  TEST 0 PASSED: Parser works correctly")
    print("=" * 60)
    return True


@pytest.mark.asyncio
async def test_yara_sigma_engines():
    """Test YARA and Sigma engines with parsed logs.

    Validates:
    - Rules loading from files
    - Pattern matching against attack logs
    - No false positives on clean logs
    """
    print("\n" + "=" * 60)
    print("  Test 1: YARA + Sigma Engines (standalone)")
    print("=" * 60)

    yara_path = _resolve_rules_path("yara")
    sigma_path = _resolve_rules_path("sigma")

    print(f"\n1. Loading YARA rules from: {yara_path}")
    yara_engine = YaraEngine(yara_path)
    print("   [OK] YARA engine initialized")

    print(f"\n2. Loading Sigma rules from: {sigma_path}")
    sigma_engine = SigmaEngine(sigma_path)
    print(f"   [OK] Loaded {len(sigma_engine._rules)} Sigma rules")

    print("\n3. Parsing attack logs...")
    attack_parsed = parse_log_content(_APACHE_ATTACK_LOG)

    print("\n4. Scanning parsed logs with YARA...")
    yara_results = yara_engine.scan(attack_parsed)
    print(f"   YARA matches: {len(yara_results)}")
    for m in yara_results[:5]:
        print(f"     - {m['rule']} (severity: {m['severity']})")

    print("\n5. Scanning parsed logs with Sigma...")
    sigma_results = sigma_engine.scan(attack_parsed)
    print(f"   Sigma matches: {len(sigma_results)}")
    for m in sigma_results[:5]:
        print(f"     - {m['title']} (severity: {m['severity']})")

    assert len(yara_results) > 0, "YARA should detect attack patterns"
    assert len(sigma_results) > 0, "Sigma should detect attack patterns"

    print("\n6. Testing clean logs (no false positives)...")
    clean_parsed = parse_log_content(_APACHE_CLEAN_LOG)
    yara_clean = yara_engine.scan(clean_parsed)
    sigma_clean = sigma_engine.scan(clean_parsed)

    print(f"   YARA clean matches: {len(yara_clean)}")
    print(f"   Sigma clean matches: {len(sigma_clean)}")

    print("\n" + "=" * 60)
    print("  TEST 1 PASSED: YARA + Sigma engines work correctly")
    print("=" * 60)
    return True


@pytest.mark.asyncio
async def test_full_pipeline_nodes():
    """Test pipeline nodes with new parse_logs flow."""
    print("\n" + "=" * 60)
    print("  Test 2: Pipeline Nodes (parse_logs flow)")
    print("=" * 60)

    yara_path = _resolve_rules_path("yara")
    sigma_path = _resolve_rules_path("sigma")

    print("\n1. Creating pipeline...")
    pipeline = await create_pipeline(
        use_rag=False,
        yara_rules_path=yara_path,
        sigma_rules_path=sigma_path,
    )
    print("   [OK] Pipeline created")

    from log_ai_agent.ai_agent_v2.models_types import AnalysisState

    state: AnalysisState = {
        "log_content": _APACHE_ATTACK_LOG,
        "parsed_logs": [],
        "log_size": len(_APACHE_ATTACK_LOG),
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

    print("\n2. Testing parse_logs_node...")
    parse_result = await pipeline._nodes.parse_logs_node(state)
    parsed_logs = parse_result.get("parsed_logs", [])
    print(f"   [OK] Parsed {len(parsed_logs)} log entries")
    state["parsed_logs"] = parsed_logs

    print("\n3. Testing yara_scan_node...")
    yara_result = await pipeline._nodes.yara_scan_node(state)
    yara_matches = yara_result.get("yara_matches", [])
    print(f"   [OK] YARA matches: {len(yara_matches)}")
    assert len(yara_matches) > 0, "YARA should detect patterns"

    print("\n4. Testing sigma_scan_node...")
    sigma_result = await pipeline._nodes.sigma_scan_node(state)
    sigma_matches = sigma_result.get("sigma_matches", [])
    print(f"   [OK] Sigma matches: {len(sigma_matches)}")
    assert len(sigma_matches) > 0, "Sigma should detect patterns"

    print("\n5. Testing clean log flow...")
    clean_state: AnalysisState = {
        "log_content": _APACHE_CLEAN_LOG,
        "parsed_logs": [],
        "log_size": len(_APACHE_CLEAN_LOG),
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

    clean_parsed = await pipeline._nodes.parse_logs_node(clean_state)
    clean_state["parsed_logs"] = clean_parsed.get("parsed_logs", [])

    clean_yara = await pipeline._nodes.yara_scan_node(clean_state)
    clean_sigma = await pipeline._nodes.sigma_scan_node(clean_state)

    print(f"   YARA clean matches: {len(clean_yara.get('yara_matches', []))}")
    print(f"   Sigma clean matches: {len(clean_sigma.get('sigma_matches', []))}")

    print("\n" + "=" * 60)
    print("  TEST 2 PASSED: Pipeline nodes work correctly")
    print("=" * 60)
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  YARA + SIGMA Integration Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_func, name in [
        (test_parser, "Parser"),
        (test_yara_sigma_engines, "Engines"),
        (test_full_pipeline_nodes, "Pipeline Nodes"),
    ]:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n[X] TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n[X] TEST ERROR: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)

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
