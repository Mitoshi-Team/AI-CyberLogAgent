"""LangGraph nodes for the analysis pipeline.

This module defines all nodes used in the LangGraph StateGraph.
Each node takes AnalysisState as input and returns a partial state update.
"""

import logging
import time
from typing import Any

from langchain_core.language_models import BaseLanguageModel

from ..knowledge_base.manager import ChromaDBManager
from ..models_types import AnalysisState
from .agent1 import create_agent1_chain
from .agent2 import generate_final_report as generate_agent2_report
from .rag_chain import retrieve_mitre_context

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Factory: create all node functions with bound dependencies
# ---------------------------------------------------------------------------


class PipelineNodes:
    """Container for all pipeline nodes with bound dependencies.

    Usage:
        nodes = PipelineNodes(llm, chroma_mgr, yara_engine, sigma_engine)
        graph = StateGraph(AnalysisState)
        graph.add_node("agent1", nodes.agent1_node)
        ...
    """

    def __init__(
        self,
        llm: BaseLanguageModel,
        chroma_mgr: ChromaDBManager | None = None,
        yara_engine: Any | None = None,
        sigma_engine: Any | None = None,
        use_rag: bool = True,
        rag_top_k: int = 5,
    ):
        self.llm = llm
        self.chroma_mgr = chroma_mgr
        self.yara_engine = yara_engine
        self.sigma_engine = sigma_engine
        self.use_rag = use_rag and chroma_mgr is not None
        self.rag_top_k = rag_top_k

        # Pre-build chains
        self._agent1_chain = create_agent1_chain(llm)

    # ===================================================================
    # AGENT 1 — Primary log analysis
    # ===================================================================

    async def agent1_node(self, state: AnalysisState) -> dict:
        """Node: Agent 1 — Primary log analysis.

        Reads: log_content
        Writes: primary_analysis, events_found
        """
        logger.info("[Node] Agent 1: Primary log analysis")
        start = time.time()

        try:
            result = await self._agent1_chain.ainvoke(
                {"log_content": state["log_content"]}
            )
            events_found = result.count("### Событие")

            logger.info(
                f"[Node] Agent 1 complete: {events_found} events in {time.time() - start:.1f}s"
            )
            return {
                "primary_analysis": result,
                "events_found": events_found,
            }

        except Exception as e:
            logger.exception(f"[Node] Agent 1 failed: {e}")
            return {
                "primary_analysis": f"Ошибка анализа: {e}",
                "events_found": 0,
            }

    # ===================================================================
    # MITRE RAG — Retrieve MITRE ATT&CK techniques
    # ===================================================================

    async def mitre_rag_node(self, state: AnalysisState) -> dict:
        """Node: RAG — Retrieve MITRE ATT&CK context.

        Reads: primary_analysis
        Writes: mitre_context, mitre_techniques, technique_ids, search_query
        """
        logger.info("[Node] MITRE RAG: Retrieving techniques")
        start = time.time()

        if not self.use_rag or not self.chroma_mgr:
            logger.warning("[Node] MITRE RAG: disabled or unavailable")
            return {
                "mitre_context": "RAG (MITRE ATT&CK) отключён.",
                "mitre_techniques": [],
                "technique_ids": [],
                "search_query": "",
            }

        try:
            rag_result = await retrieve_mitre_context(
                llm=self.llm,
                chroma_mgr=self.chroma_mgr,
                primary_analysis=state["primary_analysis"],
                k=self.rag_top_k,
            )

            logger.info(
                f"[Node] MITRE RAG complete: {len(rag_result['mitre_techniques'])} "
                f"techniques in {time.time() - start:.1f}s"
            )
            return {
                "mitre_context": rag_result["mitre_context"],
                "mitre_techniques": rag_result["mitre_techniques"],
                "technique_ids": rag_result["technique_ids"],
                "search_query": rag_result["search_query"],
            }

        except Exception as e:
            logger.exception(f"[Node] MITRE RAG failed: {e}")
            return {
                "mitre_context": f"Ошибка RAG: {e}",
                "mitre_techniques": [],
                "technique_ids": [],
                "search_query": "",
            }

    # ===================================================================
    # AGENT 2 — Detailed AI report
    # ===================================================================

    async def agent2_node(self, state: AnalysisState) -> dict:
        """Node: Agent 2 — Detailed AI report with MITRE context.

        Reads: primary_analysis, mitre_context
        Writes: agent2_report, severity_level_id, threat_type_id, mitre_techniques_final
        """
        logger.info("[Node] Agent 2: Generating detailed report")
        start = time.time()

        try:
            agent2_result = await generate_agent2_report(
                llm=self.llm,
                primary_analysis=state["primary_analysis"],
                mitre_context=state.get("mitre_context", ""),
            )

            logger.info(
                f"[Node] Agent 2 complete: severity={agent2_result['severity_level_id']}, "
                f"threat={agent2_result['threat_type_id']} in {time.time() - start:.1f}s"
            )
            return {
                "agent2_report": agent2_result["final_report"],
                "severity_level_id": agent2_result["severity_level_id"],
                "threat_type_id": agent2_result["threat_type_id"],
                "mitre_techniques_final": agent2_result["mitre_techniques"],
            }

        except Exception as e:
            logger.exception(f"[Node] Agent 2 failed: {e}")
            return {
                "agent2_report": f"Ошибка генерации отчёта: {e}",
                "severity_level_id": 3,
                "threat_type_id": 11,
                "mitre_techniques_final": [],
            }

    # ===================================================================
    # YARA SCAN — Rule-based malware detection (STUB)
    # ===================================================================

    async def yara_scan_node(self, state: AnalysisState) -> dict:
        """Node: YARA scan — Rule-based malware detection.

        Reads: log_content
        Writes: yara_matches, yara_rules_matched, yara_context

        NOTE: Currently a stub. Will be replaced with real YARA engine.
        """
        logger.info("[Node] YARA scan: checking rules")
        start = time.time()

        if self.yara_engine is None:
            logger.warning("[Node] YARA scan: engine not configured, skipping")
            return {
                "yara_matches": [],
                "yara_rules_matched": [],
                "yara_context": "YARA проверка не настроена.",
            }

        try:
            # TODO: Implement real YARA scan
            # matches = self.yara_engine.scan(state["log_content"])
            matches = []

            yara_rules_matched = [m.get("rule", "") for m in matches]
            yara_context = self._format_yara_context(matches)

            logger.info(
                f"[Node] YARA scan complete: {len(matches)} matches in {time.time() - start:.1f}s"
            )
            return {
                "yara_matches": matches,
                "yara_rules_matched": yara_rules_matched,
                "yara_context": yara_context,
            }

        except Exception as e:
            logger.exception(f"[Node] YARA scan failed: {e}")
            return {
                "yara_matches": [],
                "yara_rules_matched": [],
                "yara_context": f"Ошибка YARA: {e}",
            }

    # ===================================================================
    # SIGMA SCAN — Rule-based SIEM detection (STUB)
    # ===================================================================

    async def sigma_scan_node(self, state: AnalysisState) -> dict:
        """Node: Sigma scan — Rule-based SIEM detection.

        Reads: log_content
        Writes: sigma_matches, sigma_rules_matched, sigma_context

        NOTE: Currently a stub. Will be replaced with real Sigma engine.
        """
        logger.info("[Node] Sigma scan: checking rules")
        start = time.time()

        if self.sigma_engine is None:
            logger.warning("[Node] Sigma scan: engine not configured, skipping")
            return {
                "sigma_matches": [],
                "sigma_rules_matched": [],
                "sigma_context": "Sigma проверка не настроена.",
            }

        try:
            # TODO: Implement real Sigma scan
            # matches = self.sigma_engine.scan(state["log_content"])
            matches = []

            sigma_rules_matched = [m.get("rule_id", "") for m in matches]
            sigma_context = self._format_sigma_context(matches)

            logger.info(
                f"[Node] Sigma scan complete: {len(matches)} matches in {time.time() - start:.1f}s"
            )
            return {
                "sigma_matches": matches,
                "sigma_rules_matched": sigma_rules_matched,
                "sigma_context": sigma_context,
            }

        except Exception as e:
            logger.exception(f"[Node] Sigma scan failed: {e}")
            return {
                "sigma_matches": [],
                "sigma_rules_matched": [],
                "sigma_context": f"Ошибка Sigma: {e}",
            }

    # ===================================================================
    # AGENT 3 — Final summarization
    # ===================================================================

    async def agent3_node(self, state: AnalysisState) -> dict:
        """Node: Agent 3 — Final report summarization.

        Reads: All previous nodes' outputs
        Writes: final_report, recommendations, severity_level_id, threat_type_id,
                mitre_techniques, yara_rules, sigma_rules, events_found

        NOTE: Imports here to avoid circular dependency.
        """
        logger.info("[Node] Agent 3: Final summarization")
        start = time.time()

        try:
            from .agent3 import generate_final_report as generate_agent3_report

            agent3_result = await generate_agent3_report(
                llm=self.llm,
                primary_analysis=state["primary_analysis"],
                events_found=state.get("events_found", 0),
                mitre_context=state.get("mitre_context", ""),
                agent2_report=state.get("agent2_report", ""),
                severity_level_id=state.get("severity_level_id", 3),
                threat_type_id=state.get("threat_type_id", 11),
                mitre_techniques=state.get("mitre_techniques_final", []),
                yara_context=state.get("yara_context", "YARA проверка не проводилась."),
                yara_count=len(state.get("yara_matches", [])),
                sigma_context=state.get(
                    "sigma_context", "Sigma проверка не проводилась."
                ),
                sigma_count=len(state.get("sigma_matches", [])),
            )

            logger.info(
                f"[Node] Agent 3 complete: severity={agent3_result['severity_level_id']}, "
                f"threat={agent3_result['threat_type_id']} in {time.time() - start:.1f}s"
            )
            return {
                "final_report": agent3_result["final_report"],
                "recommendations": [],  # Extracted from report if needed
                "severity_level_id": agent3_result["severity_level_id"],
                "threat_type_id": agent3_result["threat_type_id"],
                "mitre_techniques_final": agent3_result["mitre_techniques"],
                "yara_rules_matched": agent3_result["yara_rules"],
                "sigma_rules_matched": agent3_result["sigma_rules"],
                "events_found": agent3_result["events_found"],
            }

        except Exception as e:
            logger.exception(f"[Node] Agent 3 failed: {e}")
            return {
                "final_report": f"Ошибка суммаризации: {e}",
                "recommendations": [],
                "severity_level_id": 3,
                "threat_type_id": 11,
                "mitre_techniques_final": [],
                "yara_rules_matched": [],
                "sigma_rules_matched": [],
                "events_found": 0,
            }

    # ===================================================================
    # Helpers
    # ===================================================================

    @staticmethod
    def _format_yara_context(matches: list[dict]) -> str:
        """Format YARA matches into readable text."""
        if not matches:
            return "Совпадений с YARA-правилами не обнаружено."

        lines = ["### Совпадения YARA:"]
        for i, m in enumerate(matches, 1):
            lines.append(
                f"{i}. **{m.get('rule', 'Unknown')}** — {m.get('description', '')}"
            )
            if m.get("meta"):
                lines.append(f"   Мета: {m['meta']}")
        return "\n".join(lines)

    @staticmethod
    def _format_sigma_context(matches: list[dict]) -> str:
        """Format Sigma matches into readable text."""
        if not matches:
            return "Совпадений с Sigma-правилами не обнаружено."

        lines = ["### Совпадения Sigma:"]
        for i, m in enumerate(matches, 1):
            lines.append(
                f"{i}. **{m.get('rule_id', 'Unknown')}** — {m.get('title', '')}"
            )
            if m.get("severity"):
                lines.append(f"   Серьёзность: {m['severity']}")
        return "\n".join(lines)
