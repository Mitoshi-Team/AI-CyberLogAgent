"""Integration module for AI Agent v2 with FastAPI app."""

import logging
from typing import Optional

from .gigachat_client import GigaChatClient
from .pipeline.analyzer import LogAnalysisPipeline
from .rag.chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


# Global pipeline instance (lazy initialization)
_pipeline: Optional[LogAnalysisPipeline] = None
_chroma_manager: Optional[ChromaManager] = None


def get_pipeline() -> LogAnalysisPipeline:
    """
    Get or create global LogAnalysisPipeline instance.
    
    Returns:
        Initialized LogAnalysisPipeline
    """
    global _pipeline, _chroma_manager
    
    if _pipeline is not None:
        return _pipeline
    
    try:
        # Initialize GigaChat client
        gigachat_client = GigaChatClient(
            temperature=0.1,
            max_tokens=4000,
            timeout=90,
            max_retries=3,
            rate_limit_delay=0.5,
        )
        
        # Try to initialize ChromaDB for RAG
        _chroma_manager = ChromaManager(
            embedding_model="sentence-transformers/rubert-base-cased",
        )
        
        rag_available = _chroma_manager.initialize()
        
        if not rag_available:
            logger.warning("RAG not available, will use LLM-only mode")
        
        # Create pipeline
        _pipeline = LogAnalysisPipeline(
            gigachat_client=gigachat_client,
            chroma_manager=_chroma_manager if rag_available else None,
            rag_top_k=5,
            use_rag=rag_available,
        )
        
        logger.info("AI Agent v2 pipeline initialized successfully")
        return _pipeline
        
    except Exception as e:
        logger.error(f"Failed to initialize AI Agent v2 pipeline: {e}")
        
        # Fallback: create pipeline without RAG
        gigachat_client = GigaChatClient()
        _pipeline = LogAnalysisPipeline(
            gigachat_client=gigachat_client,
            chroma_manager=None,
            use_rag=False,
        )
        
        logger.warning("AI Agent v2 pipeline created in fallback mode (no RAG)")
        return _pipeline


async def analyze_log_v2(log_content: str) -> dict:
    """
    Analyze log file using AI Agent v2 pipeline.
    
    Args:
        log_content: Raw log file content
        
    Returns:
        Dictionary with analysis results compatible with existing API:
        - description: Report text
        - severity_level_id: 1-4
        - threat_type_id: 1-11
    """
    pipeline = get_pipeline()
    
    # Run analysis
    result = await pipeline.analyze_log(log_content)
    
    if result.success and result.final_result:
        logger.info(
            f"AI Agent v2 analysis complete: "
            f"severity={result.final_result.severity_level_id}, "
            f"threat={result.final_result.threat_type_id}, "
            f"time={result.total_processing_time_ms:.0f}ms"
        )
        
        return {
            "description": result.final_result.report_text,
            "severity_level_id": result.final_result.severity_level_id,
            "threat_type_id": result.final_result.threat_type_id,
            "mitre_techniques": result.final_result.mitre_techniques,
            "processing_time_ms": result.total_processing_time_ms,
        }
    else:
        # Return error result
        error_msg = result.final_result.error_message if result.final_result else "Unknown error"
        logger.error(f"AI Agent v2 analysis failed: {error_msg}")
        
        return {
            "description": f"⚠️ Ошибка анализа: {error_msg}",
            "severity_level_id": 3,
            "threat_type_id": 11,
            "error": error_msg,
        }


async def close_pipeline():
    """Close pipeline resources."""
    global _pipeline, _chroma_manager
    
    if _pipeline and _pipeline.gigachat_client:
        await _pipeline.gigachat_client.close()
    
    _pipeline = None
    _chroma_manager = None
    logger.info("AI Agent v2 pipeline closed")
