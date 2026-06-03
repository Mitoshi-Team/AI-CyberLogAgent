#!/usr/bin/env python3
"""Tests for Prefilter node."""

import pytest
from log_ai_agent.ai_agent_v2.chains.prefilter import (
    prefilter_logs,
    is_security_relevant,
    should_sample_log,
    update_failed_attempts_tracking,
)
from log_ai_agent.ai_agent_v2.parsers.apache_parser import ParsedLog


def test_prefilter_basic():
    """Test basic prefiltering removes noise."""
    log_content = "[Wed Dec 17 13:06:06 2025] [error] Authentication failed for user admin\n[Wed Dec 17 13:06:07 2025] [error] Multiple failed login attempts\n[Wed Dec 17 13:06:08 2025] [notice] Apache started normally\n[Wed Dec 17 13:06:09 2025] [notice] child process started"
    filtered, stats = prefilter_logs(log_content)

    assert stats["original_lines"] == 4
    # At least the error lines should be kept
    assert stats["kept_lines"] >= 2
    assert stats["filtered_lines"] >= 0
    assert "Authentication failed" in filtered
    # Notice lines might be filtered
    assert isinstance(stats["filter_ratio"], float)


def test_prefilter_empty_logs():
    """Test prefilter with empty input."""
    filtered, stats = prefilter_logs("")
    
    assert stats["original_lines"] == 0
    assert stats["kept_lines"] == 0
    assert filtered == ""


def test_prefilter_all_noise():
    """Test prefilter when all lines are noise."""
    log_content = "[Wed Dec 17 13:06:06 2025] [notice] Apache/2.2.3 configured -- resuming normal operations\n[Wed Dec 17 13:06:07 2025] [notice] caught SIGTERM, shutting down\n[Wed Dec 17 13:06:08 2025] [notice] prefork.c: Child process 1234 entering scoreboard"
    filtered, stats = prefilter_logs(log_content)

    # Function may keep some lines due to sampling (~30%)
    # Just check that it runs without error
    assert stats["original_lines"] == 3
    assert isinstance(stats["kept_lines"], int)
    assert isinstance(stats["filtered_lines"], int)
    assert stats["kept_lines"] + stats["filtered_lines"] == stats["original_lines"]


def test_security_keywords_kept():
    """Test that lines with security keywords are always kept."""
    # Security keywords from SECURITY_KEYWORDS and SUSPICIOUS_KEYWORDS patterns
    security_logs = """[Wed Dec 17 13:06:06 2025] [error] Authentication failed for user admin
[Wed Dec 17 13:06:07 2025] [error] Multiple failed login attempts
[Wed Dec 17 13:06:08 2025] [warning] Potential intrusion detected
[Wed Dec 17 13:06:09 2025] [error] Malware signature found: Trojan.Generic
[Wed Dec 17 13:06:10 2025] [critical] Data breach detected
[Wed Dec 17 13:06:11 2025] [error] Unusual activity detected from 192.168.1.100
[Wed Dec 17 13:06:12 2025] [warning] Abnormal behavior: multiple connections
[Wed Dec 17 13:06:13 2025] [error] Suspicious: unexpected command execution"""
    
    filtered, stats = prefilter_logs(security_logs)
    
    # All security-related lines should be kept (8 total)
    assert stats["kept_lines"] == 8
    assert stats["filtered_lines"] == 0
    assert "Authentication failed" in filtered
    assert "intrusion" in filtered
    assert "Malware" in filtered
    assert "Unusual activity" in filtered
    assert "Abnormal behavior" in filtered
    assert "Suspicious" in filtered


def test_auth_keywords_kept():
    """Test that authentication-related logs are kept."""
    auth_logs = """[Wed Dec 17 13:06:06 2025] [info] User admin logged in
[Wed Dec 17 13:06:07 2025] [notice] Sudo command executed by user root
[Wed Dec 17 13:06:08 2025] [info] New session opened for user john
[Wed Dec 17 13:06:09 2025] [error] Privilege escalation attempt detected"""
    
    filtered, stats = prefilter_logs(auth_logs)
    
    # All auth-related lines should be kept
    assert stats["kept_lines"] == 4
    assert stats["filtered_lines"] == 0


def test_network_keywords_kept():
    """Test that network-related security logs are kept."""
    network_logs = """[Wed Dec 17 13:06:06 2025] [error] Connection refused from 192.168.1.100
[Wed Dec 17 13:06:07 2025] [warning] Firewall blocked suspicious packet
[Wed Dec 17 13:06:08 2025] [error] IDS alert: Possible port scan detected
[Wed Dec 17 13:06:09 2025] [info] Bind to port 443 successful"""
    
    filtered, stats = prefilter_logs(network_logs)
    
    # Network security events should be kept
    assert stats["kept_lines"] >= 3  # At least connection, firewall, IDS
    assert "Firewall" in filtered
    assert "IDS" in filtered


def test_path_keywords_kept():
    """Test that logs with suspicious paths/commands are kept."""
    path_logs = """[Wed Dec 17 13:06:06 2025] [error] Access denied to /admin/console
[Wed Dec 17 13:06:07 2025] [error] Cmd.exe executed: format C:
[Wed Dec 17 13:06:08 2025] [error] PowerShell script blocked: malicious.ps1
[Wed Dec 17 13:06:09 2025] [notice] Access to wp-admin granted"""
    
    filtered, stats = prefilter_logs(path_logs)
    
    # All logs with suspicious paths/commands should be kept
    assert stats["kept_lines"] == 4
    assert "cmd.exe" in filtered.lower()
    assert "PowerShell" in filtered


def test_failed_attempts_tracking():
    """Test that logs from IPs with recent failed attempts are kept."""
    # First create logs with failed attempts, then more logs from same IP
    log_content = """[Wed Dec 17 13:06:06 2025] [error] [client 192.168.1.100] Authentication failed for user admin
[Wed Dec 17 13:06:07 2025] [error] [client 192.168.1.100] Authentication failed for user admin
[Wed Dec 17 13:06:08 2025] [notice] [client 192.168.1.100] User john logged in
[Wed Dec 17 13:06:09 2025] [notice] [client 192.168.1.100] GET /api/status 200"""

    filtered, stats = prefilter_logs(log_content)

    # Due to failed attempts tracking, all logs from 192.168.1.100 should be kept
    # (success does NOT reset the counter now)
    assert stats["kept_lines"] == 4
    assert "logged in" in filtered
    assert "GET /api/status" in filtered


def test_safe_patterns_sampled():
    """Test that safe patterns are aggressively sampled (10%)."""
    # Create many heartbeat/keepalive logs with DIFFERENT content (different timestamps)
    # Using correct Apache error log format that parses successfully
    safe_logs = "\n".join([
        f"[Wed Dec 17 13:{i:02d}:00 2025] [info] Heartbeat check OK"
        for i in range(100)  # 100 logs
    ])

    filtered, stats = prefilter_logs(safe_logs)

    # Safe patterns should be sampled (not all kept)
    # Due to line_index-based sampling, ~10% should be kept
    assert stats["kept_lines"] < 100  # Not all kept
    assert stats["filtered_lines"] > 0  # Some filtered out
    # The ratio should be roughly 10% (allow wide range for hash variability)
    if stats["kept_lines"] > 0:
        ratio = stats["kept_lines"] / 100
        assert ratio < 0.5  # Less than 50% kept


def test_error_level_always_kept():
    """Test that error/warning/critical levels are always kept."""
    mixed_logs = """[Wed Dec 17 13:06:06 2025] [error] Something went wrong
[Wed Dec 17 13:06:07 2025] [warning] Potential issue detected
[Wed Dec 17 13:06:08 2025] [critical] System failure
[Wed Dec 17 13:06:09 2025] [alert] Security breach
[Wed Dec 17 13:06:10 2025] [info] Normal operation"""
    
    filtered, stats = prefilter_logs(mixed_logs)
    
    # Error/warning/critical/alert should be kept
    assert stats["kept_lines"] >= 4
    assert "Something went wrong" in filtered
    assert "System failure" in filtered


def test_parse_failure_keeps_line():
    """Test that lines which fail to parse are kept (safe fallback)."""
    # Malformed log line that can't be parsed
    malformed = "[This is not a valid apache log line"
    
    filtered, stats = prefilter_logs(malformed)
    
    # Failed parse should keep the line
    assert stats["kept_lines"] == 1
    assert "not a valid apache log" in filtered


def test_is_security_relevant():
    """Unit test for is_security_relevant function."""
    # Test security keywords
    log1 = {"message": "Authentication failed", "raw": "", "uri": ""}
    assert is_security_relevant(log1) == True
    
    # Test auth keywords
    log2 = {"message": "User admin logged in", "raw": "", "uri": ""}
    assert is_security_relevant(log2) == True
    
    # Test safe log
    log3 = {"message": "Server started", "raw": "", "uri": ""}
    assert is_security_relevant(log3) == False


def test_should_sample_log():
    """Unit test for should_sample_log function."""
    import time

    # Security relevant should always be kept
    sec_log = {"message": "attack detected", "raw": "", "uri": "", "level": "error"}
    assert should_sample_log(sec_log, {}, line_index=0) == True
    
    # Non-security with no tracking - sampled at 30%
    normal_log = {"message": "routine check", "raw": "", "uri": "", "client_ip": "1.2.3.4"}
    # Can't assert exact result due to hash, but should return bool
    result = should_sample_log(normal_log, {}, line_index=0)
    assert isinstance(result, bool)
    
    # With failed attempts tracking (new structure)
    tracked_log = {"message": "some activity", "raw": "", "uri": "", "client_ip": "5.6.7.8"}
    tracking_dict = {"5.6.7.8": {"count": 3, "last_seen": time.time()}}
    assert should_sample_log(tracked_log, tracking_dict, line_index=0) == True


def test_update_failed_attempts():
    """Unit test for update_failed_attempts_tracking function."""
    tracking = {}

    # Test failed login
    failed_log = {"message": "authentication failed", "raw": "", "client_ip": "10.0.0.1", "user": "admin"}
    update_failed_attempts_tracking(failed_log, tracking)
    assert tracking.get("10.0.0.1")["count"] == 1
    assert tracking.get("admin")["count"] == 1
    assert "last_seen" in tracking["10.0.0.1"]

    # Test another failure
    update_failed_attempts_tracking(failed_log, tracking)
    assert tracking.get("10.0.0.1")["count"] == 2

    # Test successful login does NOT reset counter
    success_log = {"message": "session opened", "raw": "", "client_ip": "10.0.0.1", "user": "admin"}
    update_failed_attempts_tracking(success_log, tracking)
    # Counter should REMAIN (not reset on success!)
    assert tracking.get("10.0.0.1")["count"] == 2  # Not changed
    assert tracking.get("admin")["count"] == 2  # Not changed (was 2 after two failures)


def test_ttl_expiration():
    """Test that tracking entries expire after 24 hours."""
    import time

    tracking = {}

    # Add a failed attempt
    failed_log = {"message": "authentication failed", "raw": "", "client_ip": "10.0.0.1", "user": "admin"}
    update_failed_attempts_tracking(failed_log, tracking)
    assert "10.0.0.1" in tracking

    # Simulate time passing (25 hours later)
    old_timestamp = tracking["10.0.0.1"]["last_seen"]
    tracking["10.0.0.1"]["last_seen"] = old_timestamp - (25 * 3600)

    # Check if should_sample_log cleans up expired entry
    test_log = {"message": "some activity", "raw": "", "client_ip": "10.0.0.1", "user": None}
    # Call should_sample_log which should clean expired entries
    result = should_sample_log(test_log, tracking, line_index=0)

    # The expired entry should be cleaned up
    assert "10.0.0.1" not in tracking  # Expired!


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
