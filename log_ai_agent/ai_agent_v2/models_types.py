"""Type definitions for LangGraph compatibility."""

from typing import TypedDict


class AnalysisState(TypedDict, total=False):
    """State type for LangGraph (future compatibility).

    This TypedDict defines the state that flows through the analysis pipeline.
    Currently used for type hints, will be used with LangGraph StateGraph.
    """

    # Input
    log_content: str

    # Agent 1 output
    primary_analysis: str
    events_found: int

    # RAG output
    mitre_context: str
    mitre_techniques: list[dict]
    technique_ids: list[str]
    search_query: str

    # Agent 2 output
    final_report: str
    severity_level_id: int
    threat_type_id: int
    mitre_techniques_final: list[str]

    # Metadata
    success: bool
    error: str | None
    total_time_sec: float
    log_size: int


class PipelineResult(TypedDict, total=False):
    """Result type for pipeline execution."""

    success: bool
    log_size: int
    total_time_sec: float

    # Stage results
    agent1_result: dict | None
    rag_result: dict | None
    agent2_result: dict | None

    # Error information
    error: str | None
    error_stage: str | None


class MITRATechnique(TypedDict):
    """MITRE ATT&CK technique type."""

    technique_id: str
    technique_name: str
    tactic: str
    description: str
    platforms: list[str]
    data_sources: list[str]
