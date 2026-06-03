"""Lightweight pre-filtering for log analysis pipeline.
 
This module provides fast, lightweight filtering to reduce log volume
before expensive LLM/YARA/Sigma processing while preserving security-relevant logs.
"""

import re
import time
import os

from ..parsers.apache_parser import ParsedLog


# Sampling rate for non-security logs (default 40%)
_SAMPLING_RATE_STR = os.getenv("AI_V2_SAMPLING_RATE", "0.4")
try:
    SAMPLING_RATE = float(_SAMPLING_RATE_STR)
    if SAMPLING_RATE < 0.0 or SAMPLING_RATE > 1.0:
        raise ValueError("Sampling rate must be between 0.0 and 1.0")
except (ValueError, TypeError):
    SAMPLING_RATE = 0.4  # Default 40%

# Convert to threshold for line_index % 10 comparison
_SAMPLING_THRESHOLD = int(SAMPLING_RATE * 10)  # 0.4 -> 4 (keep 40%)

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

# Suspicious patterns that might indicate unknown attacks
SUSPICIOUS_KEYWORDS = re.compile(
    r"\b(?:unusual|unexpected|abnormal|suspicious|"
    r"anomaly|timeout|refused|blocked|"
    r"overflow|injection|traversal|"
    r"unauthorized|breach|exploit|malware|"
    r"ransomware|trojan|virus)\b",
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
    message = (log_entry.get("message") or "").lower()
    raw = (log_entry.get("raw") or "").lower()
    uri = (log_entry.get("uri") or "").lower()

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

    # Check for suspicious patterns (potential unknown attacks)
    if SUSPICIOUS_KEYWORDS.search(combined_text):
        return True

    # Check log level if available
    level = log_entry.get("level", "").lower()
    if level in ("warning", "warn", "error", "critical", "alert", "emergency"):
        return True

    return False


def should_sample_log(log_entry: ParsedLog, recent_failed_attempts: dict, line_index: int = 0) -> bool:
    """Determine if a log should be sampled (kept) or filtered out.

    Args:
        log_entry: Parsed log entry
        recent_failed_attempts: Dict tracking failed attempts with TTL
        line_index: Line index for unique sampling across identical messages

    Returns:
        True if log should be kept, False if it can be filtered out.
    """
    # Always keep security-relevant logs
    if is_security_relevant(log_entry):
        return True

    # Get source identifiers for context tracking
    client_ip = log_entry.get("client_ip")
    user = log_entry.get("user") or log_entry.get("ident")

    # Check for expired entries first (TTL: 24 hours)
    current_time = time.time()
    for key in list(recent_failed_attempts.keys()):
        if key in recent_failed_attempts:
            data = recent_failed_attempts[key]
            if current_time - data["last_seen"] > 24 * 3600:
                del recent_failed_attempts[key]

    # Keep logs from entities with recent failed attempts
    if client_ip and client_ip in recent_failed_attempts:
        if recent_failed_attempts[client_ip]["count"] > 0:
            return True

    if user and user in recent_failed_attempts:
        if recent_failed_attempts[user]["count"] > 0:
            return True

    # Check for safe patterns that can be sampled more aggressively
    message = log_entry.get("message", "").lower()
    for pattern in SAFE_PATTERNS:
        if pattern.search(message):
            # Deterministic 10% sampling using line_index
            return line_index % 10 == 0  # Keep every 10th log

    # Default: keep configurable % of remaining logs to preserve context
    # Using line_index for simple deterministic sampling
    client_ip = log_entry.get("client_ip")
    user = log_entry.get("user") or log_entry.get("ident")
    raw = (log_entry.get("raw") or "")[:50]
    combined_id = f"{client_ip or ''}{user or ''}{raw}"
    return line_index % 10 < _SAMPLING_THRESHOLD  # Keep ~40% by default


def update_failed_attempts_tracking(log_entry: ParsedLog, tracking_dict: dict):
    """Update tracking of failed authentication attempts for context-aware filtering.

    Uses hybrid approach: track count + timestamp for TTL-based expiration.
    Does NOT reset on successful login to preserve attack context.
    """
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
        # Track failed attempts by IP and user with timestamp
        client_ip = log_entry.get("client_ip")
        user = log_entry.get("user") or log_entry.get("ident")
        current_time = time.time()

        if client_ip:
            if client_ip not in tracking_dict:
                tracking_dict[client_ip] = {"count": 0, "last_seen": current_time}
            tracking_dict[client_ip]["count"] += 1
            tracking_dict[client_ip]["last_seen"] = current_time

        if user:
            if user not in tracking_dict:
                tracking_dict[user] = {"count": 0, "last_seen": current_time}
            tracking_dict[user]["count"] += 1
            tracking_dict[user]["last_seen"] = current_time

    # NOTE: We do NOT reset on successful login - preserve attack context!
    # The TTL mechanism in should_sample_log() will expire old entries.


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

    for idx, line in enumerate(lines):
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

            # Decide whether to keep this log (pass line index for sampling)
            if should_sample_log(parsed_log, failed_attempts_tracking, idx):
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
