"""Wrapper for AI Agent v2 integration with app.py."""

import logging

from .callbacks import get_callback_config
from .pipeline.full_pipeline import LogAnalysisPipeline, create_pipeline

logger = logging.getLogger(__name__)

# Global pipeline instance
_pipeline: LogAnalysisPipeline | None = None


async def get_pipeline() -> LogAnalysisPipeline:
    """Get or create global pipeline instance."""
    global _pipeline

    if _pipeline is None:
        logger.info("Creating AI Agent v2 pipeline...")
        _pipeline = await create_pipeline(
            use_rag=True,
        )
        logger.info("✓ AI Agent v2 pipeline created")

    return _pipeline


async def analyze_log_v2(log_content: str) -> dict:
    """Analyze log using AI Agent v2.

    Args:
        log_content: Raw log content

    Returns:
        Dictionary with:
        - description: Report text
        - severity_level_id: 1-4
        - threat_type_id: 1-11
        - mitre_techniques: List of technique IDs

    """
    pipeline = await get_pipeline()

    results = await pipeline.analyze(
        log_content=log_content,
        config=get_callback_config(show_output=False),
    )

    if results.get("success") and "agent2" in results.get("stages", {}):
        agent2 = results["stages"]["agent2"]

        return {
            "description": agent2.get("final_report", ""),
            "severity_level_id": agent2.get("severity_level_id", 3),
            "threat_type_id": agent2.get("threat_type_id", 11),
            "mitre_techniques": agent2.get("mitre_techniques", []),
            "processing_time_ms": results.get("total_time_sec", 0) * 1000,
        }
    else:
        # Return error result
        error_msg = results.get("error", "Unknown error")
        logger.error(f"AI Agent v2 analysis failed: {error_msg}")

        return {
            "description": f"⚠️ Ошибка анализа: {error_msg}",
            "severity_level_id": 3,
            "threat_type_id": 11,
            "mitre_techniques": [],
            "error": error_msg,
        }


async def close_pipeline():
    """Close pipeline resources (no-op for now)."""
    global _pipeline
    _pipeline = None
    logger.info("AI Agent v2 pipeline closed")
