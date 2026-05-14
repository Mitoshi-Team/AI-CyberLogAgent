"""LangGraph-based analysis pipeline.

This module builds the LangGraph StateGraph for the full analysis pipeline:

Architecture:
```
┌─────────────────────────────────────────────┐
│           log_content (input)              │
└────┬────────────┬─────────────┬───────────┘
     │            │             │
┌────▼────┐ ┌───▼─────┐ ┌───▼──────┐
│Prefilter │ │parse_log│ │  YARA     │
└────┬────┘ └────┬─────┘ └────┬─────┘
     │            │             │
┌────▼────┐     │       ┌─────▼─────┐
│ Agent 1 │     │       │  Sigma    │
└────┬────┘     └───────┴────┬─────┘
     │                        │
     │            ┌──────────┴──────────┐
     ▼            │                     ▼
┌──────────────────┴────┐      ┌──────────┐
│  Description Agent   │      │ Agent 3  │
└──────────────┬───────┘      └──────────┘
               │
┌──────────────▼───────┐
│       Agent 2 (RAG)  │──────▶│ Agent 3 │
└──────────────────────┘       └──────────┘
```

Flow:
- START → prefilter → Agent 1 (groups of events)
- START → parse_logs → YARA/Sigma (all logs, no filtering)
- Agent1 → Description Agent (generate group descriptions)
- Description Agent → Agent2 (RAG search for each description)
- All branches converge at Agent 3
"""

import logging
import time
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseLanguageModel
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from ..chains.graph_nodes import PipelineNodes
from ..chains.llm import create_llm
from ..engines import SigmaEngine, YaraEngine
from ..knowledge_base.manager import ChromaDBManager
from ..knowledge_base.mitre_loader import initialize_mitre_knowledge_base
from ..models_types import AnalysisState

logger = logging.getLogger(__name__)


def build_analysis_graph(
    nodes: PipelineNodes,
) -> Any:
    """Build the LangGraph StateGraph for analysis pipeline.

    Args:
        nodes: PipelineNodes instance with bound dependencies

    Returns:
        Compiled LangGraph graph (ready to invoke)

    """
    logger.info("Building LangGraph analysis pipeline...")

    workflow = StateGraph(AnalysisState)

    workflow.add_node("prefilter", nodes.prefilter_node)
    workflow.add_node("agent1", nodes.agent1_node)
    workflow.add_node("description_agent", nodes.description_agent_node)
    workflow.add_node("parse_logs", nodes.parse_logs_node)
    workflow.add_node("agent2", nodes.agent2_node)
    workflow.add_node("yara_scan", nodes.yara_scan_node)
    workflow.add_node("sigma_scan", nodes.sigma_scan_node)
    workflow.add_node("agent3", nodes.agent3_node)

    workflow.add_edge("prefilter", "agent1")
    workflow.add_edge("agent1", "description_agent")

    # parse_logs runs on all logs (not filtered), for YARA/Sigma
    workflow.add_edge("parse_logs", "yara_scan")
    workflow.add_edge("parse_logs", "sigma_scan")

    # Conditional edge: if no groups found by agent1, skip description_agent and agent2
    def should_skip_description_agent(state):
        return state.get("groups", []) == []

    workflow.add_conditional_edges(
        "description_agent",
        should_skip_description_agent,
        {
            True: "agent3",
            False: "agent2",
        },
    )

    workflow.add_edge("agent2", "agent3")
    workflow.add_edge("yara_scan", "agent3")
    workflow.add_edge("sigma_scan", "agent3")

    workflow.add_edge("agent3", END)

    # START connects to both prefilter (for Agent 1) and parse_logs (for YARA/Sigma)
    workflow.add_edge(START, "prefilter")
    workflow.add_edge(START, "parse_logs")

    graph = workflow.compile()

    logger.info("LangGraph pipeline compiled successfully")
    logger.info(f"Graph nodes: {graph.get_graph().nodes}")
    return graph


class LogAnalysisPipeline:
    """Complete log analysis pipeline using LangGraph.

    Flow:
    1. Agent 1: Primary log analysis + suspicious_events
    2. Agent 2: RAG search for each event + report generation
    3. YARA Scan: Rule-based malware detection (parallel)
    4. Sigma Scan: Rule-based SIEM detection (parallel)
    5. Agent 3: Final summarization (all branches converge)
    """

    def __init__(
        self,
        chroma_mgr: ChromaDBManager | None = None,
        llm: BaseLanguageModel | None = None,
        use_rag: bool = True,
        rag_top_k: int = 5,
        rag_score_threshold: float = 0.7,
        yara_engine: Any | None = None,
        sigma_engine: Any | None = None,
    ):
        """Initialize pipeline.

        Args:
            chroma_mgr: ChromaDB manager (can be None if use_rag=False)
            llm: Language model (creates default if None)
            use_rag: Whether to use RAG
            rag_top_k: Number of techniques to retrieve
            rag_score_threshold: Minimum similarity threshold for RAG (0.0-1.0). Default: 0.7
            yara_engine: YARA engine instance (optional)
            sigma_engine: Sigma engine instance (optional)

        """
        self.chroma_mgr = chroma_mgr
        self.use_rag = use_rag and chroma_mgr is not None
        self.rag_top_k = rag_top_k
        self.rag_score_threshold = rag_score_threshold

        self.llm = llm or create_llm()

        self._nodes = PipelineNodes(
            llm=self.llm,
            chroma_mgr=self.chroma_mgr,
            yara_engine=yara_engine,
            sigma_engine=sigma_engine,
            use_rag=self.use_rag,
            rag_top_k=self.rag_top_k,
            rag_score_threshold=self.rag_score_threshold,
            rag_parallelism=8,  # Increased from default 3 for better parallelism
        )
        self._graph = build_analysis_graph(self._nodes)

        logger.info(
            f"LogAnalysisPipeline initialized, "
            f"RAG={self.use_rag}, rag_top_k={rag_top_k}, rag_score_threshold={rag_score_threshold}, "
            f"YARA={yara_engine is not None}, Sigma={sigma_engine is not None}"
        )

    async def analyze(
        self,
        log_content: str,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        """Analyze log content through full LangGraph pipeline.

        Args:
            log_content: Raw log content
            config: Optional LangChain config (callbacks, etc.)

        Returns:
            Dictionary with all results

        """
        start_time = time.time()

        initial_state: AnalysisState = {
            "log_content": log_content,
            "log_size": len(log_content),
            "success": False,
            "error": None,
            "total_time_sec": 0.0,
            "processing_time_ms": 0.0,
            "parsed_logs": [],
            "primary_analysis": "",
            "mini_report": "",
            "groups": [],
            "events_found": 0,
            "group_descriptions": [],
            "mitre_context": "",
            "mitre_techniques": [],
            "technique_ids": [],
            "search_query": "",
            "agent2_report": "",
            "mitre_techniques_final": [],
            "yara_matches": [],
            "yara_rules_matched": [],
            "yara_context": "",
            "sigma_matches": [],
            "sigma_rules_matched": [],
            "sigma_context": "",
            "final_report": "",
            "recommendations": [],
        }

        results = {
            "log_size": len(log_content),
            "stages": {},
        }

        try:
            logger.info("Invoking LangGraph pipeline...")

            final_state = await self._graph.ainvoke(
                initial_state,
                config=config,
            )

            elapsed = time.time() - start_time

            results["stages"]["prefilter"] = {
                "success": True,
                "stats": final_state.get("prefilter_stats", {}),
            }

            results["stages"]["agent1"] = {
                "success": True,
                "primary_analysis": final_state.get("primary_analysis", ""),
                "mini_report": final_state.get("mini_report", ""),
                "groups": final_state.get("groups", []),
                "events_found": final_state.get("events_found", 0),
            }

            # Description Agent stage
            results["stages"]["description_agent"] = {
                "success": True,
                "group_descriptions": final_state.get("group_descriptions", []),
                "descriptions_count": len(final_state.get("group_descriptions", [])),
            }

            # Agent 2 stage (contains RAG processing results + agent2 report)
            results["stages"]["agent2"] = {
                "success": True,
                "mitre_context": final_state.get("mitre_context", ""),
                "mitre_techniques": final_state.get("mitre_techniques_final", []),
                "technique_ids": final_state.get("technique_ids", []),
                "agent2_report": final_state.get("agent2_report", ""),
            }

            # Separate RAG stage for test compatibility
            results["stages"]["rag"] = {
                "success": True,
                "techniques_count": len(final_state.get("mitre_techniques_final", [])),
                "technique_ids": final_state.get("technique_ids", []),
            }

            results["stages"]["yara"] = {
                "success": True,
                "matches": final_state.get("yara_matches", []),
                "rules_matched": final_state.get("yara_rules_matched", []),
                "context": final_state.get("yara_context", ""),
            }

            results["stages"]["sigma"] = {
                "success": True,
                "matches": final_state.get("sigma_matches", []),
                "rules_matched": final_state.get("sigma_rules_matched", []),
                "context": final_state.get("sigma_context", ""),
            }

            results["stages"]["agent3"] = {
                "success": True,
                "final_report": final_state.get("final_report", ""),
                "severity_level_id": final_state.get("severity_level_id", 3),
                "threat_type_id": final_state.get("threat_type_id", 11),
                "mitre_techniques": final_state.get("mitre_techniques_final", []),
                "yara_rules": final_state.get("yara_rules_matched", []),
                "sigma_rules": final_state.get("sigma_rules_matched", []),
            }

            results["success"] = True
            results["total_time_sec"] = elapsed
            results["final_report"] = final_state.get("final_report", "")
            results["severity_level_id"] = final_state.get("severity_level_id", 3)
            results["threat_type_id"] = final_state.get("threat_type_id", 11)
            results["mitre_techniques"] = final_state.get("mitre_techniques_final", [])
            results["events_found"] = final_state.get("events_found", 0)

            logger.info(
                f"LangGraph pipeline complete in {elapsed:.1f}s: "
                f"severity={results['severity_level_id']}, threat={results['threat_type_id']}"
            )

        except Exception as e:
            error_details = str(e) or f"{type(e).__name__}: {e!r}"
            logger.exception("LangGraph pipeline error: %s", error_details)
            results["success"] = False
            results["error"] = error_details
            results["total_time_sec"] = time.time() - start_time

        return results


async def create_pipeline(
    chroma_path: str | None = None,
    use_rag: bool = True,
    llm_config: dict | None = None,
    yara_rules_path: str | None = None,
    sigma_rules_path: str | None = None,
) -> LogAnalysisPipeline:
    """Create and initialize analysis pipeline.

    Args:
        chroma_path: Path to ChromaDB (auto-creates if needed)
        use_rag: Whether to use RAG
        llm_config: Optional LLM configuration
        yara_rules_path: Path to YARA rules directory
        sigma_rules_path: Path to Sigma rules directory

    Returns:
        Initialized LogAnalysisPipeline

    """
    logger.info("Creating LangGraph analysis pipeline...")

    chroma_mgr = None
    if use_rag:
        if chroma_path is None:
            chroma_path = str(Path(__file__).parent.parent / "chroma_db")

        logger.info(f"Initializing ChromaDB at {chroma_path}")
        chroma_mgr = initialize_mitre_knowledge_base(
            persist_directory=chroma_path,
        )

        if chroma_mgr is not None and not chroma_mgr.is_initialized:
            logger.warning(
                "ChromaDB is not initialized - disabling RAG. "
                "Pipeline will continue without MITRE ATT&CK context."
            )
            chroma_mgr = None
            use_rag = False

    llm_kwargs = llm_config or {}
    llm = create_llm(**llm_kwargs)

    yara_engine = None
    sigma_engine = None

    try:
        if yara_rules_path:
            logger.info(f"Initializing YARA engine with rules from: {yara_rules_path}")
            yara_engine = YaraEngine(yara_rules_path)
            logger.info(f"YARA engine loaded {yara_engine.rules_count} rule files")
    except Exception as e:
        logger.warning(f"Failed to initialize YARA engine: {e}")
        yara_engine = None

    try:
        if sigma_rules_path:
            logger.info(
                f"Initializing Sigma engine with rules from: {sigma_rules_path}"
            )
            sigma_engine = SigmaEngine(sigma_rules_path)
            logger.info(f"Sigma engine loaded {len(sigma_engine._rules)} rules")
    except Exception as e:
        logger.warning(f"Failed to initialize Sigma engine: {e}")
        sigma_engine = None

    pipeline = LogAnalysisPipeline(
        chroma_mgr=chroma_mgr,
        llm=llm,
        use_rag=use_rag,
        yara_engine=yara_engine,
        sigma_engine=sigma_engine,
    )

    logger.info("LangGraph pipeline created successfully")
    return pipeline
