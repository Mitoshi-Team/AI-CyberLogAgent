"""Full analysis pipeline — LangGraph-based implementation.

This module re-exports the LangGraph-based pipeline for backward compatibility.
All existing imports (create_pipeline, LogAnalysisPipeline) continue to work.

The new architecture uses LangGraph StateGraph with parallel branches:
- AI Pipeline: Agent 1 → RAG (MITRE) → Agent 2
- YARA Scan: Rule-based malware detection
- Sigma Scan: Rule-based SIEM detection
- Agent 3: Final summarization (all branches converge)
"""

from .langgraph_pipeline import LogAnalysisPipeline, create_pipeline

__all__ = ["LogAnalysisPipeline", "create_pipeline"]
