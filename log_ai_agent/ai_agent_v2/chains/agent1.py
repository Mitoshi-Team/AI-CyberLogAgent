"""Agent 1: Primary log analysis chain with event grouping."""

import json
import logging
import re
from typing import Any

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnableSequence

from ..models_types import EventGroup, SuspiciousEvent
from ..parsers import parse_log_content
from ..prompts import (
    PRIMARY_ANALYSIS_SYSTEM_PROMPT,
    PRIMARY_ANALYSIS_USER_PROMPT_V2,
)

logger = logging.getLogger(__name__)


def create_agent1_chain(llm: BaseLanguageModel) -> RunnableSequence:
    """Create Agent 1 chain for primary log analysis.

    Args:
        llm: LangChain language model (e.g., Ollama)

    Returns:
        RunnableSequence for primary analysis

    """
    logger.info("Creating Agent 1 chain for primary log analysis")

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(PRIMARY_ANALYSIS_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(PRIMARY_ANALYSIS_USER_PROMPT_V2),
        ]
    )

    chain: RunnableSequence = prompt | llm | StrOutputParser()

    logger.info("Agent 1 chain created")
    return chain


def extract_timestamp_from_log_line(log_line: str) -> str | None:
    """Extract timestamp from a log line.

    Args:
        log_line: Raw log line

    Returns:
        Timestamp string or None

    """
    syslog_pattern = re.compile(r"^\[([^\]]+)\]")
    clf_pattern = re.compile(r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})")

    syslog_match = syslog_pattern.match(log_line.strip())
    if syslog_match:
        return syslog_match.group(1)

    clf_match = clf_pattern.search(log_line)
    if clf_match:
        return clf_match.group(1)

    return None


def build_log_line_mapping(log_content: str) -> dict[str, str]:
    """Build a mapping of log line prefixes to full lines with timestamps.

    Args:
        log_content: Raw log content

    Returns:
        Dictionary mapping log line prefixes to full lines with timestamps

    """
    parsed_logs = parse_log_content(log_content)
    mapping = {}

    for parsed in parsed_logs:
        timestamp = parsed.get("timestamp")
        if timestamp:
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            mapping[parsed["raw"]] = timestamp_str

    return mapping


def parse_groups_from_response(response: str) -> list[EventGroup]:

    groups = []

    start_marker = "---GROUPS---"
    start_idx = response.find(start_marker)
    if start_idx == -1:
        logger.warning(
            f"[Agent1/Parse] ---GROUPS--- marker not found "
            f"(response length {len(response)}, first 300 chars: {response[:300]!r})"
        )
        return groups

    logger.info(
        f"[Agent1/Parse] Opening ---GROUPS--- at position {start_idx} "
        f"(response length {len(response)})"
    )

    start_idx += len(start_marker)
    end_idx = response.find(start_marker, start_idx)

    groups_data: list | None = None
    if end_idx != -1:
        json_str = response[start_idx:end_idx].strip()
        logger.info(
            f"[Agent1/Parse] Closing marker found at {end_idx}, "
            f"JSON region: {len(json_str)} chars"
        )
        if json_str:
            try:
                groups_data = json.loads(json_str)
                logger.info(
                    f"[Agent1/Parse] json.loads OK: {len(groups_data)} groups"
                )
            except json.JSONDecodeError as e:
                logger.warning(
                    f"[Agent1/Parse] json.loads failed at char {e.pos}: {e}"
                )
                return groups
    else:
        logger.info(
            "[Agent1/Parse] No closing marker, falling back to raw_decode"
        )
        search_idx = start_idx
        while search_idx < len(response) and response[search_idx] not in "[{":
            search_idx += 1
        if search_idx < len(response):
            decoder = json.JSONDecoder()
            try:
                parsed, end_pos = decoder.raw_decode(response, search_idx)
                groups_data = parsed if isinstance(parsed, list) else [parsed]
                json_len = end_pos - search_idx
                logger.info(
                    f"[Agent1/Parse] raw_decode OK: {len(groups_data)} groups, "
                    f"{json_len} JSON chars (ends at {end_pos})"
                )
            except json.JSONDecodeError as e:
                logger.warning(
                    f"[Agent1/Parse] raw_decode failed at char {e.pos}: {e}"
                )
                logger.warning(
                    f"[Agent1/Parse] Context around error: "
                    f"{response[max(0, e.pos - 100):e.pos + 100]!r}"
                )
                return groups
        else:
            logger.warning(
                f"[Agent1/Parse] No JSON array/object found after marker "
                f"(search_idx={search_idx}, response length {len(response)})"
            )
            return groups

    if groups_data is None:
        logger.warning("[Agent1/Parse] groups_data is None after extraction")
        return groups

    for group in groups_data:
        event_group: EventGroup = {
            "group_id": group.get("group_id", f"g{len(groups) + 1}"),
            "log_lines": group.get("log_lines", []),
            "first_seen": group.get("first_seen", ""),
            "last_seen": group.get("last_seen", ""),
        }
        groups.append(event_group)

    logger.info(f"[Agent1/Parse] Returning {len(groups)} groups")
    return groups


def parse_events_from_response(response: str) -> list[SuspiciousEvent]:
    """Parse suspicious events from Agent 1 response (legacy compatibility).

    Args:
        response: LLM response containing ---GROUPS--- section

    Returns:
        List of SuspiciousEvent (flattened from groups)

    """
    events = []
    groups = parse_groups_from_response(response)
    for group in groups:
        for log_line in group.get("log_lines", []):
            events.append(
                SuspiciousEvent(
                    description=log_line,
                    timestamp=None,
                    log_line=log_line,
                )
            )
    return events


def extract_mini_report(response: str) -> str:
    """Extract mini report from Agent 1 response.

    Args:
        response: LLM response containing ## Краткий отчёт section

    Returns:
        Mini report text

    """
    mini_match = re.search(
        r"##\s*Краткий отчёт\s*\n\s*([\s\S]*?)(?=\n##|\n---EVENTS---|$)",
        response,
        re.IGNORECASE,
    )

    if mini_match:
        return mini_match.group(1).strip()

    lines = response.split("\n")
    for i, line in enumerate(lines):
        if "краткий" in line.lower() or "summary" in line.lower():
            if i + 1 < len(lines):
                return "\n".join(lines[i + 1 : i + 4]).strip()

    return response[:200] + "..."


async def analyze_logs_primary(
    llm: BaseLanguageModel,
    log_content: str,
) -> dict[str, Any]:
    """Analyze logs using Agent 1 chain.

    Args:
        llm: Language model
        log_content: Raw log content

    Returns:
        Dictionary with:
        - primary_analysis: full analysis text
        - mini_report: brief summary
        - groups: list of EventGroup with suspicious events
        - events_found: count of events across all groups

    """
    chain = create_agent1_chain(llm)

    logger.info("[Agent1] Running Agent 1 analysis...")
    result = await chain.ainvoke({"log_content": log_content})
    logger.info(f"[Agent1] LLM response received: {len(result)} chars")
    logger.info(
        f"[Agent1] ---GROUPS--- marker present: {'---GROUPS---' in result}"
    )

    primary_analysis = result
    mini_report = extract_mini_report(result)
    groups = parse_groups_from_response(result)

    events_found = sum(len(g.get("log_lines", [])) for g in groups)

    if not groups:
        logger.warning(
            f"[Agent1] Parsed 0 groups. Response preview (first 500 chars): "
            f"{result[:500]!r}"
        )
    else:
        logger.info(f"[Agent1] Parsed {len(groups)} groups, {events_found} events")
        for g in groups:
            logger.info(
                f"[Agent1]   Group {g['group_id']}: "
                f"{len(g.get('events', []))} events, "
                f"keywords={g.get('keywords', [])[:3]}..."
            )

    logger.info(f"[Agent1] Complete: {len(groups)} groups, {events_found} events found")

    return {
        "primary_analysis": primary_analysis,
        "mini_report": mini_report,
        "groups": groups,
        "events_found": events_found,
    }
