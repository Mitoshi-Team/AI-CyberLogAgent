"""LangGraph nodes for the analysis pipeline.

This module defines all nodes used in the LangGraph StateGraph.
Each node takes AnalysisState as input and returns a partial state update.
"""

import asyncio
import logging
import time

from langchain_core.language_models import BaseLanguageModel

from ..engines.sigma_engine import SigmaEngine
from ..engines.yara_engine import YaraEngine
from ..knowledge_base.manager import ChromaDBManager
from ..models_types import AnalysisState, MITRETechnique, SuspiciousEvent
from ..parsers.apache_parser import ApacheLogParser
from .agent1 import analyze_logs_primary, create_agent1_chain
from .prefilter import prefilter_logs
from .rag_chain import rag_search_single_event

logger = logging.getLogger(__name__)


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
        yara_engine: YaraEngine | None = None,
        sigma_engine: SigmaEngine | None = None,
        use_rag: bool = True,
        rag_top_k: int = 5,
        rag_score_threshold: float = 0.7,
        rag_parallelism: int = 5,
    ):
        self.llm = llm
        self.chroma_mgr = chroma_mgr
        self.yara_engine = yara_engine
        self.sigma_engine = sigma_engine
        self.use_rag = use_rag and chroma_mgr is not None
        self.rag_top_k = rag_top_k
        self.rag_score_threshold = rag_score_threshold

        self._agent1_chain = create_agent1_chain(llm)
        self._rag_semaphore = asyncio.Semaphore(rag_parallelism)

    async def prefilter_node(self, state: AnalysisState) -> dict:
        """Node: Pre-filter logs to reduce volume before expensive processing.

        Reads: log_content
        Writes: log_content (filtered), prefilter_stats
        """
        logger.info("[Node] Pre-filter: lightweight log filtering")
        start = time.time()

        try:
            log_content = state["log_content"]

            # Apply lightweight pre-filtering
            filtered_content, stats = prefilter_logs(log_content)

            logger.info(
                f"[Node] Pre-filter complete: {stats['kept_lines']}/{stats['original_lines']} "
                f"lines kept ({stats['filter_ratio']:.1%}) in {time.time() - start:.1f}s"
            )

            return {
                "log_content": filtered_content,
                "prefilter_stats": stats,
            }

        except Exception as e:
            logger.exception(f"[Node] Pre-filter failed: {e}")
            # Return original content on error to avoid breaking pipeline
            return {
                "log_content": state["log_content"],
                "prefilter_stats": {"error": str(e)},
            }

    async def agent1_node(self, state: AnalysisState) -> dict:
        """Node: Agent 1 — Primary log analysis.

        Reads: log_content
        Writes: primary_analysis, mini_report, suspicious_events, events_found
        """
        logger.info("[Node] Agent 1: Primary log analysis")
        start = time.time()

        try:
            result = await analyze_logs_primary(
                llm=self.llm,
                log_content=state["log_content"],
            )

            logger.info(
                f"[Node] Agent 1 complete: {result['events_found']} events "
                f"in {time.time() - start:.1f}s"
            )
            return {
                "primary_analysis": result["primary_analysis"],
                "mini_report": result["mini_report"],
                "suspicious_events": result["suspicious_events"],
                "events_found": result["events_found"],
            }

        except Exception as e:
            logger.exception(f"[Node] Agent 1 failed: {e}")
            return {
                "primary_analysis": f"Error: {e}",
                "mini_report": "Analysis failed",
                "suspicious_events": [],
                "events_found": 0,
            }

    async def parse_logs_node(self, state: AnalysisState) -> dict:
        """Node: Parse logs — Parse raw log content for YARA/Sigma scanning.

        Reads: log_content
        Writes: parsed_logs
        """
        logger.info("[Node] Parse logs: parsing log content")
        start = time.time()

        try:
            parser = ApacheLogParser()
            parsed_logs = parser.parse(state["log_content"])

            logger.info(
                f"[Node] Parse logs complete: {len(parsed_logs)} entries parsed "
                f"in {time.time() - start:.1f}s"
            )
            return {
                "parsed_logs": parsed_logs,
            }

        except Exception as e:
            logger.exception(f"[Node] Parse logs failed: {e}")
            return {
                "parsed_logs": [],
            }

    async def agent2_node(self, state: AnalysisState) -> dict:
        """Node: Agent 2 — RAG search for each suspicious event + final report.

        This node:
        1. Loops through suspicious_events from Agent1
        2. For each event, does RAG search (without timestamp)
        3. Accumulates matched MITRE techniques
        4. Generates final report with all data

        Reads: primary_analysis, suspicious_events, mitre_context
        Writes: mitre_context, mitre_techniques_final, agent2_report
        """
        logger.info("[Node] Agent 2: RAG search + report generation")
        start = time.time()

        suspicious_events = state.get("suspicious_events", [])

        if not self.use_rag or not self.chroma_mgr:
            logger.warning("[Node] Agent 2: RAG disabled or unavailable")
            return {
                "mitre_context": "RAG (MITRE ATT&CK) is disabled.",
                "mitre_techniques_final": [],
                "technique_ids": [],
            }

        logger.info(
            f"[Node] Agent 2: Processing {len(suspicious_events)} events in parallel"
        )

        async def process_event(
            i: int, event: SuspiciousEvent
        ) -> tuple[int, MITRETechnique | None]:
            description = event.get("description", "")

            if not description:
                return i, None

            async with self._rag_semaphore:
                try:
                    rag_result = await rag_search_single_event(
                        llm=self.llm,
                        chroma_mgr=self.chroma_mgr,
                        description=description,
                        k=self.rag_top_k,
                        score_threshold=self.rag_score_threshold,
                    )

                    if rag_result.get("has_match"):
                        technique: MITRETechnique = {
                            "technique_id": rag_result.get("technique_id", ""),
                            "name": rag_result.get("name", ""),
                            "timestamp": event.get("timestamp"),
                            "event": description,
                            "log_line": event.get("log_line", ""),
                        }
                        logger.info(
                            f"[Node] Agent 2: Event {i + 1}/{len(suspicious_events)} "
                            f"matched {technique['technique_id']}"
                        )
                        return i, technique
                    else:
                        logger.debug(
                            f"[Node] Agent 2: Event {i + 1}/{len(suspicious_events)} "
                            f"no MITRE match"
                        )
                        return i, None

                except Exception as e:
                    logger.warning(
                        f"[Node] Agent 2: RAG search failed for event {i}: {e}"
                    )
                    return i, None

        tasks = [process_event(i, event) for i, event in enumerate(suspicious_events)]
        results = await asyncio.gather(*tasks)

        mitre_techniques_final: list[MITRETechnique] = []
        mitre_context_parts: list[str] = []

        for i, technique in sorted(results, key=lambda x: x[0]):
            if technique:
                mitre_techniques_final.append(technique)
                mitre_context_parts.append(
                    f"- {technique['technique_id']} ({technique['name']}): "
                    f"{technique['event']} at {technique.get('timestamp', 'N/A')}"
                )

        mitre_context = (
            "Found MITRE techniques:\n" + "\n".join(mitre_context_parts)
            if mitre_context_parts
            else "No MITRE techniques found for suspicious events."
        )

        technique_ids = [
            t["technique_id"] for t in mitre_techniques_final if t.get("technique_id")
        ]
        logger.info(
            f"[Node] Agent 2 RAG complete: {len(mitre_techniques_final)} techniques "
            f"from {len(suspicious_events)} events in {time.time() - start:.1f}s"
        )

        return {
            "mitre_context": mitre_context,
            "mitre_techniques_final": mitre_techniques_final,
            "technique_ids": technique_ids,
        }

    async def yara_scan_node(self, state: AnalysisState) -> dict:
        """Node: YARA scan — Rule-based malware detection.

        Reads: parsed_logs
        Writes: yara_matches, yara_rules_matched, yara_context
        """
        logger.info("[Node] YARA scan: checking rules")
        start = time.time()

        if self.yara_engine is None:
            logger.warning("[Node] YARA scan: engine not configured, skipping")
            return {
                "yara_matches": [],
                "yara_rules_matched": [],
                "yara_context": "YARA check not configured.",
            }

        try:
            parsed_logs = state.get("parsed_logs", [])
            matches = self.yara_engine.scan(parsed_logs)

            yara_rules_matched = list(
                {m.get("rule", "") for m in matches if m.get("rule")}
            )
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
                "yara_context": f"YARA error: {e}",
            }

    async def sigma_scan_node(self, state: AnalysisState) -> dict:
        """Node: Sigma scan — Rule-based SIEM detection.

        Reads: parsed_logs
        Writes: sigma_matches, sigma_rules_matched, sigma_context
        """
        logger.info("[Node] Sigma scan: checking rules")
        start = time.time()

        if self.sigma_engine is None:
            logger.warning("[Node] Sigma scan: engine not configured, skipping")
            return {
                "sigma_matches": [],
                "sigma_rules_matched": [],
                "sigma_context": "Sigma check not configured.",
            }

        try:
            parsed_logs = state.get("parsed_logs", [])
            matches = self.sigma_engine.scan(parsed_logs)

            sigma_rules_matched = list(
                {m.get("rule_id", "") for m in matches if m.get("rule_id")}
            )
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
                "sigma_context": f"Sigma error: {e}",
            }

    async def agent3_node(self, state: AnalysisState) -> dict:
        """Node: Agent 3 — Final report summarization.

        Reads: All previous nodes' outputs
        Writes: final_report, recommendations, severity_level_id, threat_type_id
        """
        logger.info("[Node] Agent 3: Final summarization")
        start = time.time()

        try:
            from .agent3 import generate_final_report as generate_agent3_report

            mitre_techniques = state.get("mitre_techniques_final", [])

            mitre_techniques_str = (
                ", ".join(
                    [
                        f"{t['technique_id']} ({t['name']})"
                        for t in mitre_techniques
                        if t.get("technique_id")
                    ]
                )
                or "No MITRE techniques found"
            )

            agent3_result = await generate_agent3_report(
                llm=self.llm,
                primary_analysis=state.get("primary_analysis", ""),
                mini_report=state.get("mini_report", ""),
                events_found=state.get("events_found", 0),
                mitre_context=state.get("mitre_context", ""),
                agent2_report=state.get("agent2_report", ""),
                severity_level_id=state.get("severity_level_id", 3),
                threat_type_id=state.get("threat_type_id", 11),
                mitre_techniques=mitre_techniques,
                yara_context=state.get("yara_context", "YARA check not performed."),
                yara_count=len(state.get("yara_matches", [])),
                sigma_context=state.get("sigma_context", "Sigma check not performed."),
                sigma_count=len(state.get("sigma_matches", [])),
            )

            logger.info(
                f"[Node] Agent 3 complete: severity={agent3_result.get('severity_level_id', 3)}, "
                f"threat={agent3_result.get('threat_type_id', 11)} in {time.time() - start:.1f}s"
            )
            return {
                "final_report": agent3_result.get("final_report", ""),
                "recommendations": [],
                "severity_level_id": agent3_result.get("severity_level_id", 3),
                "threat_type_id": agent3_result.get("threat_type_id", 11),
                "yara_rules_matched": agent3_result.get("yara_rules", []),
                "sigma_rules_matched": agent3_result.get("sigma_rules", []),
                "events_found": agent3_result.get("events_found", 0),
                "confidence_level": agent3_result.get("confidence_level", "medium"),
                "unconfirmed_events_count": agent3_result.get("unconfirmed_events_count", 0),
            }

        except Exception as e:
            logger.exception(f"[Node] Agent 3 failed: {e}")
            return {
                "final_report": f"Error: {e}",
                "recommendations": [],
                "severity_level_id": 3,
                "threat_type_id": 11,
                "yara_rules_matched": [],
                "sigma_rules_matched": [],
                "events_found": 0,
            }

    @staticmethod
    def _format_yara_context(matches: list[dict]) -> str:
        """Format YARA matches into readable text."""
        if not matches:
            return "No YARA rule matches found."

        lines = ["### YARA Matches:"]
        for i, m in enumerate(matches, 1):
            lines.append(
                f"{i}. **{m.get('rule', 'Unknown')}** — {m.get('description', '')}"
            )
            if m.get("matched_strings"):
                lines.append(f"   Matched: {', '.join(m['matched_strings'][:3])}")
        return "\n".join(lines)

    @staticmethod
    def _format_sigma_context(matches: list[dict]) -> str:
        """Format Sigma matches into readable text."""
        if not matches:
            return "No Sigma rule matches found."

        lines = ["### Sigma Matches:"]
        for i, m in enumerate(matches, 1):
            lines.append(
                f"{i}. **{m.get('title', 'Unknown')}** — {m.get('description', '')}"
            )
            if m.get("severity"):
                lines.append(f"   Severity: {m['severity']}")
        return "\n".join(lines)
