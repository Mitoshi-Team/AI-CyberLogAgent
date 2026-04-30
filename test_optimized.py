#!/usr/bin/env python3
"""Test script to verify optimized pipeline works."""

import asyncio
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our optimized components
try:
    from log_ai_agent.ai_agent_v2.pipeline.langgraph_pipeline import create_pipeline
    from log_ai_agent.ai_agent_v2.chains.prefilter import prefilter_logs
    print("✓ Successfully imported optimized pipeline components")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Simple test log with some security events
TEST_LOG = """
[Wed Dec 17 13:53:04 2025] [notice] caught SIGTERM, shutting down
[Wed Dec 17 13:53:06 2025] [error] [client 24.175.206.253] script not found or unable to stat: /var/www/html/admin/
[Wed Dec 17 13:53:13 2025] [error] jk2_init() Can't find child 6385 in scoreboard
[Wed Dec 17 13:53:20 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 13:53:24 2025] [error] ajp_send_request: Connection reset by peer or network problems
[Wed Dec 17 13:53:29 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:53:32 2025] [error] [client 251.149.178.187] File does not exist: /var/www/html/
[Wed Dec 17 13:53:40 2025] [error] [client 210.113.22.164] File does not exist: /var/www/html/api/
[Wed Dec 17 13:53:44 2025] [error] jk2_init() Can't find child 6454 in scoreboard
[Wed Dec 17 13:53:52 2025] [error] [client 216.165.71.161] Directory index forbidden by rule: /var/www/html/admin/
[Wed Dec 17 13:53:58 2025] [notice] prefork.c: Child process 6939 is entering scoreboard slot 1
[Wed Dec 17 13:54:01 2025] [error] [client 82.95.92.61] Directory index forbidden by rule: /var/www/html/images/
[Wed Dec 17 13:54:07 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 13:54:14 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:54:18 2025] [notice] jk2_init() Found child 6765 in scoreboard slot 8
[Wed Dec 17 13:54:21 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 13:54:23 2025] [notice] jk2_init() Found child 6765 in scoreboard slot 8
[Wed Dec 17 13:54:25 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 13:54:31 2025] [error] mod_jk child workerEnv in error state 8
[Wed Dec 17 13:54:35 2025] [notice] prefork.c: Child process 6202 is entering scoreboard slot 7
[Wed Dec 17 13:54:43 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 13:54:48 2025] [error] jk2_init() Can't find child 6202 in scoreboard
[Wed Dec 17 13:54:52 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:54:57 2025] [notice] jk2_init() Found child 6821 in scoreboard slot 10
[Wed Dec 17 13:55:02 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 13:55:04 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:55:12 2025] [error] [client 129.139.45.140] File does not exist: /var/www/html/admin/
[Wed Dec 17 13:55:17 2025] [error] jk2_init() Can't find child 6243 in scoreboard
[Wed Dec 17 13:55:19 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:55:22 2025] [notice] Server built: Dec 17 2025 13:55:22
[Wed Dec 17 13:55:26 2025] [error] [client 72.142.44.233] Directory index forbidden by rule: /usr/local/apache/htdocs/
[Wed Dec 17 13:55:28 2025] [notice] jk2_init() Found child 6912 in scoreboard slot 7
[Wed Dec 17 13:55:34 2025] [notice] Server built: Dec 17 2025 13:55:34
[Wed Dec 17 13:55:42 2025] [error] [client 214.36.24.39] Directory index forbidden by rule: /var/www/html/uploads/
[Wed Dec 17 13:55:44 2025] [error] [client 198.67.171.172] Directory index forbidden by rule: /var/www/html/uploads/
[Wed Dec 17 13:55:47 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 13:55:52 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:55:57 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 13:56:05 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:56:10 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 13:56:18 2025] [error] jk2_init() Can't find child 6949 in scoreboard
[Wed Dec 17 13:56:22 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:56:30 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:56:36 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 13:56:42 2025] [error] [client 122.201.60.132] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 13:56:47 2025] [error] [client 2.39.15.157] Directory index forbidden by rule: /usr/local/apache/htdocs/
[Wed Dec 17 13:56:50 2025] [error] mod_jk child workerEnv in error state 9
[Wed Dec 17 13:56:53 2025] [error] mod_jk child workerEnv in error state 10
[Wed Dec 17 13:56:57 2025] [error] mod_jk child workerEnv in critical error state 3
[Wed Dec 17 13:57:05 2025] [notice] prefork.c: Child process 6992 is entering scoreboard slot 4
[Wed Dec 17 13:57:09 2025] [error] [client 26.109.120.241] Directory index forbidden by rule: /var/www/html/admin/
[Wed Dec 17 13:57:12 2025] [error] Child 6029: Encountered too many errors accepting client connections
[Wed Dec 17 13:57:19 2025] [notice] prefork.c: Child process 6855 is entering scoreboard slot 8
[Wed Dec 17 13:57:21 2025] [error] mod_jk child init 1 -2
[Wed Dec 17 13:57:26 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:57:34 2025] [error] Child 6543: Encountered too many errors accepting client connections
[Wed Dec 17 13:57:36 2025] [notice] prefork.c: Child process 6940 is entering scoreboard slot 6
[Wed Dec 17 13:57:41 2025] [error] mod_jk child workerEnv in error state 2
[Wed Dec 17 13:57:43 2025] [notice] caught SIGTERM, shutting down
[Wed Dec 17 13:57:46 2025] [error] jk2_init() Can't find child 6687 in scoreboard
[Wed Dec 17 13:57:50 2025] [error] [client 128.160.178.164] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 13:57:52 2025] [error] Child 6476: Encountered too many errors accepting client connections
[Wed Dec 17 13:57:58 2025] [notice] jk2_init() Found child 6254 in scoreboard slot 2
[Wed Dec 17 13:58:06 2025] [error] [client 244.193.221.15] script not found or unable to stat: /var/www/html/api/
[Wed Dec 17 13:58:09 2025] [error] mod_jk child workerEnv in error state 7
[Wed Dec 17 13:58:13 2025] [notice] prefork.c: Child process 6414 is entering scoreboard slot 7
[Wed Dec 17 13:58:15 2025] [notice] prefork.c: Child process 6960 is entering scoreboard slot 9
[Wed Dec 17 13:58:29 2025] [error] Unable to establish connection to worker node
[Wed Dec 17 13:58:31 2025] [error] Backend connection pool exhausted
[Wed Dec 17 13:58:39 2025] [error] Unable to establish connection to worker node
[Wed Dec 17 13:58:47 2025] [error] Backend connection pool exhausted
[Wed Dec 17 13:58:53 2025] [notice] jk2_init() Found child 6328 in scoreboard slot 2
[Wed Dec 17 13:58:56 2025] [error] [client 19.27.199.60] Directory index forbidden by rule: /var/www/html/api/
[Wed Dec 17 13:58:59 2025] [notice] Server built: Dec 17 2025 13:58:59
"""

async def test_prefilter():
    """Test the prefilter function."""
    print("\n1. Testing prefilter function...")
    filtered_content, stats = prefilter_logs(TEST_LOG)
    print(f"   Original lines: {stats['original_lines']}")
    print(f"   Filtered lines: {stats['filtered_lines']}")
    print(f"   Kept lines: {stats['kept_lines']}")
    print(f"   Filter ratio: {stats['filter_ratio']:.1%}")
    print("   ✓ Prefilter test completed")

async def test_pipeline():
    """Test the full pipeline."""
    print("\n2. Testing full pipeline...")
    try:
        # Create pipeline with minimal config for testing
        pipeline = await create_pipeline(
            use_rag=False,  # Disable RAG for faster testing
            yara_rules_path=None,  # Disable YARA
            sigma_rules_path=None   # Disable Sigma
        )
        print("   ✓ Pipeline created")
        
        # Analyze the test log
        results = await pipeline.analyze(
            log_content=TEST_LOG,
            config=None
        )
        
        if results.get("success"):
            print("   ✓ Pipeline analysis successful")
            print(f"   Events found: {results.get('events_found', 0)}")
            print(f"   Processing time: {results.get('total_time_sec', 0):.2f}s")
            print(f"   Prefilter stats: {results.get('stages', {}).get('prefilter', {}).get('stats', {})}")
        else:
            print(f"   ✗ Pipeline analysis failed: {results.get('error')}")
            
    except Exception as e:
        print(f"   ✗ Pipeline test error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests."""
    print("=" * 50)
    print("Testing Optimized Pipeline")
    print("=" * 50)
    
    await test_prefilter()
    await test_pipeline()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())