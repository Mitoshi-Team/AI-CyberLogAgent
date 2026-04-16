"""Universal Apache log parser supporting multiple formats."""

import re
from datetime import datetime
from typing import TypedDict

APACHE_SYSLOG_PATTERN = re.compile(
    r"^\[([^\]]+)\]\s*\[([^\]]+)\](?:\s*\[client\s+([^\]]+)\])?\s*(.*)$"
)

APACHE_CLF_PATTERN = re.compile(
    r"^(\S+)\s+"  # host
    r"(\S+)\s+"  # ident
    r"(\S+)\s+"  # user
    r"\[([^\]]+)\]\s*"  # date:time
    r'"([^"]*)"\s*'  # request
    r"(\d+)\s+"  # status
    r"(\S+)"  # size
    r"(?:\s+\"([^\"]*)\"(?:\s+\"([^\"]*)\")?)?"  # referer, user-agent
)

REQUEST_PATTERN = re.compile(r"^(\S+)\s+(\S+)(?:\s+\S+)?$")

LEVEL_PATTERNS = [
    (re.compile(r"\berror\b", re.I), "error"),
    (re.compile(r"\bwarning\b", re.I), "warning"),
    (re.compile(r"\bwarn\b", re.I), "warning"),
    (re.compile(r"\bnotice\b", re.I), "notice"),
    (re.compile(r"\binfo\b", re.I), "info"),
    (re.compile(r"\bdebug\b", re.I), "debug"),
    (re.compile(r"\bcritical\b", re.I), "critical"),
    (re.compile(r"\balert\b", re.I), "alert"),
    (re.compile(r"\bemerg\b", re.I), "emergency"),
]

CLF_MONTH_MAP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


class ParsedLog(TypedDict, total=False):
    timestamp: datetime | None
    level: str | None
    client_ip: str | None
    method: str | None
    uri: str | None
    query: str | None
    status_code: int | None
    bytes_sent: int | None
    user_agent: str | None
    referer: str | None
    message: str
    raw: str
    format: str


def extract_level(message: str) -> str | None:
    for pattern, level in LEVEL_PATTERNS:
        if pattern.search(message):
            return level
    return None


def parse_clf_timestamp(timestamp_str: str) -> datetime | None:
    try:
        parts = timestamp_str.split()
        if len(parts) == 2:
            date_part, time_part = parts
            day = int(date_part.split("/")[0])
            month = CLF_MONTH_MAP.get(date_part.split("/")[1], 1)
            year = int(date_part.split("/")[2])
            hour, minute, second = map(int, time_part.split(":"))
            return datetime(year, month, day, hour, minute, second)
    except (ValueError, IndexError):
        pass
    return None


def parse_syslog_format(line: str) -> ParsedLog | None:
    match = APACHE_SYSLOG_PATTERN.match(line.strip())
    if not match:
        return None

    timestamp_str, level, client_ip, message = match.groups()

    try:
        timestamp = datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %Y")
    except ValueError:
        timestamp = None

    return ParsedLog(
        timestamp=timestamp,
        level=extract_level(message) or level.lower() if level else None,
        client_ip=client_ip,
        method=None,
        uri=None,
        query=None,
        status_code=None,
        bytes_sent=None,
        user_agent=None,
        referer=None,
        message=message.strip(),
        raw=line,
        format="syslog",
    )


def parse_clf_format(line: str) -> ParsedLog | None:
    match = APACHE_CLF_PATTERN.match(line.strip())
    if not match:
        return None

    host, ident, user, timestamp_str, request, status, size, referer, user_agent = (
        match.groups()
    )

    method, uri = None, None
    if request:
        req_match = REQUEST_PATTERN.match(request)
        if req_match:
            method = req_match.group(1)
            full_uri = req_match.group(2)
            if "?" in full_uri:
                uri, query = full_uri.split("?", 1)
            else:
                uri, query = full_uri, None

    try:
        timestamp = parse_clf_timestamp(timestamp_str)
    except Exception:
        timestamp = None

    try:
        status_code = int(status) if status else None
    except ValueError:
        status_code = None

    try:
        bytes_sent = int(size) if size and size != "-" else None
    except ValueError:
        bytes_sent = None

    return ParsedLog(
        timestamp=timestamp,
        level=None,
        client_ip=host,
        method=method,
        uri=uri,
        query=query,
        status_code=status_code,
        bytes_sent=bytes_sent,
        user_agent=user_agent,
        referer=referer,
        message=line,
        raw=line,
        format="clf",
    )


def parse_line(line: str) -> ParsedLog:
    line = line.strip()
    if not line or line.startswith("#"):
        return ParsedLog(
            timestamp=None,
            level=None,
            client_ip=None,
            method=None,
            uri=None,
            query=None,
            status_code=None,
            bytes_sent=None,
            user_agent=None,
            referer=None,
            message=line,
            raw=line,
            format="unknown",
        )

    result = parse_syslog_format(line)
    if result:
        return result

    result = parse_clf_format(line)
    if result:
        return result

    return ParsedLog(
        timestamp=None,
        level=extract_level(line),
        client_ip=None,
        method=None,
        uri=None,
        query=None,
        status_code=None,
        bytes_sent=None,
        user_agent=None,
        referer=None,
        message=line,
        raw=line,
        format="unknown",
    )


def parse_log_content(log_content: str) -> list[ParsedLog]:
    lines = log_content.splitlines()
    return [parse_line(line) for line in lines if line.strip()]


class ApacheLogParser:
    def __init__(self):
        pass

    def parse(self, log_content: str) -> list[ParsedLog]:
        return parse_log_content(log_content)

    def parse_file(self, filepath: str) -> list[ParsedLog]:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            content = f.read()
        return self.parse(content)
