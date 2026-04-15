"""Wrapper for AI Agent v2 integration with app.py."""

import asyncio
import logging
import os
from pathlib import Path

from .callbacks import get_callback_config
from .config import AgentConfig
from .pipeline import LogAnalysisPipeline, create_pipeline

logger = logging.getLogger(__name__)

# Global pipeline instance
_pipeline: LogAnalysisPipeline | None = None
_analyze_lock = asyncio.Lock()
_MAX_ANALYSIS_LOG_CHARS = int(os.getenv("AI_V2_MAX_ANALYSIS_LOG_CHARS", "25000"))
_agent_config: AgentConfig | None = None


def _resolve_rules_path(relative_path: str) -> str | None:
    """Resolve a rules path relative to the ai_agent_v2 package directory."""
    base = Path(__file__).parent
    full = (base / relative_path).resolve()
    if full.exists():
        return str(full)
    return None


def _is_rate_limited(error_msg: str) -> bool:
    """Check whether pipeline error indicates API rate limiting."""
    lowered = error_msg.lower()
    return "429" in lowered or "too many requests" in lowered


def _prepare_log_for_analysis(log_content: str) -> str:
    """Trim oversized logs before sending to LLM to reduce TPM/RPM rate-limit hits."""
    if len(log_content) <= _MAX_ANALYSIS_LOG_CHARS:
        return log_content

    head_size = _MAX_ANALYSIS_LOG_CHARS // 2
    tail_size = _MAX_ANALYSIS_LOG_CHARS - head_size
    logger.warning(
        "Input log is too large for analysis (%s chars), trimming to %s chars",
        len(log_content),
        _MAX_ANALYSIS_LOG_CHARS,
    )
    return (
        log_content[:head_size]
        + "\n\n[... LOG TRIMMED FOR RATE-LIMIT SAFETY ...]\n\n"
        + log_content[-tail_size:]
    )


async def get_pipeline() -> LogAnalysisPipeline:
    """Get or create global pipeline instance."""
    global _pipeline, _agent_config

    if _pipeline is None:
        _agent_config = AgentConfig.from_env()
        provider = _agent_config.detected_provider
        logger.info("Creating AI Agent v2 pipeline...")

        # Resolve YARA and Sigma rules paths
        yara_rules = _resolve_rules_path("rules/yara")
        sigma_rules = _resolve_rules_path("rules/sigma")

        _pipeline = await create_pipeline(
            chroma_path=_agent_config.chroma_path,
            use_rag=_agent_config.use_rag,
            llm_config={
                "temperature": _agent_config.temperature,
                "max_tokens": _agent_config.max_tokens,
                "timeout": _agent_config.timeout,
            },
            yara_rules_path=yara_rules,
            sigma_rules_path=sigma_rules,
        )
        logger.info(
            "AI Agent v2 backend config: provider=%s timeout=%ss temp=%s max_tokens=%s use_rag=%s rag_top_k=%s yara=%s sigma=%s",
            provider.value,
            _agent_config.timeout,
            _agent_config.temperature,
            _agent_config.max_tokens,
            _agent_config.use_rag,
            _agent_config.rag_top_k,
            yara_rules is not None,
            sigma_rules is not None,
        )
        logger.info("✓ AI Agent v2 pipeline created")

    return _pipeline


async def warmup_pipeline() -> None:
    """Warm up AI Agent v2 pipeline during app startup."""
    await get_pipeline()


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
        - events_found: Number of events detected by Agent 1

    """
    pipeline = await get_pipeline()
    prepared_log_content = _prepare_log_for_analysis(log_content)

    # GigaChat can return HTTP 429 under burst traffic.
    # Retry with exponential backoff and serialize analysis calls.
    max_attempts = 3
    backoff_seconds = [0, 2, 5]

    results: dict = {}
    async with _analyze_lock:
        for attempt in range(max_attempts):
            if attempt > 0:
                await asyncio.sleep(backoff_seconds[attempt])

            results = await pipeline.analyze(
                log_content=prepared_log_content,
                config=get_callback_config(show_output=False),
            )

            error_msg = str(results.get("error") or "")
            if results.get("success") or not _is_rate_limited(error_msg):
                break

            logger.warning(
                "Rate limit from GigaChat (attempt %s/%s), retrying in %ss",
                attempt + 1,
                max_attempts,
                backoff_seconds[attempt + 1] if attempt + 1 < max_attempts else 0,
            )

    if results.get("success") and "agent3" in results.get("stages", {}):
        agent1 = results["stages"].get("agent1", {})
        agent3 = results["stages"]["agent3"]

        return {
            "description": agent3.get("final_report", ""),
            "severity_level_id": agent3.get("severity_level_id", 3),
            "threat_type_id": agent3.get("threat_type_id", 11),
            "mitre_techniques": agent3.get("mitre_techniques", []),
            "events_found": agent1.get("events_found", 0),
            "processing_time_ms": results.get("total_time_sec", 0) * 1000,
        }
    else:
        # Return error result
        error_msg = results.get("error") or "Unknown error"
        logger.error(f"AI Agent v2 analysis failed: {error_msg}")

        if _is_rate_limited(error_msg):
            return {
                "description": (
                    "⚠️ Временный лимит запросов к LLM (429 Too Many Requests). "
                    "Повторите анализ через 15-60 секунд."
                ),
                "severity_level_id": 3,
                "threat_type_id": 11,
                "mitre_techniques": [],
                "events_found": 0,
                "error": error_msg,
            }

        return {
            "description": f"⚠️ Ошибка анализа: {error_msg}",
            "severity_level_id": 3,
            "threat_type_id": 11,
            "mitre_techniques": [],
            "events_found": 0,
            "error": error_msg,
        }


async def close_pipeline():
    """Close pipeline resources (no-op for now)."""
    global _pipeline, _agent_config
    _pipeline = None
    _agent_config = None
    logger.info("AI Agent v2 pipeline closed")
