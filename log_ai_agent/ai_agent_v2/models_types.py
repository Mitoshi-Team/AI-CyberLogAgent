"""Type definitions for LangGraph compatibility."""

from typing import TypedDict


class AnalysisState(TypedDict, total=False):
    """State type for LangGraph analysis pipeline.

    This TypedDict defines the state that flows through the analysis pipeline.
    The pipeline has 4 parallel branches that converge in Agent 3:
    - AI Pipeline: Agent 1 → RAG (MITRE) → Agent 2
    - YARA Scan: Rule-based malware detection
    - Sigma Scan: Rule-based SIEM detection
    - Agent 3: Final summarization

    State flow:
    ┌─────────────────────────────────────┐
    │         log_content (input)         │
    └────┬────────────┬─────────┬─────────┘
         │            │         │
    ┌────▼────┐  ┌───▼────┐ ┌─▼────────┐
    │ Agent 1 │  │  YARA  │ │  Sigma   │
    └────┬────┘  └───┬────┘ └─┬────────┘
         │            │         │
    ┌────▼────┐       │         │
    │  RAG    │       │         │
    └────┬────┘       │         │
         │            │         │
    ┌────▼────┐  ┌───▼────┐ ┌─▼────────┐
    │ Agent 2 │  │  YARA  │ │  Sigma   │
    └────┬────┘  └───┬────┘ └─┬────────┘
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

    # ===== AGENT 1 OUTPUT =====
    primary_analysis: str
    events_found: int

    # ===== RAG (MITRE) OUTPUT =====
    mitre_context: str
    mitre_techniques: list[dict]
    technique_ids: list[str]
    search_query: str

    # ===== AGENT 2 OUTPUT =====
    agent2_report: str
    severity_level_id: int
    threat_type_id: int
    mitre_techniques_final: list[str]

    # ===== YARA SCAN OUTPUT =====
    yara_matches: list[dict]
    yara_rules_matched: list[str]
    yara_context: str

    # ===== SIGMA SCAN OUTPUT =====
    sigma_matches: list[dict]
    sigma_rules_matched: list[str]
    sigma_context: str

    # ===== AGENT 3 OUTPUT (FINAL) =====
    final_report: str
    recommendations: list[str]

    # ===== METADATA =====
    success: bool
    error: str | None
    total_time_sec: float
    log_size: int
    processing_time_ms: float


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
