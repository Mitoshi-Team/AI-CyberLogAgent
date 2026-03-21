"""Log analysis pipeline: Agent1 → RAG → Agent2."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from ..gigachat_client import GigaChatClient
from ..rag.retriever import MitreRAGRetriever
from ..rag.chroma_manager import ChromaManager
from ..prompts.system import PRIMARY_ANALYSIS_SYSTEM_PROMPT, FINAL_REPORT_SYSTEM_PROMPT
from ..prompts.log_analysis import PRIMARY_ANALYSIS_USER_PROMPT, FINAL_REPORT_USER_PROMPT
from ..models.schemas import (
    PrimaryAnalysisResult,
    MITREResult,
    FinalAnalysisResult,
    FullPipelineResult,
)

logger = logging.getLogger(__name__)


class LogAnalysisPipeline:
    """
    Complete log analysis pipeline with 2 agents and RAG.
    
    Flow:
    1. Agent 1: Analyze raw logs → Primary analysis report
    2. RAG: Search MITRE ATT&CK → Relevant techniques context
    3. Agent 2: Combine analysis + MITRE → Final report with metadata
    """

    def __init__(
        self,
        gigachat_client: GigaChatClient,
        chroma_manager: Optional[ChromaManager] = None,
        rag_top_k: int = 5,
        use_rag: bool = True,
    ):
        """
        Initialize analysis pipeline.
        
        Args:
            gigachat_client: GigaChat API client
            chroma_manager: Optional ChromaDB manager for RAG
            rag_top_k: Number of MITRE techniques to retrieve
            use_rag: Whether to use RAG (can be disabled for fallback)
        """
        self.gigachat_client = gigachat_client
        self.chroma_manager = chroma_manager
        self.use_rag = use_rag and chroma_manager is not None
        
        # Initialize RAG retriever if available
        if self.use_rag:
            self.rag_retriever = MitreRAGRetriever(
                chroma_manager=chroma_manager,
                gigachat_client=gigachat_client,
                top_k=rag_top_k,
            )
        else:
            self.rag_retriever = None
        
        logger.info(f"LogAnalysisPipeline initialized, RAG: {self.use_rag}")

    async def analyze_log(
        self,
        log_content: str,
        timeout_seconds: int = 120,
    ) -> FullPipelineResult:
        """
        Analyze log file through complete pipeline.
        
        Args:
            log_content: Raw log file content
            timeout_seconds: Total pipeline timeout
            
        Returns:
            FullPipelineResult with all stages
        """
        start_time = time.time()
        
        try:
            # Stage 1: Primary analysis (Agent 1)
            primary_result = await self._primary_analysis(log_content)
            
            if not primary_result.success:
                return FullPipelineResult(
                    success=False,
                    primary_analysis=primary_result,
                    log_size_bytes=len(log_content),
                    total_processing_time_ms=(time.time() - start_time) * 1000,
                )
            
            # Stage 2: RAG - MITRE search
            mitre_result = await self._rag_search(primary_result.analysis_text)
            
            # Stage 3: Final report (Agent 2)
            final_result = await self._final_report(
                primary_result.analysis_text,
                mitre_result.context_text if mitre_result else "",
            )
            
            total_time = (time.time() - start_time) * 1000
            
            return FullPipelineResult(
                success=final_result.success,
                primary_analysis=primary_result,
                mitre_result=mitre_result,
                final_result=final_result,
                total_processing_time_ms=total_time,
                log_size_bytes=len(log_content),
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Pipeline timeout after {timeout_seconds}s")
            return FullPipelineResult(
                success=False,
                primary_analysis=None,
                mitre_result=None,
                final_result=FinalAnalysisResult(
                    success=False,
                    report_text="⚠️ Превышено время анализа. Попробуйте загрузить файл меньшего размера.",
                    severity_level_id=3,
                    threat_type_id=11,
                    error_message=f"Timeout after {timeout_seconds}s",
                ),
                total_processing_time_ms=(time.time() - start_time) * 1000,
                log_size_bytes=len(log_content),
            )
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return FullPipelineResult(
                success=False,
                primary_analysis=None,
                mitre_result=None,
                final_result=FinalAnalysisResult(
                    success=False,
                    report_text=f"⚠️ Ошибка анализа: {str(e)}",
                    severity_level_id=3,
                    threat_type_id=11,
                    error_message=str(e),
                ),
                total_processing_time_ms=(time.time() - start_time) * 1000,
                log_size_bytes=len(log_content),
            )

    async def _primary_analysis(self, log_content: str) -> PrimaryAnalysisResult:
        """
        Agent 1: Analyze raw logs and create primary report.
        
        Args:
            log_content: Raw log content
            
        Returns:
            PrimaryAnalysisResult
        """
        start_time = time.time()
        
        try:
            # Truncate if too large (keep last 50KB for analysis)
            max_size = 50 * 1024
            if len(log_content) > max_size:
                log_content = log_content[-max_size:]
                logger.info(f"Truncated log to last {max_size} bytes")
            
            # Build prompt
            user_prompt = PRIMARY_ANALYSIS_USER_PROMPT.format(
                log_content=log_content
            )
            
            # Call Agent 1
            response = await self.gigachat_client.chat(
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system_prompt=PRIMARY_ANALYSIS_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=3000,
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Count events (simple heuristic: count "### Событие" headers)
            events_found = response.count("### Событие")
            
            logger.info(f"Agent 1 completed in {processing_time:.0f}ms, found {events_found} events")
            
            return PrimaryAnalysisResult(
                success=True,
                analysis_text=response,
                events_found=events_found,
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"Agent 1 error: {e}")
            return PrimaryAnalysisResult(
                success=False,
                analysis_text="",
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def _rag_search(self, primary_analysis: str) -> MITREResult:
        """
        Stage 2: Search MITRE ATT&CK knowledge base.
        
        Args:
            primary_analysis: Primary analysis report from Agent 1
            
        Returns:
            MITREResult
        """
        start_time = time.time()
        
        if not self.use_rag or not self.rag_retriever:
            logger.info("RAG disabled, skipping MITRE search")
            return MITREResult(
                success=False,
                techniques=[],
                context_text="RAG отключен.",
                processing_time_ms=0,
            )
        
        try:
            # Retrieve and format MITRE context
            context = await self.rag_retriever.retrieve_and_format(
                query=primary_analysis,
                use_llm_enhancement=True,
            )
            
            # Get raw results for metadata
            results = await self.rag_retriever.retrieve(
                query=primary_analysis,
                use_llm_enhancement=False,
            )
            
            techniques = [
                {
                    "id": r.get("metadata", {}).get("technique_id", ""),
                    "name": r.get("metadata", {}).get("technique_name", ""),
                    "tactic": r.get("metadata", {}).get("tactic", ""),
                }
                for r in results
            ]
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(f"RAG completed in {processing_time:.0f}ms, found {len(techniques)} techniques")
            
            return MITREResult(
                success=True,
                techniques=techniques,
                context_text=context,
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"RAG error: {e}")
            return MITREResult(
                success=False,
                techniques=[],
                context_text=f"Ошибка RAG: {str(e)}",
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def _final_report(
        self, 
        primary_analysis: str, 
        mitre_context: str,
    ) -> FinalAnalysisResult:
        """
        Agent 2: Generate final report with metadata.
        
        Args:
            primary_analysis: Primary analysis from Agent 1
            mitre_context: MITRE context from RAG
            
        Returns:
            FinalAnalysisResult with parsed metadata
        """
        start_time = time.time()
        
        try:
            # Build prompt
            user_prompt = FINAL_REPORT_USER_PROMPT.format(
                primary_analysis=primary_analysis,
                mitre_context=mitre_context,
            )
            
            # Call Agent 2
            response = await self.gigachat_client.chat(
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system_prompt=FINAL_REPORT_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=4000,
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Parse metadata from response
            severity_id, threat_id, mitre_techniques = self._parse_metadata(response)
            
            logger.info(f"Agent 2 completed in {processing_time:.0f}ms, severity={severity_id}, threat={threat_id}")
            
            return FinalAnalysisResult(
                success=True,
                report_text=response,
                severity_level_id=severity_id,
                threat_type_id=threat_id,
                mitre_techniques=mitre_techniques,
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"Agent 2 error: {e}")
            return FinalAnalysisResult(
                success=False,
                report_text=f"⚠️ Ошибка генерации отчёта: {str(e)}",
                severity_level_id=3,
                threat_type_id=11,
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _parse_metadata(self, response: str) -> tuple[int, int, list[str]]:
        """
        Parse metadata from Agent 2 response.
        
        Args:
            response: Full response text from Agent 2
            
        Returns:
            Tuple of (severity_level_id, threat_type_id, mitre_techniques)
        """
        severity_id = 3  # Default: Medium
        threat_id = 11   # Default: Other
        mitre_techniques = []
        
        try:
            # Look for ---META--- block
            if "---META---" in response:
                meta_start = response.index("---META---")
                meta_end = response.index("---END---", meta_start)
                meta_section = response[meta_start + 10:meta_end].strip()
                
                for line in meta_section.split("\n"):
                    line = line.strip()
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == "severity_level_id":
                            try:
                                severity_id = int(value)
                                if severity_id < 1 or severity_id > 4:
                                    severity_id = 3
                            except ValueError:
                                pass
                        
                        elif key == "threat_type_id":
                            try:
                                threat_id = int(value)
                                if threat_id < 1 or threat_id > 11:
                                    threat_id = 11
                            except ValueError:
                                pass
                        
                        elif key == "mitre_techniques":
                            # Parse JSON-like array
                            try:
                                # Simple parsing: extract quoted strings
                                import re
                                mitre_techniques = re.findall(r'"([^"]+)"', value)
                            except Exception:
                                pass
                
                logger.info(f"Parsed metadata: severity={severity_id}, threat={threat_id}, mitre={mitre_techniques}")
            
        except Exception as e:
            logger.warning(f"Failed to parse metadata: {e}")
        
        return severity_id, threat_id, mitre_techniques
