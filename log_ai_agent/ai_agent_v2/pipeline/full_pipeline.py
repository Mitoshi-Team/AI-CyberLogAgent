"""Full analysis pipeline using LangChain RunnableSequence."""

import logging
import time
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseLanguageModel
from langchain_core.runnables import RunnableConfig

from ..chains.agent1 import create_agent1_chain
from ..chains.agent2 import generate_final_report
from ..chains.llm import create_gigachat_llm
from ..chains.rag_chain import retrieve_mitre_context
from ..knowledge_base.manager import ChromaDBManager
from ..knowledge_base.mitre_loader import initialize_mitre_knowledge_base

logger = logging.getLogger(__name__)


class LogAnalysisPipeline:
    """Complete log analysis pipeline using LangChain.

    Flow:
    1. Agent 1: Primary log analysis
    2. RAG: Retrieve MITRE ATT&CK techniques
    3. Agent 2: Generate final report with metadata

    Usage:
        pipeline = LogAnalysisPipeline(chroma_mgr, llm)
        result = await pipeline.analyze(log_content)
    """

    def __init__(
        self,
        chroma_mgr: ChromaDBManager | None,
        llm: BaseLanguageModel | None = None,
        use_rag: bool = True,
        rag_top_k: int = 5,
    ):
        """Initialize pipeline.

        Args:
            chroma_mgr: ChromaDB manager (can be None if use_rag=False)
            llm: Language model (creates default GigaChat if None)
            use_rag: Whether to use RAG
            rag_top_k: Number of techniques to retrieve

        """
        self.chroma_mgr = chroma_mgr
        self.use_rag = use_rag and chroma_mgr is not None
        self.rag_top_k = rag_top_k

        # Create or use provided LLM
        self.llm = llm or create_gigachat_llm()

        # Create Agent 1 chain
        self.agent1_chain = create_agent1_chain(self.llm)

        logger.info(f"LogAnalysisPipeline initialized, RAG={self.use_rag}")

    async def analyze(
        self,
        log_content: str,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        """Analyze log content through full pipeline.

        Args:
            log_content: Raw log content
            config: Optional LangChain config (callbacks, etc.)

        Returns:
            Dictionary with all results

        """
        start_time = time.time()
        results = {
            "log_size": len(log_content),
            "stages": {},
        }

        try:
            # Step 1: Agent 1 - Primary analysis
            logger.info("Step 1: Primary log analysis (Agent 1)")
            primary_analysis = await self.agent1_chain.ainvoke(
                {"log_content": log_content},
                config=config,
            )
            events_found = primary_analysis.count("### Событие")

            results["stages"]["agent1"] = {
                "success": True,
                "primary_analysis": primary_analysis,
                "events_found": events_found,
            }
            logger.info(f"✓ Agent 1 complete: found {events_found} events")

            # Step 2: RAG - Retrieve MITRE context
            if self.use_rag and self.chroma_mgr:
                logger.info("Step 2: RAG - Retrieving MITRE ATT&CK techniques")
                rag_result = await retrieve_mitre_context(
                    llm=self.llm,
                    chroma_mgr=self.chroma_mgr,
                    primary_analysis=primary_analysis,
                    k=self.rag_top_k,
                )

                results["stages"]["rag"] = {
                    "success": True,
                    "mitre_context": rag_result["mitre_context"],
                    "techniques_count": len(rag_result["mitre_techniques"]),
                    "technique_ids": rag_result["technique_ids"],
                }
                logger.info(
                    f"✓ RAG complete: found {len(rag_result['mitre_techniques'])} techniques"
                )
            else:
                logger.info("Step 2: RAG skipped (disabled or unavailable)")
                results["stages"]["rag"] = {
                    "success": False,
                    "mitre_context": "RAG not available",
                    "techniques_count": 0,
                }

            # Step 3: Agent 2 - Final report
            logger.info("Step 3: Final report generation (Agent 2)")
            agent2_result = await generate_final_report(
                llm=self.llm,
                primary_analysis=primary_analysis,
                mitre_context=results["stages"]["rag"]["mitre_context"],
            )

            final_report = agent2_result["final_report"]

            results["stages"]["agent2"] = {
                "success": True,
                "final_report": final_report,
                "severity_level_id": agent2_result["severity_level_id"],
                "threat_type_id": agent2_result["threat_type_id"],
                "mitre_techniques": agent2_result["mitre_techniques"],
            }
            logger.info(
                f"✓ Agent 2 complete: severity={agent2_result['severity_level_id']}, threat={agent2_result['threat_type_id']}"
            )

            # Summary
            results["success"] = True
            results["total_time_sec"] = time.time() - start_time

            logger.info(f"✓ Pipeline complete in {results['total_time_sec']:.1f}s")

        except Exception as e:
            error_details = str(e) or f"{type(e).__name__}: {e!r}"
            logger.exception("Pipeline error: %s", error_details)
            results["success"] = False
            results["error"] = error_details
            results["total_time_sec"] = time.time() - start_time

        return results


async def create_pipeline(
    chroma_path: str | None = None,
    use_rag: bool = True,
    llm_config: dict | None = None,
) -> LogAnalysisPipeline:
    """Create and initialize analysis pipeline.

    Convenience function to create pipeline with proper initialization.

    Args:
        chroma_path: Path to ChromaDB (auto-creates if needed)
        use_rag: Whether to use RAG
        llm_config: Optional LLM configuration

    Returns:
        Initialized LogAnalysisPipeline

    """
    logger.info("Creating analysis pipeline...")

    # Initialize ChromaDB if using RAG
    chroma_mgr = None
    if use_rag:
        if chroma_path is None:
            chroma_path = str(Path(__file__).parent.parent / "chroma_db")

        logger.info(f"Initializing ChromaDB at {chroma_path}")
        chroma_mgr = initialize_mitre_knowledge_base(
            persist_directory=chroma_path,
        )

    # Create LLM
    llm_kwargs = llm_config or {}
    llm = create_gigachat_llm(**llm_kwargs)

    # Create pipeline
    pipeline = LogAnalysisPipeline(
        chroma_mgr=chroma_mgr,
        llm=llm,
        use_rag=use_rag,
    )

    logger.info("✓ Pipeline created successfully")
    return pipeline
