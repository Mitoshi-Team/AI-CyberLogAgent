"""Lightweight pre-filtering for log analysis pipeline.

This module provides fast, lightweight filtering to reduce log volume
before expensive LLM/YARA/Sigma processing while preserving security-relevant logs.
"""

import re

from ..parsers.apache_parser import ParsedLog

# Compiled regex patterns for fast matching
SECURITY_KEYWORDS = re.compile(
    r"\b(?:failed|error|denied|invalid|attack|intrusion|breach|"
    r"exploit|vulnerability|malware|virus|trojan|ransomware|"
    r"unauthorized|suspicious|anomaly|alert|warning|critical)\b",
    re.IGNORECASE,
)

AUTH_KEYWORDS = re.compile(
    r"\b(?:login|logout|authentication|auth|password|"
    r"credential|session|token|sudo|su|privilege|"
    r"escalation|admin|administrator|root)\b",
    re.IGNORECASE,
)

NETWORK_KEYWORDS = re.compile(
    r"\b(?:connection|connect|disconnect|bind|"
    r"listen|accept|port|protocol|tcp|udp|"
    r"firewall|ids|ips|intrusion)\b",
    re.IGNORECASE,
)

PATH_KEYWORDS = re.compile(
    r"\b(?:admin|wp-admin|phpmyadmin|console|"
    r"shell|cmd|powershell|bash|sh|"
    r"\.exe|\.dll|\.bat|\.ps1)\b",
    re.IGNORECASE,
)

# Common safe patterns that can be sampled more aggressively
SAFE_PATTERNS = [
    re.compile(r"\b(?:heartbeat|keepalive|ping|pong)\b", re.IGNORECASE),
    re.compile(r"\b(?:started|starting|stopped|stopping)\b", re.IGNORECASE),
    re.compile(r"\b(?:health|status|check)\b", re.IGNORECASE),
]


def is_security_relevant(log_entry: ParsedLog) -> bool:
    """Quickly determine if a log entry is security-relevant.

    Returns True for logs that should definitely be processed,
    False for logs that can be safely filtered/sampled.
    """
    message = log_entry.get("message", "").lower()
    raw = log_entry.get("raw", "").lower()
    uri = log_entry.get("uri", "").lower()

    # Check combined text for security indicators
    combined_text = f"{message} {raw} {uri}"

    # High priority security indicators
    if SECURITY_KEYWORDS.search(combined_text):
        return True

    if AUTH_KEYWORDS.search(combined_text):
        return True

    if NETWORK_KEYWORDS.search(combined_text):
        return True

    if PATH_KEYWORDS.search(combined_text):
        return True

    # Check log level if available
    level = log_entry.get("level", "").lower()
    if level in ("warning", "warn", "error", "critical", "alert", "emergency"):
        return True

    return False


def should_sample_log(log_entry: ParsedLog, recent_failed_attempts: dict) -> bool:
    """Determine if a log should be sampled (kept) or filtered out.

    Returns True if log should be kept, False if it can be filtered out.
    """
    # Always keep security-relevant logs
    if is_security_relevant(log_entry):
        return True

    # Get source identifiers for context tracking
    client_ip = log_entry.get("client_ip")
    user = log_entry.get("user") or log_entry.get("ident")

    # Keep logs from entities with recent failed attempts
    if client_ip and client_ip in recent_failed_attempts:
        if recent_failed_attempts[client_ip] > 0:
            return True

    if user and user in recent_failed_attempts:
        if recent_failed_attempts[user] > 0:
            return True

    # Check for safe patterns that can be sampled more aggressively
    message = log_entry.get("message", "").lower()
    for pattern in SAFE_PATTERNS:
        if pattern.search(message):
            # Sample 10% of safe, repetitive logs
            return hash(message) % 10 == 0  # Deterministic sampling

    # Default: keep 30% of remaining logs to preserve context
    # Using hash for deterministic sampling across runs
    combined_id = f"{client_ip or ''}{user or ''}{log_entry.get('raw', '')[:50]}"
    return hash(combined_id) % 10 < 3  # Keep 30%


def update_failed_attempts_tracking(log_entry: ParsedLog, tracking_dict: dict):
    """Update tracking of failed authentication attempts for context-aware filtering."""
    message = log_entry.get("message", "").lower()
    raw = log_entry.get("raw", "").lower()
    combined = f"{message} {raw}"

    # Detect failed login attempts
    failed_indicators = [
        r"failed.*login",
        r"login.*failed",
        r"invalid.*password",
        r"password.*invalid",
        r"authentication.*failed",
        r"failed.*auth",
        r"access.*denied",
        r"denied.*access",
    ]

    is_failed_attempt = any(
        re.search(pattern, combined) for pattern in failed_indicators
    )

    if is_failed_attempt:
        # Track failed attempts by IP and user
        client_ip = log_entry.get("client_ip")
        user = log_entry.get("user") or log_entry.get("ident")

        if client_ip:
            tracking_dict[client_ip] = tracking_dict.get(client_ip, 0) + 1
        if user:
            tracking_dict[user] = tracking_dict.get(user, 0) + 1
    else:
        # Detect successful logins to reset counters
        success_indicators = [
            r"successful.*login",
            r"login.*successful",
            r"accepted.*password",
            r"password.*accepted",
            r"session.*opened",
            r"login.*session",
        ]

        is_success = any(re.search(pattern, combined) for pattern in success_indicators)

        if is_success:
            # Reset counters on successful login (but keep some history)
            client_ip = log_entry.get("client_ip")
            user = log_entry.get("user") or log_entry.get("ident")

            if client_ip in tracking_dict:
                # Reduce but don't zero out to maintain some context
                tracking_dict[client_ip] = max(0, tracking_dict[client_ip] - 1)
            if user in tracking_dict:
                tracking_dict[user] = max(0, tracking_dict[user] - 1)


def prefilter_logs(log_content: str) -> tuple[str, dict]:
    """Apply lightweight pre-filtering to log content.

    Args:
        log_content: Raw log content as string

    Returns:
        Tuple of (filtered_log_content, stats_dict)

    """
    if not log_content.strip():
        return log_content, {"original_lines": 0, "filtered_lines": 0, "kept_lines": 0}

    lines = log_content.splitlines()
    if not lines:
        return log_content, {"original_lines": 0, "filtered_lines": 0, "kept_lines": 0}

    # Track failed attempts for context-aware filtering
    failed_attempts_tracking = {}

    # First pass: parse logs and apply filtering
    kept_lines = []
    filtered_count = 0

    for line in lines:
        if not line.strip():
            # Keep empty lines for formatting
            kept_lines.append(line)
            continue

        # Parse the log line to get structured data
        try:
            from ..parsers.apache_parser import parse_line

            parsed_log = parse_line(line)

            # Update tracking based on this log
            update_failed_attempts_tracking(parsed_log, failed_attempts_tracking)

            # Decide whether to keep this log
            if should_sample_log(parsed_log, failed_attempts_tracking):
                kept_lines.append(line)
            else:
                filtered_count += 1

        except Exception:
            # If parsing fails, keep the line to be safe
            kept_lines.append(line)

    filtered_content = "\n".join(kept_lines)

    stats = {
        "original_lines": len(lines),
        "filtered_lines": filtered_count,
        "kept_lines": len(kept_lines),
        "filter_ratio": len(kept_lines) / len(lines) if lines else 0,
    }

    return filtered_content, stats
