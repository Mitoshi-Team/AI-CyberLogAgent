"""Pipeline results logger for detection metrics.

Writes detection results to a structured file for later comparison
against ground truth (e.g. from mitre-log-simulator).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SEPARATOR = "-----------------\n"
ENTRY_FIELDS = ["timestamp_start", "timestamp_end", "AGENT1", "RAG", "YARA", "SIGMA"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _format_list(items: list[str]) -> str:
    return ", ".join(items) if items else "Нет"


def _extract_timestamp_range(stages: dict[str, Any]) -> tuple[str, str]:
    """Extract the earliest first_seen and latest last_seen from agent1 groups."""
    groups: list[dict] = stages.get("agent1", {}).get("groups", [])
    if not groups:
        return "N/A", "N/A"

    starts = [g.get("first_seen", "") for g in groups if g.get("first_seen")]
    ends = [g.get("last_seen", "") for g in groups if g.get("last_seen")]

    start = min(starts) if starts else "N/A"
    end = max(ends) if ends else "N/A"
    return start, end


def _extract_agent1_events(stages: dict[str, Any]) -> list[str]:
    """Extract event_type from each agent1 group (unconfirmed events)."""
    groups: list[dict] = stages.get("agent1", {}).get("groups", [])
    return [g.get("event_type", "") for g in groups if g.get("event_type")]


def _extract_rag_techniques(stages: dict[str, Any]) -> list[str]:
    """Extract MITRE technique IDs from agent2 stage."""
    techniques: list[dict] = stages.get("agent2", {}).get("mitre_techniques", [])
    ids: list[str] = []
    for t in techniques:
        tid = t.get("technique_id", "")
        if tid:
            ids.append(tid)
    return ids


def _extract_yara_rules(stages: dict[str, Any]) -> list[str]:
    return list(stages.get("yara", {}).get("rules_matched", []))


def _extract_sigma_rules(stages: dict[str, Any]) -> list[str]:
    return list(stages.get("sigma", {}).get("rules_matched", []))


def log_incident(filepath: str | Path, stages: dict[str, Any]) -> None:
    """Append one detection incident block to the metrics file.

    Args:
        filepath: Path to the metrics log file (appended).
        stages: The ``stages`` dict from pipeline ``analyze()`` results.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    agent1 = _extract_agent1_events(stages)
    rag = _extract_rag_techniques(stages)
    yara = _extract_yara_rules(stages)
    sigma = _extract_sigma_rules(stages)
    start, end = _extract_timestamp_range(stages)

    now = _now_iso()
    lines = [
        f"{now} - INCIDENT",
        SEPARATOR,
        f"timestamp_start: {start}",
        f"timestamp_end: {end}",
        f"AGENT1: {_format_list(agent1)}",
        f"RAG: {_format_list(rag)}",
        f"YARA: {_format_list(yara)}",
        f"SIGMA: {_format_list(sigma)}",
        SEPARATOR,
    ]
    text = "\n".join(lines)

    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"Metrics: logged incident (AGENT1={len(agent1)}, RAG={len(rag)}, YARA={len(yara)}, SIGMA={len(sigma)})")
    except OSError as e:
        logger.warning(f"Metrics: failed to write {path}: {e}")
