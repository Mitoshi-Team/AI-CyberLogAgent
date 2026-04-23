"""Chains module."""

from ..config import LLMProvider
from .agent1 import analyze_logs_primary, create_agent1_chain
from .agent2 import create_agent2_chain, generate_final_report, parse_metadata
from .agent3 import create_agent3_chain
from .agent3 import generate_final_report as generate_agent3_report
from .graph_nodes import PipelineNodes
from .llm import create_gigachat_llm, create_llm
from .rag_chain import retrieve_mitre_context, search_mitre_techniques

__all__ = [
    "create_agent1_chain",
    "analyze_logs_primary",
    "create_agent2_chain",
    "generate_final_report",
    "parse_metadata",
    "retrieve_mitre_context",
    "search_mitre_techniques",
    # Agent 3
    "create_agent3_chain",
    "generate_agent3_report",
    # Graph nodes
    "PipelineNodes",
    # LLM factory
    "create_llm",
    "create_gigachat_llm",  # backward compatibility
    "LLMProvider",
]
