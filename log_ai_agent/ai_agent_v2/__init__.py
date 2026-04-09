"""AI Agent v2 - Log analysis pipeline with LangGraph and RAG.

Architecture:
┌─────────────────────────────────────────────┐
│           log_content (input)               │
└───┬──────────────┬──────────────┬───────────┘
    │              │              │
┌───▼───┐    ┌────▼────┐   ┌────▼────┐
│Agent 1│    │  YARA   │   │  Sigma  │
└───┬───┘    └─────────┘   └─────────┘
    │
┌───▼───┐
│ RAG   │
└───┬───┘
    │
┌───▼───┐
│Agent 2│
└───┬───┘
    │
    └──────────────┬──────────────┐
                   │              │
            ┌──────▼──────┐       │
            │   Agent 3   │◄──────┘
            │ (summarize) │
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │  END (report)│
            └─────────────┘

Usage:
    # Quick start
    from log_ai_agent.ai_agent_v2 import create_pipeline

    pipeline = await create_pipeline(use_rag=True)
    results = await pipeline.analyze(log_content)

    # Or use CLI
    uv run -m log_ai_agent.ai_agent_v2.run
"""

from .chains.llm import create_gigachat_llm, create_llm
from .config import AgentConfig, LLMProvider
from .knowledge_base.mitre_loader import initialize_mitre_knowledge_base
from .models_types import AnalysisState, PipelineResult
from .pipeline import LogAnalysisPipeline, create_pipeline

__all__ = [
    # Pipeline
    "LogAnalysisPipeline",
    "create_pipeline",
    # Config
    "AgentConfig",
    "LLMProvider",
    # ChromaDB
    "initialize_mitre_knowledge_base",
    # LLM
    "create_llm",
    "create_gigachat_llm",  # backward compatibility
    # Types
    "AnalysisState",
    "PipelineResult",
]
