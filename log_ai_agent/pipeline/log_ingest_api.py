"""API endpoints for ingesting external logs into the shared volume directory."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from log_ai_agent.config.cfg import PIPELINE_EXTERNAL_LOGS_DIR

router = APIRouter(prefix="/api/pipeline", tags=["pipeline-ingest"])


class LogTextIngestRequest(BaseModel):
    """Request body for plain-text log ingestion."""

    content: str
    filename: str | None = None
    source: str | None = "external"


def _sanitize_filename(name: str) -> str:
    """Return a safe filename without path traversal parts."""
    base_name = Path(name).name.strip()
    if not base_name:
        return "log.log"

    cleaned = "".join(
        ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in base_name
    )
    if not cleaned:
        return "log.log"
    return cleaned


def _target_path(source: str, original_name: str) -> Path:
    """Build the resulting log file path inside shared volume."""
    external_dir = Path(PIPELINE_EXTERNAL_LOGS_DIR)
    external_dir.mkdir(parents=True, exist_ok=True)

    safe_source = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in source
    )
    safe_name = _sanitize_filename(original_name)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    return external_dir / f"{safe_source}_{ts}_{uuid4().hex[:8]}_{safe_name}"


@router.post("/logs/upload")
async def ingest_log_file(
    file: UploadFile = File(...),
    source: str = Form("external"),
):
    """Accept uploaded log file and write it into shared volume."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла отсутствует")

    target = _target_path(source=source, original_name=file.filename)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Загружен пустой файл")

    with open(target, "wb") as output:
        output.write(content)

    return {
        "success": True,
        "message": "Лог сохранен в общий том",
        "path": str(target),
        "size_bytes": len(content),
    }


@router.post("/logs/text")
async def ingest_log_text(payload: LogTextIngestRequest):
    """Accept raw text log payload and write it into shared volume."""
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Текст логов пустой")

    source = payload.source or "external"
    base_name = payload.filename or "payload.log"
    target = _target_path(source=source, original_name=base_name)

    with open(target, "w", encoding="utf-8") as output:
        output.write(payload.content)

    return {
        "success": True,
        "message": "Текстовые логи сохранены в общий том",
        "path": str(target),
        "size_bytes": len(payload.content.encode("utf-8")),
    }
