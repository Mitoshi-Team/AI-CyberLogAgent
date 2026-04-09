"""LangGraph-based analysis pipeline.

This module builds the LangGraph StateGraph for the full analysis pipeline:

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

The AI pipeline (Agent1→RAG→Agent2) runs sequentially,
while YARA and Sigma scans run in parallel from the start.
Agent 3 waits for ALL branches to complete.
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

    # ---- Register nodes ----
    workflow.add_node("agent1", nodes.agent1_node)
    workflow.add_node("mitre_rag", nodes.mitre_rag_node)
    workflow.add_node("agent2", nodes.agent2_node)
    workflow.add_node("yara_scan", nodes.yara_scan_node)
    workflow.add_node("sigma_scan", nodes.sigma_scan_node)
    workflow.add_node("agent3", nodes.agent3_node)

    # ---- Edges: AI pipeline branch (sequential) ----
    # Agent 1 → RAG → Agent 2
    workflow.add_edge("agent1", "mitre_rag")
    workflow.add_edge("mitre_rag", "agent2")

    # ---- Edges: Parallel branches converge into Agent 3 ----
    # AI branch → Agent 3
    workflow.add_edge("agent2", "agent3")

    # YARA branch → Agent 3
    workflow.add_edge("yara_scan", "agent3")

    # Sigma branch → Agent 3
    workflow.add_edge("sigma_scan", "agent3")

    # Agent 3 → END
    workflow.add_edge("agent3", END)

    # ---- Entry point: start 3 parallel branches ----
    workflow.add_edge(START, "agent1")
    workflow.add_edge(START, "yara_scan")
    workflow.add_edge(START, "sigma_scan")

    # ---- Compile without checkpointer (pipeline-style, single run) ----
    # Checkpointer is for multi-turn conversations, not needed for batch analysis
    graph = workflow.compile()

    logger.info("✓ LangGraph pipeline compiled successfully")
    logger.info(f"Graph nodes: {graph.get_graph().nodes}")
    return graph


class LogAnalysisPipeline:
    """Complete log analysis pipeline using LangGraph.

    This class wraps the LangGraph graph and provides the same public API
    as the previous implementation for backward compatibility.

    Flow:
    1. Agent 1: Primary log analysis
    2. RAG: Retrieve MITRE ATT&CK techniques
    3. Agent 2: Generate detailed report
    4. YARA Scan: Rule-based malware detection (parallel)
    5. Sigma Scan: Rule-based SIEM detection (parallel)
    6. Agent 3: Final summarization (all branches converge)

    Usage:
        pipeline = LogAnalysisPipeline(chroma_mgr, llm)
        result = await pipeline.analyze(log_content)
    """

    def __init__(
        self,
        chroma_mgr: ChromaDBManager | None = None,
        llm: BaseLanguageModel | None = None,
        use_rag: bool = True,
        rag_top_k: int = 5,
        yara_engine: Any | None = None,
        sigma_engine: Any | None = None,
    ):
        """Initialize pipeline.

        Args:
            chroma_mgr: ChromaDB manager (can be None if use_rag=False)
            llm: Language model (creates default if None)
            use_rag: Whether to use RAG
            rag_top_k: Number of techniques to retrieve
            yara_engine: YARA engine instance (optional)
            sigma_engine: Sigma engine instance (optional)

        """
        self.chroma_mgr = chroma_mgr
        self.use_rag = use_rag and chroma_mgr is not None
        self.rag_top_k = rag_top_k

        # Create or use provided LLM
        self.llm = llm or create_llm()

        # Build nodes and graph
        self._nodes = PipelineNodes(
            llm=self.llm,
            chroma_mgr=self.chroma_mgr,
            yara_engine=yara_engine,
            sigma_engine=sigma_engine,
            use_rag=self.use_rag,
            rag_top_k=self.rag_top_k,
        )
        self._graph = build_analysis_graph(self._nodes)

        logger.info(
            f"LogAnalysisPipeline initialized, "
            f"RAG={self.use_rag}, YARA={yara_engine is not None}, Sigma={sigma_engine is not None}"
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
            Dictionary with all results (backward-compatible format)

        """
        start_time = time.time()

        # Initial state
        initial_state: AnalysisState = {
            "log_content": log_content,
            "log_size": len(log_content),
            "success": False,
            "error": None,
            "total_time_sec": 0.0,
            "processing_time_ms": 0.0,
            # Defaults (will be overwritten by nodes)
            "primary_analysis": "",
            "events_found": 0,
            "mitre_context": "",
            "mitre_techniques": [],
            "technique_ids": [],
            "search_query": "",
            "agent2_report": "",
            "severity_level_id": 3,
            "threat_type_id": 11,
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
            # Invoke the graph
            logger.info("Invoking LangGraph pipeline...")

            final_state = await self._graph.ainvoke(
                initial_state,
                config=config,
            )

            elapsed = time.time() - start_time

            # ---- Build backward-compatible result ----
            # Stage 1: Agent 1
            results["stages"]["agent1"] = {
                "success": True,
                "primary_analysis": final_state.get("primary_analysis", ""),
                "events_found": final_state.get("events_found", 0),
            }

            # Stage 2: RAG
            results["stages"]["rag"] = {
                "success": True,
                "mitre_context": final_state.get("mitre_context", ""),
                "techniques_count": len(final_state.get("mitre_techniques", [])),
                "technique_ids": final_state.get("technique_ids", []),
            }

            # Stage 3: Agent 2
            results["stages"]["agent2"] = {
                "success": True,
                "final_report": final_state.get("agent2_report", ""),
                "severity_level_id": final_state.get("severity_level_id", 3),
                "threat_type_id": final_state.get("threat_type_id", 11),
                "mitre_techniques": final_state.get("mitre_techniques_final", []),
            }

            # Stage 4: YARA (new)
            results["stages"]["yara"] = {
                "success": True,
                "matches": final_state.get("yara_matches", []),
                "rules_matched": final_state.get("yara_rules_matched", []),
                "context": final_state.get("yara_context", ""),
            }

            # Stage 5: Sigma (new)
            results["stages"]["sigma"] = {
                "success": True,
                "matches": final_state.get("sigma_matches", []),
                "rules_matched": final_state.get("sigma_rules_matched", []),
                "context": final_state.get("sigma_context", ""),
            }

            # Stage 6: Agent 3 (final)
            results["stages"]["agent3"] = {
                "success": True,
                "final_report": final_state.get("final_report", ""),
                "severity_level_id": final_state.get("severity_level_id", 3),
                "threat_type_id": final_state.get("threat_type_id", 11),
                "mitre_techniques": final_state.get("mitre_techniques_final", []),
                "yara_rules": final_state.get("yara_rules_matched", []),
                "sigma_rules": final_state.get("sigma_rules_matched", []),
            }

            # Summary
            results["success"] = True
            results["total_time_sec"] = elapsed
            results["final_report"] = final_state.get("final_report", "")
            results["severity_level_id"] = final_state.get("severity_level_id", 3)
            results["threat_type_id"] = final_state.get("threat_type_id", 11)
            results["mitre_techniques"] = final_state.get("mitre_techniques_final", [])
            results["events_found"] = final_state.get("events_found", 0)

            logger.info(
                f"✓ LangGraph pipeline complete in {elapsed:.1f}s: "
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

    Convenience function to create pipeline with proper initialization.

    Args:
        chroma_path: Path to ChromaDB (auto-creates if needed)
        use_rag: Whether to use RAG
        llm_config: Optional LLM configuration
        yara_rules_path: Path to YARA rules directory (future)
        sigma_rules_path: Path to Sigma rules directory (future)

    Returns:
        Initialized LogAnalysisPipeline

    """
    logger.info("Creating LangGraph analysis pipeline...")

    # Initialize ChromaDB if using RAG
    chroma_mgr = None
    if use_rag:
        if chroma_path is None:
            chroma_path = str(Path(__file__).parent.parent / "chroma_db")

        logger.info(f"Initializing ChromaDB at {chroma_path}")
        chroma_mgr = initialize_mitre_knowledge_base(
            persist_directory=chroma_path,
        )

        # Check if initialization actually succeeded
        if chroma_mgr is not None and not chroma_mgr.is_initialized:
            logger.warning(
                "ChromaDB is not initialized — disabling RAG. "
                "Pipeline will continue without MITRE ATT&CK context."
            )
            chroma_mgr = None
            use_rag = False

    # Create LLM
    llm_kwargs = llm_config or {}
    llm = create_llm(**llm_kwargs)

    # TODO: Initialize YARA and Sigma engines when ready
    # yara_engine = init_yara_engine(yara_rules_path) if yara_rules_path else None
    # sigma_engine = init_sigma_engine(sigma_rules_path) if sigma_rules_path else None
    yara_engine = None
    sigma_engine = None

    # Create pipeline
    pipeline = LogAnalysisPipeline(
        chroma_mgr=chroma_mgr,
        llm=llm,
        use_rag=use_rag,
        yara_engine=yara_engine,
        sigma_engine=sigma_engine,
    )

    logger.info("✓ LangGraph pipeline created successfully")
    return pipeline
