"""Agent 1: Primary log analysis chain."""

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

from ..models_types import SuspiciousEvent
from ..parsers import parse_log_content
from ..prompts import (
    PRIMARY_ANALYSIS_SYSTEM_PROMPT,
    PRIMARY_ANALYSIS_USER_PROMPT_V2,
)

logger = logging.getLogger(__name__)


def create_agent1_chain(llm: BaseLanguageModel) -> RunnableSequence:
    """Create Agent 1 chain for primary log analysis.

    Args:
        llm: LangChain language model (e.g., GigaChat)

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


def parse_events_from_response(response: str) -> list[SuspiciousEvent]:
    """Parse suspicious events from Agent 1 response.

    Args:
        response: LLM response containing ---EVENTS--- section

    Returns:
        List of SuspiciousEvent dictionaries

    """
    events = []

    events_match = re.search(r"---EVENTS---\s*(\[[\s\S]*?\])\s*---EVENTS---", response)

    if events_match:
        try:
            events_data = json.loads(events_match.group(1))
            for event in events_data:
                events.append(
                    SuspiciousEvent(
                        description=event.get("description", ""),
                        timestamp=event.get("timestamp"),
                        log_line=event.get("log_line", ""),
                    )
                )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse events JSON: {e}")

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
        - suspicious_events: list of SuspiciousEvent
        - events_found: count of events

    """
    chain = create_agent1_chain(llm)

    logger.info("Running Agent 1 analysis...")
    result = await chain.ainvoke({"log_content": log_content})

    primary_analysis = result
    mini_report = extract_mini_report(result)
    suspicious_events = parse_events_from_response(result)

    events_found = len(suspicious_events)

    logger.info(f"Agent 1 complete: {events_found} suspicious events found")

    return {
        "primary_analysis": primary_analysis,
        "mini_report": mini_report,
        "suspicious_events": suspicious_events,
        "events_found": events_found,
    }
