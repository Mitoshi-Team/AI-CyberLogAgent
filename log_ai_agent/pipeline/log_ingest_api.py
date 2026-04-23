"""API endpoints for ingesting external logs into a shared append-only file."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from log_ai_agent.config.cfg import (
    PIPELINE_EXTERNAL_APPEND_FILE,
    PIPELINE_EXTERNAL_LOGS_DIR,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline-ingest"])


class LogTextIngestRequest(BaseModel):
    """Request body for plain-text log ingestion."""

    content: str
    filename: str | None = None
    source: str | None = "external"


def _append_target_path() -> Path:
    """Return append target path for all external log uploads."""
    default_external_dir = Path(PIPELINE_EXTERNAL_LOGS_DIR)
    default_external_dir.mkdir(parents=True, exist_ok=True)

    append_path = Path(PIPELINE_EXTERNAL_APPEND_FILE)
    append_path.parent.mkdir(parents=True, exist_ok=True)
    return append_path


def _decode_uploaded_bytes(content: bytes) -> str:
    """Decode uploaded bytes into text, preserving most common encodings."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("windows-1251")
        except UnicodeDecodeError:
            return content.decode("utf-8", errors="replace")


def _append_text_with_separator(path: Path, text: str) -> int:
    """Append text to target path and ensure each payload ends with newline."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized and not normalized.endswith("\n"):
        normalized += "\n"

    with path.open("a", encoding="utf-8") as output:
        output.write(normalized)

    return len(normalized.encode("utf-8"))


@router.post("/logs/upload")
async def ingest_log_file(
    file: UploadFile = File(...),
    source: str = Form("external"),
):
    """Accept uploaded log file and append lines into shared stream file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла отсутствует")

    target = _append_target_path()

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Загружен пустой файл")

    decoded = _decode_uploaded_bytes(content)

    now_ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    source_label = (source or "external").strip() or "external"
    header = (
        f'{now_ts} app {{"level":"INFO","msg":"ingest_upload",'
        f'"source":"{source_label}","filename":"{file.filename}"}}\n'
    )
    bytes_written = _append_text_with_separator(target, header + decoded)

    return {
        "success": True,
        "message": "Лог добавлен в общий поток внешних логов",
        "path": str(target),
        "size_bytes": bytes_written,
    }


@router.post("/logs/text")
async def ingest_log_text(payload: LogTextIngestRequest):
    """Accept raw text log payload and append lines into shared stream file."""
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Текст логов пустой")

    source = payload.source or "external"
    base_name = payload.filename or "payload.log"
    target = _append_target_path()

    now_ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        f'{now_ts} app {{"level":"INFO","msg":"ingest_text",'
        f'"source":"{source}","filename":"{base_name}"}}\n'
    )
    bytes_written = _append_text_with_separator(target, header + payload.content)

    return {
        "success": True,
        "message": "Текстовые логи добавлены в общий поток внешних логов",
        "path": str(target),
        "size_bytes": bytes_written,
    }
