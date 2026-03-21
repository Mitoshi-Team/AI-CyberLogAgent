#!/usr/bin/env python3
r"""
Quick test script for AI Agent v2 pipeline.

Usage:
    cd C:\Users\litsu\PycharmProjects\AI-CyberLogAgent
    .venv\Scripts\python.exe -m log_ai_agent.ai_agent_v2.test_quick
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path (parent of log_ai_agent)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from log_ai_agent.ai_agent_v2 import GigaChatClient, LogAnalysisPipeline


async def test_pipeline():
    """Test the complete log analysis pipeline."""
    
    print("=" * 60)
    print("  AI Agent v2 - Quick Test")
    print("=" * 60)
    
    # Sample log content for testing
    sample_log = """
2026-03-21 10:15:23 INFO Application started
2026-03-21 10:15:45 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:46 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:47 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:48 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:49 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:16:00 ERROR SQL syntax error near 'SELECT * FROM users WHERE id=1 OR 1=1--'
2026-03-21 10:16:01 CRITICAL Database connection pool exhausted
2026-03-21 10:16:15 WARNING Suspicious file access: /etc/passwd
2026-03-21 10:16:30 ERROR Unauthorized API request from 10.0.0.55
"""
    
    print("\n📝 Initializing GigaChat client...")
    client = GigaChatClient(
        temperature=0.1,
        max_tokens=4000,
        timeout=90,
        rate_limit_delay=0.5,
    )
    
    print("📝 Creating pipeline (without RAG for quick test)...")
    pipeline = LogAnalysisPipeline(
        gigachat_client=client,
        chroma_manager=None,  # Disable RAG for quick test
        use_rag=False,
    )
    
    print("\n🔍 Analyzing sample log...")
    print("-" * 60)
    
    try:
        result = await pipeline.analyze_log(sample_log, timeout_seconds=120)
        
        if result.success and result.final_result:
            print("\n✅ Analysis completed successfully!")
            print(f"\n⏱️  Total time: {result.total_processing_time_ms:.0f}ms")
            print(f"📊 Severity: {result.final_result.severity_level_id}/4")
            print(f"🎯 Threat type: {result.final_result.threat_type_id}/11")
            if result.final_result.mitre_techniques:
                print(f"📚 MITRE techniques: {', '.join(result.final_result.mitre_techniques)}")
            
            print("\n" + "=" * 60)
            print("  REPORT PREVIEW")
            print("=" * 60)
            # Show first 500 chars of report
            report_preview = result.final_result.report_text[:500]
            print(report_preview)
            if len(result.final_result.report_text) > 500:
                print("\n... (truncated)")
        else:
            print("\n❌ Analysis failed!")
            if result.final_result:
                print(f"Error: {result.final_result.error_message}")
            else:
                print("Error: No final result (pipeline failed early)")
            
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()
    
    print("\n" + "=" * 60)
    print("  Test completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_pipeline())
