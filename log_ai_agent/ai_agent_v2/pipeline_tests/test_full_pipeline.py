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
[Wed Dec 17 13:54:18 2025] [error] [client 142.168.104.226] Directory index forbidden by rule: /var/www/html/admin/
[Wed Dec 17 13:54:21 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
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
[Wed Dec 17 13:55:19 2025] [notice] Server built: Dec 17 2025 13:55:19
[Wed Dec 17 13:55:22 2025] [error] [client 72.142.44.233] Directory index forbidden by rule: /usr/local/apache/htdocs/
[Wed Dec 17 13:55:26 2025] [notice] jk2_init() Found child 6912 in scoreboard slot 7
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
[Wed Dec 17 13:56:57 2025] [error] mod_jk child init 3 -2
[Wed Dec 17 13:57:05 2025] [notice] prefork.c: Child process 6992 is entering scoreboard slot 4
[Wed Dec 17 13:57:09 2025] [error] [client 26.109.120.241] Directory index forbidden by rule: /var/www/html/admin/
[Wed Dec 17 13:57:12 2025] [error] Child 6029: Encountered too many errors accepting client connections
[Wed Dec 17 13:57:19 2025] [notice] prefork.c: Child process 6855 is entering scoreboard slot 8
[Wed Dec 17 13:57:21 2025] [error] mod_jk child init 1 -2
[Wed Dec 17 13:57:26 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 13:57:34 2025] [error] Child 6543: Encountered too many errors accepting client connections
[Wed Dec 17 13:57:36 2025] [notice] prefork.c: Child process 6940 is entering scoreboard slot 6
[Wed Dec 17 13:57:41 2025] [error] mod_jk child init 2 -2
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
[Wed Dec 17 13:59:05 2025] [error] jk2_init() Can't find child 6303 in scoreboard
[Wed Dec 17 13:59:11 2025] [notice] prefork.c: Child process 6672 is entering scoreboard slot 1
[Wed Dec 17 13:59:14 2025] [error] mod_jk child init 3 -2
[Wed Dec 17 13:59:21 2025] [notice] jk2_init() Found child 6275 in scoreboard slot 4
[Wed Dec 17 13:59:24 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 13:59:29 2025] [error] mod_jk child init 3 -2
[Wed Dec 17 13:59:37 2025] [notice] jk2_init() Found child 6761 in scoreboard slot 8
[Wed Dec 17 13:59:42 2025] [notice] jk2_init() Found child 6891 in scoreboard slot 8
[Wed Dec 17 13:59:49 2025] [notice] Server built: Dec 17 2025 13:59:49
[Wed Dec 17 13:59:57 2025] [notice] Server built: Dec 17 2025 13:59:57
[Wed Dec 17 14:00:04 2025] [notice] jk2_init() Found child 6071 in scoreboard slot 1
[Wed Dec 17 14:00:11 2025] [notice] jk2_init() Found child 6579 in scoreboard slot 3
[Wed Dec 17 14:00:16 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:00:23 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:00:30 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 14:00:38 2025] [error] mod_jk child init 1 -2
[Wed Dec 17 14:00:43 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:00:50 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:00:58 2025] [error] Permission denied: user 'user' cannot access /etc/passwd
[Wed Dec 17 14:01:06 2025] [error] Security violation: unauthorized access attempt to /etc/passwd
[Wed Dec 17 14:01:11 2025] [error] Security violation: unauthorized access attempt to /admin
[Wed Dec 17 14:01:15 2025] [error] Permission denied: user 'root' cannot access /admin
[Wed Dec 17 14:01:22 2025] [error] [client 162.101.68.151] Directory index forbidden by rule: /var/www/html/images/
[Wed Dec 17 14:01:24 2025] [notice] jk2_init() Found child 6478 in scoreboard slot 7
[Wed Dec 17 14:01:34 2025] [error] Permission denied: user 'root' cannot access /var/log
[Wed Dec 17 14:01:40 2025] [error] Access forbidden for 119.176.218.84: insufficient privileges
[Wed Dec 17 14:01:44 2025] [error] Security violation: unauthorized access attempt to /var/log
[Wed Dec 17 14:01:52 2025] [error] Access forbidden for 82.137.90.70: insufficient privileges
[Wed Dec 17 14:01:59 2025] [error] Access forbidden for 219.99.51.85: insufficient privileges
[Wed Dec 17 14:02:02 2025] [error] Permission denied: user 'root' cannot access /etc/passwd
[Wed Dec 17 14:02:09 2025] [error] Access forbidden for 193.127.125.107: insufficient privileges
[Wed Dec 17 14:02:12 2025] [error] Permission denied: user 'admin' cannot access /admin
[Wed Dec 17 14:02:17 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:02:30 2025] [error] Multiple failed login attempts detected from 236.34.60.253
[Wed Dec 17 14:02:37 2025] [error] Possible brute force attack from 19.177.83.128
[Wed Dec 17 14:02:42 2025] [error] Multiple failed login attempts detected from 90.245.109.113
[Wed Dec 17 14:02:49 2025] [error] Authentication failed for user 'user' from 226.167.155.210
[Wed Dec 17 14:02:53 2025] [error] Multiple failed login attempts detected from 48.111.223.5
[Wed Dec 17 14:03:00 2025] [error] Authentication failed for user 'admin' from 204.74.172.188
[Wed Dec 17 14:03:06 2025] [error] Authentication failed for user 'root' from 152.86.187.220
[Wed Dec 17 14:03:10 2025] [error] Multiple failed login attempts detected from 192.133.106.211
[Wed Dec 17 14:03:18 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:03:22 2025] [error] jk2_init() Can't find child 6900 in scoreboard
[Wed Dec 17 14:03:35 2025] [error] Authentication failed for user 'user' from 7.138.234.36
[Wed Dec 17 14:03:40 2025] [error] Possible brute force attack from 69.222.60.173
[Wed Dec 17 14:03:44 2025] [error] Multiple failed login attempts detected from 2.92.32.200
[Wed Dec 17 14:03:47 2025] [error] Authentication failed for user 'root' from 122.255.40.122
[Wed Dec 17 14:03:51 2025] [error] Possible brute force attack from 112.196.6.16
[Wed Dec 17 14:03:58 2025] [error] Authentication failed for user 'admin' from 235.33.219.117
[Wed Dec 17 14:04:04 2025] [error] Possible brute force attack from 52.135.202.153
[Wed Dec 17 14:04:09 2025] [error] [client 117.64.222.252] script not found or unable to stat: /var/www/html/
[Wed Dec 17 14:04:23 2025] [error] Multiple failed login attempts detected from 63.25.230.225
[Wed Dec 17 14:04:26 2025] [error] Possible brute force attack from 24.137.162.128
[Wed Dec 17 14:04:34 2025] [error] Multiple failed login attempts detected from 127.138.208.105
[Wed Dec 17 14:04:39 2025] [error] Authentication failed for user 'root' from 193.154.27.224
[Wed Dec 17 14:04:45 2025] [error] Multiple failed login attempts detected from 76.18.14.163
[Wed Dec 17 14:04:50 2025] [error] Authentication failed for user 'root' from 5.87.147.108
[Wed Dec 17 14:04:57 2025] [error] Possible brute force attack from 46.113.142.24
[Wed Dec 17 14:05:01 2025] [error] Multiple failed login attempts detected from 123.86.226.11
[Wed Dec 17 14:05:09 2025] [notice] jk2_init() Found child 6869 in scoreboard slot 9
[Wed Dec 17 14:05:18 2025] [error] Security violation: unauthorized access attempt to /etc/passwd
[Wed Dec 17 14:05:22 2025] [error] Security violation: unauthorized access attempt to /etc/passwd
[Wed Dec 17 14:05:30 2025] [error] Permission denied: user 'user' cannot access /var/log
[Wed Dec 17 14:05:36 2025] [error] Security violation: unauthorized access attempt to /admin
[Wed Dec 17 14:05:42 2025] [error] Security violation: unauthorized access attempt to /etc/passwd
[Wed Dec 17 14:05:48 2025] [error] ajp_send_request: Connection reset by peer or network problems
[Wed Dec 17 14:05:50 2025] [error] [client 128.15.104.16] Directory index forbidden by rule: /var/www/html/admin/
[Wed Dec 17 14:05:58 2025] [notice] jk2_init() Found child 6440 in scoreboard slot 4
[Wed Dec 17 14:06:05 2025] [error] jk2_init() Can't find child 6227 in scoreboard
[Wed Dec 17 14:06:12 2025] [error] All workers in error state, service degraded
[Wed Dec 17 14:06:15 2025] [error] mod_jk child workerEnv in critical error state 8
[Wed Dec 17 14:06:23 2025] [error] All workers in error state, service degraded
[Wed Dec 17 14:06:25 2025] [error] Worker process 6821 failed to initialize
[Wed Dec 17 14:06:32 2025] [notice] Server built: Dec 17 2025 14:06:32
[Wed Dec 17 14:06:39 2025] [notice] SIGHUP received. Attempting to restart
[Wed Dec 17 14:06:43 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 14:06:46 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:06:48 2025] [error] jk2_init() Can't find child 6833 in scoreboard
[Wed Dec 17 14:06:55 2025] [error] mod_jk child workerEnv in error state 7
[Wed Dec 17 14:07:00 2025] [notice] Server built: Dec 17 2025 14:07:00
[Wed Dec 17 14:07:06 2025] [error] [client 179.233.170.10] Directory index forbidden by rule: /var/www/html/admin/
[Wed Dec 17 14:07:11 2025] [notice] prefork.c: Child process 6033 is entering scoreboard slot 8
[Wed Dec 17 14:07:15 2025] [error] Permission denied: user 'guest' cannot access /config
[Wed Dec 17 14:07:20 2025] [error] Permission denied: user 'root' cannot access /var/log
[Wed Dec 17 14:07:26 2025] [error] Access forbidden for 45.67.90.177: insufficient privileges
[Wed Dec 17 14:07:31 2025] [error] Permission denied: user 'user' cannot access /etc/passwd
[Wed Dec 17 14:07:36 2025] [error] Permission denied: user 'guest' cannot access /var/log
[Wed Dec 17 14:07:40 2025] [error] Permission denied: user 'root' cannot access /config
[Wed Dec 17 14:07:43 2025] [error] Permission denied: user 'user' cannot access /admin
[Wed Dec 17 14:07:49 2025] [error] Access forbidden for 56.5.193.79: insufficient privileges
[Wed Dec 17 14:07:54 2025] [notice] jk2_init() Found child 6185 in scoreboard slot 10
[Wed Dec 17 14:08:02 2025] [error] [client 54.117.185.107] File does not exist: /usr/local/apache/htdocs/
[Wed Dec 17 14:08:09 2025] [notice] Server built: Dec 17 2025 14:08:09
[Wed Dec 17 14:08:15 2025] [notice] jk2_init() Found child 6557 in scoreboard slot 5
[Wed Dec 17 14:08:17 2025] [error] [client 150.93.161.217] Directory index forbidden by rule: /var/www/html/uploads/
[Wed Dec 17 14:08:20 2025] [error] [client 54.34.253.128] File does not exist: /var/www/html/api/
[Wed Dec 17 14:08:28 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:08:32 2025] [notice] Server built: Dec 17 2025 14:08:32
[Wed Dec 17 14:08:40 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:08:46 2025] [notice] jk2_init() Found child 6890 in scoreboard slot 4
[Wed Dec 17 14:08:50 2025] [error] mod_jk child workerEnv in error state 2
[Wed Dec 17 14:09:01 2025] [error] Authentication failed for user 'root' from 33.20.151.74
[Wed Dec 17 14:09:06 2025] [error] Authentication failed for user 'root' from 181.255.71.36
[Wed Dec 17 14:09:09 2025] [error] Possible brute force attack from 199.62.155.13
[Wed Dec 17 14:09:15 2025] [error] Possible brute force attack from 235.83.117.57
[Wed Dec 17 14:09:20 2025] [error] Multiple failed login attempts detected from 217.55.203.232
[Wed Dec 17 14:09:27 2025] [error] Possible brute force attack from 196.16.203.195
[Wed Dec 17 14:09:30 2025] [error] Possible brute force attack from 113.179.177.154
[Wed Dec 17 14:09:37 2025] [error] Possible brute force attack from 63.202.109.148
[Wed Dec 17 14:09:44 2025] [error] ajp_send_request: Connection reset by peer or network problems
[Wed Dec 17 14:09:48 2025] [error] mod_jk child workerEnv in error state 3
[Wed Dec 17 14:09:53 2025] [notice] Server built: Dec 17 2025 14:09:53
[Wed Dec 17 14:10:01 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:10:09 2025] [error] jk2_init() Can't find child 6198 in scoreboard
[Wed Dec 17 14:10:16 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:10:20 2025] [notice] Server built: Dec 17 2025 14:10:20
[Wed Dec 17 14:10:25 2025] [notice] jk2_init() Found child 6731 in scoreboard slot 6
[Wed Dec 17 14:10:32 2025] [error] [client 152.141.53.76] Directory index forbidden by rule: /var/www/html/admin/
[Wed Dec 17 14:10:38 2025] [error] [client 119.231.109.26] Directory index forbidden by rule: /usr/local/apache/htdocs/
[Wed Dec 17 14:10:43 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:10:51 2025] [error] [client 140.222.69.92] File does not exist: /var/www/html/admin/
[Wed Dec 17 14:10:58 2025] [error] [client 153.218.214.254] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 14:11:04 2025] [notice] jk2_init() Found child 6174 in scoreboard slot 2
[Wed Dec 17 14:11:12 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:11:18 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 14:11:24 2025] [notice] SIGHUP received. Attempting to restart
[Wed Dec 17 14:11:30 2025] [error] [client 177.218.4.22] Directory index forbidden by rule: /var/www/html/images/
[Wed Dec 17 14:11:36 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:11:44 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:11:51 2025] [notice] jk2_init() Found child 6161 in scoreboard slot 8
[Wed Dec 17 14:11:58 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:12:06 2025] [error] mod_jk child workerEnv in critical error state 7
[Wed Dec 17 14:12:14 2025] [error] Worker process 6713 failed to initialize
[Wed Dec 17 14:12:21 2025] [error] All workers in error state, service degraded
[Wed Dec 17 14:12:25 2025] [error] mod_jk child workerEnv in critical error state 10
[Wed Dec 17 14:12:32 2025] [error] Worker process 6647 failed to initialize
[Wed Dec 17 14:12:37 2025] [error] Worker process 6905 failed to initialize
[Wed Dec 17 14:12:40 2025] [error] All workers in error state, service degraded
[Wed Dec 17 14:12:42 2025] [notice] Server built: Dec 17 2025 14:12:42
[Wed Dec 17 14:12:47 2025] [notice] jk2_init() Found child 6334 in scoreboard slot 2
[Wed Dec 17 14:12:51 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:12:56 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 14:12:58 2025] [notice] jk2_init() Found child 6587 in scoreboard slot 1
[Wed Dec 17 14:13:03 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:13:06 2025] [notice] Server built: Dec 17 2025 14:13:06
[Wed Dec 17 14:13:09 2025] [notice] jk2_init() Found child 6298 in scoreboard slot 8
[Wed Dec 17 14:13:16 2025] [error] [client 197.229.63.58] File does not exist: /usr/local/apache/htdocs/
[Wed Dec 17 14:13:19 2025] [error] [client 121.169.176.126] script not found or unable to stat: /var/www/html/images/
[Wed Dec 17 14:13:25 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:13:28 2025] [error] [client 54.198.92.192] script not found or unable to stat: /var/www/html/
[Wed Dec 17 14:13:33 2025] [error] jk2_init() Can't find child 6765 in scoreboard
[Wed Dec 17 14:13:41 2025] [notice] Server built: Dec 17 2025 14:13:41
[Wed Dec 17 14:13:49 2025] [error] [client 151.223.14.98] script not found or unable to stat: /var/www/html/images/
[Wed Dec 17 14:13:56 2025] [error] jk2_init() Can't find child 6735 in scoreboard
[Wed Dec 17 14:14:01 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:14:05 2025] [error] mod_jk child workerEnv in error state 7
[Wed Dec 17 14:14:11 2025] [notice] jk2_init() Found child 6322 in scoreboard slot 6
[Wed Dec 17 14:14:19 2025] [error] [client 134.23.217.255] Directory index forbidden by rule: /var/www/html/images/
[Wed Dec 17 14:14:23 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:14:30 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:14:35 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 14:14:43 2025] [error] [client 34.181.235.134] File does not exist: /var/www/html/images/
[Wed Dec 17 14:14:46 2025] [error] [client 247.67.240.137] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 14:14:50 2025] [error] [client 207.95.14.9] Directory index forbidden by rule: /var/www/html/images/
[Wed Dec 17 14:14:56 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:14:59 2025] [error] [client 98.160.66.75] File does not exist: /var/www/html/images/
[Wed Dec 17 14:15:01 2025] [notice] jk2_init() Found child 6272 in scoreboard slot 5
[Wed Dec 17 14:15:06 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:15:08 2025] [error] jk2_init() Can't find child 6525 in scoreboard
[Wed Dec 17 14:15:15 2025] [error] [client 72.208.188.187] Directory index forbidden by rule: /var/www/html/api/
[Wed Dec 17 14:15:26 2025] [error] Connection to backend server failed after 8 attempts
[Wed Dec 17 14:15:30 2025] [error] Unable to establish connection to worker node
[Wed Dec 17 14:15:35 2025] [error] Unable to establish connection to worker node
[Wed Dec 17 14:15:43 2025] [error] Unable to establish connection to worker node
[Wed Dec 17 14:15:51 2025] [error] Connection to backend server failed after 6 attempts
[Wed Dec 17 14:15:59 2025] [error] Backend connection pool exhausted
[Wed Dec 17 14:16:04 2025] [error] Connection to backend server failed after 10 attempts
[Wed Dec 17 14:16:07 2025] [error] [client 231.18.220.74] File does not exist: /var/www/html/api/
[Wed Dec 17 14:16:13 2025] [error] [client 179.223.229.2] script not found or unable to stat: /var/www/html/
[Wed Dec 17 14:16:17 2025] [error] [client 129.74.200.226] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 14:16:19 2025] [error] mod_jk child init 3 -2
[Wed Dec 17 14:16:27 2025] [notice] caught SIGTERM, shutting down
[Wed Dec 17 14:16:42 2025] [error] Possible brute force attack from 48.9.156.231
[Wed Dec 17 14:16:48 2025] [error] Authentication failed for user 'root' from 252.98.68.204
[Wed Dec 17 14:16:53 2025] [error] Possible brute force attack from 97.150.127.129
[Wed Dec 17 14:17:01 2025] [error] Authentication failed for user 'admin' from 95.143.121.204
[Wed Dec 17 14:17:13 2025] [error] Worker process 6805 failed to initialize
[Wed Dec 17 14:17:21 2025] [error] mod_jk child workerEnv in critical error state 14
[Wed Dec 17 14:17:25 2025] [error] mod_jk child workerEnv in critical error state 10
[Wed Dec 17 14:17:32 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:17:38 2025] [notice] prefork.c: Child process 6678 is entering scoreboard slot 9
[Wed Dec 17 14:17:46 2025] [error] Authentication failed for user 'root' from 216.132.169.65
[Wed Dec 17 14:17:54 2025] [error] Authentication failed for user 'guest' from 147.149.77.213
[Wed Dec 17 14:17:59 2025] [error] Possible brute force attack from 117.222.26.96
[Wed Dec 17 14:18:04 2025] [error] Multiple failed login attempts detected from 152.110.251.37
[Wed Dec 17 14:18:08 2025] [error] Possible brute force attack from 89.241.184.221
[Wed Dec 17 14:18:15 2025] [error] Multiple failed login attempts detected from 232.165.248.70
[Wed Dec 17 14:18:21 2025] [error] Multiple failed login attempts detected from 32.90.45.63
[Wed Dec 17 14:18:24 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:18:28 2025] [notice] prefork.c: Child process 6234 is entering scoreboard slot 6
[Wed Dec 17 14:18:35 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:18:38 2025] [notice] jk2_init() Found child 6906 in scoreboard slot 10
[Wed Dec 17 14:18:43 2025] [notice] Server built: Dec 17 2025 14:18:43
[Wed Dec 17 14:18:45 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:18:47 2025] [error] mod_jk child workerEnv in error state 7
[Wed Dec 17 14:18:53 2025] [notice] caught SIGTERM, shutting down
[Wed Dec 17 14:18:58 2025] [error] jk2_init() Can't find child 6919 in scoreboard
[Wed Dec 17 14:19:00 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 14:19:06 2025] [notice] Server built: Dec 17 2025 14:19:06
[Wed Dec 17 14:19:13 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:19:16 2025] [error] [client 88.8.127.68] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 14:19:23 2025] [error] mod_jk child workerEnv in error state 9
[Wed Dec 17 14:19:27 2025] [error] [client 74.232.204.1] Directory index forbidden by rule: /var/www/html/uploads/
[Wed Dec 17 14:19:29 2025] [error] jk2_init() Can't find child 6918 in scoreboard
[Wed Dec 17 14:19:35 2025] [notice] prefork.c: Child process 6506 is entering scoreboard slot 10
[Wed Dec 17 14:19:43 2025] [notice] jk2_init() Found child 6955 in scoreboard slot 1
[Wed Dec 17 14:19:57 2025] [error] Possible brute force attack from 103.145.30.79
[Wed Dec 17 14:20:04 2025] [error] Multiple failed login attempts detected from 119.35.68.245
[Wed Dec 17 14:20:06 2025] [error] Authentication failed for user 'admin' from 4.209.122.210
[Wed Dec 17 14:20:14 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:20:26 2025] [error] mod_jk child workerEnv in critical error state 12
[Wed Dec 17 14:20:29 2025] [error] mod_jk child workerEnv in critical error state 9
[Wed Dec 17 14:20:32 2025] [error] All workers in error state, service degraded
[Wed Dec 17 14:20:40 2025] [error] mod_jk child workerEnv in critical error state 6
[Wed Dec 17 14:20:45 2025] [error] mod_jk child workerEnv in critical error state 13
[Wed Dec 17 14:20:53 2025] [error] All workers in error state, service degraded
[Wed Dec 17 14:20:55 2025] [error] mod_jk child workerEnv in critical error state 9
[Wed Dec 17 14:20:57 2025] [error] [client 40.5.71.166] Directory index forbidden by rule: /var/www/html/images/
[Wed Dec 17 14:21:01 2025] [error] [client 116.7.113.138] script not found or unable to stat: /var/www/html/uploads/
[Wed Dec 17 14:21:07 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:21:13 2025] [error] mod_jk child init 1 -2
[Wed Dec 17 14:21:15 2025] [error] [client 2.214.9.103] File does not exist: /var/www/html/images/
[Wed Dec 17 14:21:17 2025] [error] mod_jk child workerEnv in error state 6
[Wed Dec 17 14:21:19 2025] [notice] jk2_init() Found child 6377 in scoreboard slot 3
[Wed Dec 17 14:21:26 2025] [error] [client 167.193.28.68] Directory index forbidden by rule: /var/www/html/api/
[Wed Dec 17 14:21:28 2025] [notice] jk2_init() Found child 6192 in scoreboard slot 3
[Wed Dec 17 14:21:32 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 14:21:35 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:21:42 2025] [notice] Server built: Dec 17 2025 14:21:42
[Wed Dec 17 14:21:46 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:21:54 2025] [notice] Server built: Dec 17 2025 14:21:54
[Wed Dec 17 14:21:58 2025] [error] ajp_send_request: Connection reset by peer or network problems
[Wed Dec 17 14:22:06 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:22:09 2025] [error] [client 14.149.23.158] Directory index forbidden by rule: /var/www/html/api/
[Wed Dec 17 14:22:15 2025] [notice] jk2_init() Found child 6115 in scoreboard slot 3
[Wed Dec 17 14:22:17 2025] [error] Child 6017: Encountered too many errors accepting client connections
[Wed Dec 17 14:22:19 2025] [error] [client 94.249.69.98] script not found or unable to stat: /var/www/html/admin/
[Wed Dec 17 14:22:27 2025] [notice] jk2_init() Found child 6529 in scoreboard slot 9
[Wed Dec 17 14:22:31 2025] [notice] Server built: Dec 17 2025 14:22:31
[Wed Dec 17 14:22:38 2025] [notice] jk2_init() Found child 6374 in scoreboard slot 8
[Wed Dec 17 14:22:42 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:22:48 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 14:22:55 2025] [notice] prefork.c: Child process 6997 is entering scoreboard slot 6
[Wed Dec 17 14:23:02 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:23:06 2025] [notice] Server built: Dec 17 2025 14:23:06
[Wed Dec 17 14:23:09 2025] [error] [client 69.226.237.220] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 14:23:21 2025] [error] Authentication failed for user 'root' from 1.31.154.166
[Wed Dec 17 14:23:29 2025] [error] Multiple failed login attempts detected from 184.88.123.189
[Wed Dec 17 14:23:34 2025] [error] Authentication failed for user 'root' from 211.129.145.174
[Wed Dec 17 14:23:40 2025] [error] Authentication failed for user 'guest' from 96.219.97.147
[Wed Dec 17 14:23:43 2025] [error] Multiple failed login attempts detected from 242.255.171.77
[Wed Dec 17 14:23:49 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:23:55 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:24:02 2025] [error] [client 167.10.133.107] File does not exist: /var/www/html/
[Wed Dec 17 14:24:05 2025] [error] [client 169.139.110.4] Directory index forbidden by rule: /var/www/html/admin/
[Wed Dec 17 14:24:07 2025] [notice] jk2_init() Found child 6064 in scoreboard slot 6
[Wed Dec 17 14:24:15 2025] [error] [client 197.111.163.113] script not found or unable to stat: /var/www/html/uploads/
[Wed Dec 17 14:24:21 2025] [error] mod_jk child workerEnv in error state 8
[Wed Dec 17 14:24:26 2025] [error] [client 11.9.28.219] File does not exist: /var/www/html/uploads/
[Wed Dec 17 14:24:33 2025] [error] [client 248.169.223.84] File does not exist: /var/www/html/admin/
[Wed Dec 17 14:24:39 2025] [notice] jk2_init() Found child 6260 in scoreboard slot 9
[Wed Dec 17 14:24:45 2025] [error] [client 21.244.211.244] Directory index forbidden by rule: /usr/local/apache/htdocs/
[Wed Dec 17 14:24:52 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:25:02 2025] [error] Security violation: unauthorized access attempt to /etc/passwd
[Wed Dec 17 14:25:04 2025] [error] Security violation: unauthorized access attempt to /admin
[Wed Dec 17 14:25:11 2025] [error] Access forbidden for 19.130.130.154: insufficient privileges
[Wed Dec 17 14:25:19 2025] [error] Permission denied: user 'root' cannot access /admin
[Wed Dec 17 14:25:25 2025] [error] Security violation: unauthorized access attempt to /config
[Wed Dec 17 14:25:29 2025] [error] mod_jk child workerEnv in error state 9
[Wed Dec 17 14:25:37 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
[Wed Dec 17 14:25:39 2025] [notice] Server built: Dec 17 2025 14:25:39
[Wed Dec 17 14:25:45 2025] [notice] jk2_init() Found child 6638 in scoreboard slot 10
[Wed Dec 17 14:25:50 2025] [notice] Server built: Dec 17 2025 14:25:50
[Wed Dec 17 14:26:00 2025] [error] Possible brute force attack from 14.201.6.223
[Wed Dec 17 14:26:08 2025] [error] Authentication failed for user 'user' from 82.175.142.210
[Wed Dec 17 14:26:10 2025] [error] Possible brute force attack from 102.203.121.128
[Wed Dec 17 14:26:16 2025] [error] Possible brute force attack from 105.133.228.108
[Wed Dec 17 14:26:20 2025] [error] Possible brute force attack from 226.69.81.76
[Wed Dec 17 14:26:26 2025] [error] Multiple failed login attempts detected from 111.12.120.39
[Wed Dec 17 14:26:28 2025] [error] Possible brute force attack from 40.100.14.220
[Wed Dec 17 14:26:32 2025] [error] [client 169.120.5.97] Directory index forbidden by rule: /var/www/html/admin/
[Wed Dec 17 14:26:35 2025] [error] mod_jk child init 3 -2
[Wed Dec 17 14:26:37 2025] [notice] Server built: Dec 17 2025 14:26:37
[Wed Dec 17 14:26:43 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:26:47 2025] [notice] SIGHUP received. Attempting to restart
[Wed Dec 17 14:26:55 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:26:58 2025] [error] mod_jk child init 2 -2
[Wed Dec 17 14:27:00 2025] [error] mod_jk child init 2 -2
[Wed Dec 17 14:27:06 2025] [notice] jk2_init() Found child 6211 in scoreboard slot 3
[Wed Dec 17 14:27:14 2025] [notice] SIGHUP received. Attempting to restart
[Wed Dec 17 14:27:16 2025] [notice] jk2_init() Found child 6177 in scoreboard slot 2
[Wed Dec 17 14:27:20 2025] [error] jk2_init() Can't find child 6390 in scoreboard
[Wed Dec 17 14:27:24 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:27:28 2025] [notice] prefork.c: Child process 6664 is entering scoreboard slot 3
[Wed Dec 17 14:27:34 2025] [error] [client 67.14.82.11] script not found or unable to stat: /usr/local/apache/htdocs/
[Wed Dec 17 14:27:39 2025] [error] [client 228.12.65.212] File does not exist: /var/www/html/api/
[Wed Dec 17 14:27:43 2025] [notice] prefork.c: Child process 6337 is entering scoreboard slot 1
[Wed Dec 17 14:27:54 2025] [error] Access forbidden for 254.95.81.210: insufficient privileges
[Wed Dec 17 14:27:58 2025] [error] Security violation: unauthorized access attempt to /var/log
[Wed Dec 17 14:28:04 2025] [error] Access forbidden for 132.12.154.214: insufficient privileges
[Wed Dec 17 14:28:09 2025] [error] Permission denied: user 'user' cannot access /admin
[Wed Dec 17 14:28:17 2025] [error] Permission denied: user 'guest' cannot access /var/log
[Wed Dec 17 14:28:22 2025] [error] Security violation: unauthorized access attempt to /var/log
[Wed Dec 17 14:28:25 2025] [error] Security violation: unauthorized access attempt to /var/log
[Wed Dec 17 14:28:32 2025] [error] Security violation: unauthorized access attempt to /var/log
[Wed Dec 17 14:28:40 2025] [error] [client 58.212.94.31] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 14:28:46 2025] [notice] jk2_init() Found child 6373 in scoreboard slot 4
[Wed Dec 17 14:28:53 2025] [error] mod_jk child workerEnv in error state 10
[Wed Dec 17 14:28:58 2025] [notice] Server built: Dec 17 2025 14:28:58
[Wed Dec 17 14:29:06 2025] [error] [client 246.174.121.88] script not found or unable to stat: /var/www/html/api/
[Wed Dec 17 14:29:09 2025] [error] [client 223.75.81.135] script not found or unable to stat: /var/www/html/images/
[Wed Dec 17 14:29:15 2025] [error] jk2_init() Can't find child 6704 in scoreboard
[Wed Dec 17 14:29:18 2025] [notice] jk2_init() Found child 6118 in scoreboard slot 3
[Wed Dec 17 14:29:21 2025] [notice] jk2_init() Found child 6803 in scoreboard slot 1
[Wed Dec 17 14:29:27 2025] [error] mod_jk child init 3 -2
[Wed Dec 17 14:29:34 2025] [error] mod_jk child workerEnv in error state 1
[Wed Dec 17 14:29:41 2025] [error] [client 86.172.21.51] Directory index forbidden by rule: /var/www/html/api/
[Wed Dec 17 14:29:44 2025] [notice] jk2_init() Found child 6304 in scoreboard slot 1
[Wed Dec 17 14:29:47 2025] [error] [client 225.139.45.173] Directory index forbidden by rule: /usr/local/apache/htdocs/
[Wed Dec 17 14:29:50 2025] [error] jk2_init() Can't find child 6388 in scoreboard
[Wed Dec 17 14:29:54 2025] [notice] jk2_init() Found child 6179 in scoreboard slot 7
[Wed Dec 17 14:29:56 2025] [notice] Server built: Dec 17 2025 14:29:56
[Wed Dec 17 14:30:00 2025] [error] jk2_init() Can't find child 6599 in scoreboard
[Wed Dec 17 14:30:06 2025] [error] [client 164.254.114.175] Directory index forbidden by rule: /var/www/html/api/
[Wed Dec 17 14:30:13 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:30:17 2025] [notice] Server built: Dec 17 2025 14:30:17
[Wed Dec 17 14:30:20 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:30:23 2025] [notice] caught SIGTERM, shutting down
[Wed Dec 17 14:30:30 2025] [notice] jk2_init() Found child 6038 in scoreboard slot 9
[Wed Dec 17 14:30:34 2025] [error] ajp_send_request: Connection reset by peer or network problems
[Wed Dec 17 14:30:36 2025] [notice] jk2_init() Found child 6392 in scoreboard slot 8
[Wed Dec 17 14:30:42 2025] [error] [client 18.173.19.96] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 14:30:49 2025] [error] [client 13.110.178.84] Directory index forbidden by rule: /var/www/html/
[Wed Dec 17 14:30:56 2025] [error] mod_jk child workerEnv in error state 9
[Wed Dec 17 14:31:04 2025] [error] [client 14.137.76.213] script not found or unable to stat: /var/www/html/admin/
[Wed Dec 17 14:31:07 2025] [notice] prefork.c: Child process 6131 is entering scoreboard slot 4
[Wed Dec 17 14:31:15 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:31:18 2025] [notice] jk2_init() Found child 6132 in scoreboard slot 10
[Wed Dec 17 14:31:25 2025] [notice] jk2_init() Found child 6439 in scoreboard slot 1
[Wed Dec 17 14:31:30 2025] [notice] jk2_init() Found child 6787 in scoreboard slot 5
[Wed Dec 17 14:31:32 2025] [error] ajp_send_request: Connection reset by peer or network problems
[Wed Dec 17 14:31:38 2025] [error] ajp_connection_tcp_get_message: Error receiving message
[Wed Dec 17 14:31:40 2025] [notice] Server built: Dec 17 2025 14:31:40
[Wed Dec 17 14:31:43 2025] [error] [client 41.146.61.105] script not found or unable to stat: /var/www/html/api/
[Wed Dec 17 14:31:49 2025] [error] [client 40.153.213.68] script not found or unable to stat: /var/www/html/uploads/
[Wed Dec 17 14:32:01 2025] [error] Access forbidden for 58.96.83.27: insufficient privileges
[Wed Dec 17 14:32:09 2025] [error] Access forbidden for 133.253.70.135: insufficient privileges
[Wed Dec 17 14:32:16 2025] [error] Permission denied: user 'guest' cannot access /admin
[Wed Dec 17 14:32:19 2025] [error] Access forbidden for 150.217.83.123: insufficient privileges
[Wed Dec 17 14:32:21 2025] [notice] Server built: Dec 17 2025 14:32:21
[Wed Dec 17 14:32:36 2025] [error] Access forbidden for 15.49.204.118: insufficient privileges
[Wed Dec 17 14:32:38 2025] [error] Access forbidden for 126.103.42.85: insufficient privileges
[Wed Dec 17 14:32:45 2025] [error] Security violation: unauthorized access attempt to /etc/passwd
[Wed Dec 17 14:32:47 2025] [error] Access forbidden for 241.49.245.40: insufficient privileges
[Wed Dec 17 14:32:50 2025] [error] Security violation: unauthorized access attempt to /config
[Wed Dec 17 14:32:54 2025] [error] Access forbidden for 143.232.198.229: insufficient privileges
[Wed Dec 17 14:32:58 2025] [notice] jk2_init() Found child 6351 in scoreboard slot 2
[Wed Dec 17 14:33:05 2025] [error] [client 140.218.53.216] Directory index forbidden by rule: /var/www/html/api/
[Wed Dec 17 14:33:12 2025] [notice] Server built: Dec 17 2025 14:33:12
[Wed Dec 17 14:33:17 2025] [error] [client 19.178.53.150] script not found or unable to stat: /var/www/html/uploads/
[Wed Dec 17 14:33:20 2025] [notice] jk2_init() Found child 6115 in scoreboard slot 10
[Wed Dec 17 14:33:22 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:33:25 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:33:30 2025] [notice] caught SIGTERM, shutting down
[Wed Dec 17 14:33:36 2025] [notice] prefork.c: Child process 6456 is entering scoreboard slot 6
[Wed Dec 17 14:33:44 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:33:46 2025] [notice] jk2_init() Found child 6530 in scoreboard slot 6
[Wed Dec 17 14:33:48 2025] [notice] jk2_init() Found child 6987 in scoreboard slot 2
[Wed Dec 17 14:33:55 2025] [error] jk2_init() Can't find child 6626 in scoreboard
[Wed Dec 17 14:34:03 2025] [notice] jk2_init() Found child 6091 in scoreboard slot 6
[Wed Dec 17 14:34:10 2025] [notice] prefork.c: Child process 6966 is entering scoreboard slot 7
[Wed Dec 17 14:34:18 2025] [error] [client 143.117.173.37] Directory index forbidden by rule: /var/www/html/images/
[Wed Dec 17 14:34:21 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:34:23 2025] [error] [client 190.51.223.236] script not found or unable to stat: /var/www/html/admin/
[Wed Dec 17 14:34:28 2025] [notice] prefork.c: Child process 6793 is entering scoreboard slot 4
[Wed Dec 17 14:34:36 2025] [notice] prefork.c: Child process 6137 is entering scoreboard slot 7
[Wed Dec 17 14:34:44 2025] [notice] prefork.c: Child process 6328 is entering scoreboard slot 4
[Wed Dec 17 14:34:47 2025] [notice] Server built: Dec 17 2025 14:34:47
[Wed Dec 17 14:34:53 2025] [error] [client 145.194.249.135] File does not exist: /usr/local/apache/htdocs/
[Wed Dec 17 14:34:57 2025] [error] mod_jk child workerEnv in error state 7
[Wed Dec 17 14:34:59 2025] [notice] prefork.c: Child process 6971 is entering scoreboard slot 8
[Wed Dec 17 14:35:07 2025] [notice] jk2_init() Found child 6674 in scoreboard slot 5
[Wed Dec 17 14:35:11 2025] [notice] Server built: Dec 17 2025 14:35:11
[Wed Dec 17 14:35:23 2025] [error] Unable to establish connection to worker node
[Wed Dec 17 14:35:26 2025] [error] Unable to establish connection to worker node
[Wed Dec 17 14:35:30 2025] [error] Unable to establish connection to worker node
[Wed Dec 17 14:35:33 2025] [error] Backend connection pool exhausted
[Wed Dec 17 14:35:38 2025] [error] Connection to backend server failed after 10 attempts
[Wed Dec 17 14:35:41 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:35:46 2025] [notice] jk2_init() Found child 6917 in scoreboard slot 1
[Wed Dec 17 14:35:48 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:35:55 2025] [error] jk2_init() Can't find child 6064 in scoreboard
[Wed Dec 17 14:35:59 2025] [notice] SIGHUP received. Attempting to restart
[Wed Dec 17 14:36:02 2025] [notice] jk2_init() Found child 6723 in scoreboard slot 7
[Wed Dec 17 14:36:07 2025] [error] mod_jk child init 3 -2
[Wed Dec 17 14:36:12 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:36:19 2025] [notice] Apache/2.2.3 configured -- resuming normal operations
[Wed Dec 17 14:36:22 2025] [error] [client 157.80.209.56] Directory index forbidden by rule: /var/www/html/images/
[Wed Dec 17 14:36:28 2025] [error] [client 141.64.28.227] Directory index forbidden by rule: /usr/local/apache/htdocs/
[Wed Dec 17 14:36:38 2025] [error] Access forbidden for 63.138.98.67: insufficient privileges
[Wed Dec 17 14:36:44 2025] [error] Security violation: unauthorized access attempt to /var/log
[Wed Dec 17 14:36:49 2025] [error] Permission denied: user 'admin' cannot access /etc/passwd
[Wed Dec 17 14:36:53 2025] [error] Permission denied: user 'root' cannot access /var/log
[Wed Dec 17 14:36:56 2025] [error] Permission denied: user 'admin' cannot access /var/log
[Wed Dec 17 14:36:59 2025] [error] [client 246.109.242.238] File does not exist: /usr/local/apache/htdocs/
[Wed Dec 17 14:37:07 2025] [error] [client 144.161.171.17] File does not exist: /var/www/html/api/
[Wed Dec 17 14:37:09 2025] [error] [client 151.51.140.178] script not found or unable to stat: /var/www/html/admin/
[Wed Dec 17 14:37:15 2025] [error] [client 219.180.156.69] Directory index forbidden by rule: /var/www/html/api/
[Wed Dec 17 14:37:17 2025] [notice] jk2_init() Found child 6951 in scoreboard slot 10
[Wed Dec 17 14:37:19 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:37:25 2025] [notice] jk2_init() Found child 6582 in scoreboard slot 7
[Wed Dec 17 14:37:29 2025] [notice] jk2_init() Found child 6733 in scoreboard slot 7
[Wed Dec 17 14:37:31 2025] [error] mod_jk child workerEnv in error state 6
[Wed Dec 17 14:37:33 2025] [error] mod_jk child workerEnv in error state 10
[Wed Dec 17 14:37:40 2025] [notice] Server built: Dec 17 2025 14:37:40
[Wed Dec 17 14:37:44 2025] [notice] jk2_init() Found child 6989 in scoreboard slot 8
[Wed Dec 17 14:37:54 2025] [error] Access forbidden for 254.180.246.231: insufficient privileges
[Wed Dec 17 14:38:01 2025] [error] Permission denied: user 'guest' cannot access /etc/passwd
[Wed Dec 17 14:38:03 2025] [error] Permission denied: user 'root' cannot access /admin
[Wed Dec 17 14:38:11 2025] [notice] Server built: Dec 17 2025 14:38:11
[Wed Dec 17 14:38:18 2025] [notice] Server built: Dec 17 2025 14:38:18
[Wed Dec 17 14:38:22 2025] [error] [client 26.219.55.3] Directory index forbidden by rule: /var/www/html/api/
[Wed Dec 17 14:38:27 2025] [notice] jk2_init() Found child 6519 in scoreboard slot 8
[Wed Dec 17 14:38:29 2025] [error] mod_jk child init 1 -2
[Wed Dec 17 14:38:36 2025] [error] Child 6889: Encountered too many errors accepting client connections
[Wed Dec 17 14:38:44 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:38:47 2025] [notice] Server built: Dec 17 2025 14:38:47
[Wed Dec 17 14:38:51 2025] [error] [client 155.37.28.174] File does not exist: /var/www/html/
[Wed Dec 17 14:38:59 2025] [error] [client 155.116.65.253] script not found or unable to stat: /var/www/html/uploads/
[Wed Dec 17 14:39:07 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:39:13 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[Wed Dec 17 14:39:19 2025] [notice] jk2_init() Found child 6992 in scoreboard slot 1
[Wed Dec 17 14:39:25 2025] [error] [client 150.16.78.209] Directory index forbidden by rule: /var/www/html/
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
    print("   RAG: enabled")
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
        print("\n   Report preview:")
        print(f"   {agent3.get('final_report', '')}")

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
