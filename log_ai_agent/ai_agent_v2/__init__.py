"""AI Agent v2 - Log analysis pipeline with LangChain and RAG.

Usage:
    # Quick start
    from log_ai_agent.ai_agent_v2 import create_pipeline

    pipeline = await create_pipeline(use_rag=True)
    results = await pipeline.analyze(log_content)

    # Or use CLI
    uv run -m log_ai_agent.ai_agent_v2.run
"""

from .chains.llm import create_gigachat_llm
from .config import AgentConfig
from .knowledge_base.mitre_loader import initialize_mitre_knowledge_base
from .models_types import AnalysisState, PipelineResult
from .pipeline.full_pipeline import LogAnalysisPipeline, create_pipeline

__all__ = [
    # Pipeline
    "LogAnalysisPipeline",
    "create_pipeline",
    # Config
    "AgentConfig",
    # ChromaDB
    "initialize_mitre_knowledge_base",
    # LLM
    "create_gigachat_llm",
    # Types
    "AnalysisState",
    "PipelineResult",
]
