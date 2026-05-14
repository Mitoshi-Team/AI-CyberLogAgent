"""Type definitions for LangGraph compatibility."""

import operator
from typing import Annotated, TypedDict

from .parsers.apache_parser import ParsedLog


class SuspiciousEvent(TypedDict, total=False):
    """A suspicious event extracted from logs by Agent 1.

    This is sent to Agent 2 for RAG/MITRE lookup.
    Deprecated: Use EventGroup instead.
    """

    description: str
    timestamp: str | None
    log_line: str


class EventGroup(TypedDict, total=False):
    """Group of related events from Agent1.

    Agent1 groups events by possible connection (user, attack_pattern etc.),
    but NOT by timestamp. One event can be in multiple groups.
    """

    group_id: str
    events: list[dict]
    first_seen: str
    last_seen: str
    keywords: list[str]
    description: str


class GroupDescription(TypedDict, total=False):
    """Description of group from Description Agent.

    For each group, one coherent description and keywords are generated.
    """

    group_id: str
    description: str
    first_seen: str
    last_seen: str
    keywords: list[str]


class MITRETechnique(TypedDict, total=False):
    """MITRE ATT&CK technique found by RAG search.

    Includes context from the original event.
    """

    technique_id: str
    name: str
    timestamp: str | None
    event: str
    log_line: str


class AnalysisState(TypedDict, total=False):
    """State type for LangGraph analysis pipeline.

    This TypedDict defines the state that flows through the analysis pipeline.
    The pipeline has parallel branches that converge in Agent 3:

    State flow:
    ┌─────────────────────────────────────┐
    │         log_content (input)         │
    └────┬────────────┬─────────┬───────┘
         │            │         │
    ┌────▼────┐ ┌────▼────┐ ┌─▼──────┐
    │ Agent 1 │ │  YARA   │ │ Sigma  │
    └────┬────┘ └───┬────┘ └──┬──────┘
         │            │         │
    ┌────▼────┐       │         │
    │Agent 2  │       │         │
    │(RAG it) │       │         │
    └────┬────┘       │         │
         │            │         │
         └────────────┼─────────┘
                      │
               ┌──────▼──────┐
               │   Agent 3   │
               │ (summarize) │
               └──────┬──────┘
                      │
               ┌──────▼──────┐
               │  END (report)│
               └─────────────┘
    """

    # ===== INPUT =====
    log_content: str
    parsed_logs: list[ParsedLog]

    # ===== AGENT 1 OUTPUT =====
    primary_analysis: str
    mini_report: str
    events_found: int
    groups: list[EventGroup]

    # ===== DESCRIPTION AGENT OUTPUT =====
    group_descriptions: list[GroupDescription]

    # ===== RAG + AGENT 2 OUTPUT =====
    mitre_context: str
    mitre_techniques: list[dict]
    technique_ids: list[str]
    search_query: str
    mitre_techniques_final: list[MITRETechnique]

    # ===== AGENT 2 OUTPUT =====
    agent2_report: str

    # ===== YARA SCAN OUTPUT =====
    yara_matches: Annotated[list[str], operator.add]
    yara_rules_matched: Annotated[list[str], operator.add]
    yara_context: str

    # ===== SIGMA SCAN OUTPUT =====
    sigma_matches: Annotated[list[str], operator.add]
    sigma_rules_matched: Annotated[list[str], operator.add]
    sigma_context: str

    # ===== AGENT 3 OUTPUT (FINAL) =====
    final_report: str
    recommendations: list[str]
    severity_level_id: int
    threat_type_id: int
    confidence_level: str
    unconfirmed_events_count: int

    # ===== METADATA =====
    success: bool
    error: str | None
    total_time_sec: float
    log_size: int
    processing_time_ms: float
    prefilter_stats: dict


class PipelineResult(TypedDict, total=False):
    """Result type for pipeline execution."""

    success: bool
    log_size: int
    total_time_sec: float

    agent1_result: dict | None
    rag_result: dict | None
    agent2_result: dict | None

    error: str | None
    error_stage: str | None


class MITRATechnique(TypedDict):
    """MITRE ATT&CK technique type (original, for compatibility)."""

    technique_id: str
    technique_name: str
    tactic: str
    description: str
    platforms: list[str]
    data_sources: list[str]
