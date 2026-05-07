import asyncio
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid
import urllib.parse
import ssl
import urllib.error
import urllib.request
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, func, text, case
from log_ai_agent.db.session import get_async_session, get_sync_session
from log_ai_agent.db.models import (
    User,
    AgentLog,
    ActionType,
    UserLog,
    Log,
    Report,
    Message,
    SeverityLevel,
    ThreatType,
)
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    import readline
except ImportError:  # pragma: no cover - environment dependent
    readline = None

from log_ai_agent.ai_agent_v2.app_integration import (
    analyze_log_v2,
    close_pipeline,
    warmup_pipeline,
)
from log_ai_agent.ai_agent_v2.chat_integration import (
    clear_user_context,
    process_chat_message,
)
from log_ai_agent.config import commands
from log_ai_agent.config.cfg import (
    KAFKA_AUTO_OFFSET_RESET,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_DLQ_ENABLED,
    KAFKA_DLQ_TOPIC,
    KAFKA_ENABLED,
    KAFKA_GROUP_ID,
    KAFKA_PROCESS_RETRY_ATTEMPTS,
    KAFKA_RETRY_BACKOFF_SECONDS,
    KAFKA_TOPIC,
    PIPELINE_COLLECTED_LOGS_FILE,
    PIPELINE_CONSUMED_LOGS_FILE,
    PIPELINE_KAFKA_AUTO_ANALYZE,
)
from log_ai_agent.pipeline.kafka_consumer import KafkaLogBatchConsumer
from log_ai_agent.pipeline.log_ingest_api import router as pipeline_ingest_router

# Загрузка переменных окружения из .env файла
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Получение настроек из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
CLI_TZ_OFFSET_HOURS = int(os.getenv("CLI_TZ_OFFSET_HOURS", "5"))
CLI_TZ = timezone(timedelta(hours=CLI_TZ_OFFSET_HOURS))
SBER_SPEECH_AUTH_KEY = os.getenv("VITE_SBER_SPEECH_API_KEY")
SBER_SPEECH_API_URL = os.getenv(
    "VITE_SBER_SPEECH_API_URL", "https://smartspeech.sber.ru/rest/v1/speech:recognize"
)
SBER_SPEECH_VALIDATE_URL = os.getenv(
    "VITE_SBER_SPEECH_VALIDATE_URL", "https://smartspeech.sber.ru/rest/v1/text:synthesize"
)
SBER_SPEECH_OAUTH_URL = os.getenv(
    "VITE_SBER_SPEECH_OAUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
)
SBER_SPEECH_SCOPE = os.getenv("VITE_SBER_SPEECH_SCOPE", "SALUTE_SPEECH_PERS")

_sber_token_cache: dict[str, object] = {
    "access_token": None,
    "expires_at": 0.0,
}
APP_DIR = Path(__file__).parent.resolve()
AI_AGENT_RULES_DIR = APP_DIR / "ai_agent_v2" / "rules"
SIGMA_RULES_DIR = AI_AGENT_RULES_DIR / "sigma"
YARA_RULES_DIR = AI_AGENT_RULES_DIR / "yara"
YARA_RULE_FILE = YARA_RULES_DIR / "cyber_security_rules.yar"
ENABLE_DOCKER_RULE_SYNC = os.getenv(
    "ENABLE_DOCKER_RULE_SYNC", "true"
).strip().lower() in {"1", "true", "yes", "on"}
DOCKER_RULE_SYNC_CONTAINER = os.getenv("BACKEND_CONTAINER_NAME", "cyberlog-backend")
DOCKER_RULES_ROOT = Path(
    os.getenv("DOCKER_RULES_ROOT", "/app/log_ai_agent/ai_agent_v2/rules")
)

AGENT_ACTION_RECEIVE_LOGS = 1
AGENT_ACTION_ANALYZE_LOGS = 2
AGENT_ACTION_MATCH_THREATS = 3
AGENT_ACTION_BUILD_REPORT = 4
AGENT_ACTION_SAVE_REPORT = 5
AGENT_ACTION_RESPOND = 6

USER_ACTION_LOGIN = 7
USER_ACTION_LOGOUT = 8
USER_ACTION_SEND_LOGS = 9
USER_ACTION_SEND_MESSAGE = 10

MIN_LOG_LINES = 50
MAX_LOG_LINES = 500

AUTH_TOKENS: dict[str, int] = {}


def _resolve_analysis_marker_file(processed_dir: Path) -> Path:
    """Resolve path to persisted analysis marker shared between CLI and backend."""
    return Path(
        os.getenv(
            "PIPELINE_ANALYSIS_MARKER_FILE",
            str(processed_dir / ".analysis_progress.marker"),
        )
    )


def _extract_bearer_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def _read_analysis_marker(marker_file: Path) -> int | None:
    """Read persisted marker line from analysis marker file."""
    if not marker_file.exists() or not marker_file.is_file():
        return None

    try:
        raw_value = marker_file.read_text(encoding="utf-8").strip()
        marker = int(raw_value)
        return marker if marker >= 0 else 0
    except Exception:
        return None


def _build_sber_speech_request(
    url: str,
    method: str,
    payload: bytes | None = None,
    content_type: str | None = None,
    access_token: str | None = None,
) -> urllib.request.Request:
    headers = {
        "Accept": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if content_type:
        headers["Content-Type"] = content_type

    request = urllib.request.Request(
        url=url,
        data=payload,
        headers=headers,
        method=method,
    )
    return request


def _perform_sber_speech_request(
    url: str,
    method: str,
    payload: bytes | None = None,
    content_type: str | None = None,
    access_token: str | None = None,
) -> tuple[int, str]:
    request = _build_sber_speech_request(
        url, method, payload, content_type, access_token=access_token
    )
    try:
        ssl_context = ssl._create_unverified_context()
        with urllib.request.urlopen(request, timeout=15, context=ssl_context) as response:
            body = response.read().decode("utf-8")
            return response.status, body
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8") if error.fp else ""
        return error.code, body
    except urllib.error.URLError as error:
        return 0, str(error)


def _parse_sber_token_response(payload: dict) -> tuple[str | None, float]:
    access_token = payload.get("access_token")
    if not access_token:
        return None, 0.0

    now = time.time()
    expires_in = payload.get("expires_in")
    expires_at = payload.get("expires_at")

    if isinstance(expires_at, (int, float)):
        if expires_at > now * 10:
            expires_at = expires_at / 1000
        return access_token, float(expires_at)

    if isinstance(expires_in, (int, float)):
        return access_token, now + float(expires_in)

    return access_token, now + 60 * 25


def _get_sber_access_token() -> tuple[str | None, str | None]:
    if not SBER_SPEECH_AUTH_KEY:
        return None, "missing_key"

    now = time.time()
    cached_token = _sber_token_cache.get("access_token")
    cached_expiry = float(_sber_token_cache.get("expires_at") or 0)
    if cached_token and now < cached_expiry - 15:
        return str(cached_token), None

    payload = urllib.parse.urlencode({"scope": SBER_SPEECH_SCOPE}).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {SBER_SPEECH_AUTH_KEY}",
    }

    request = urllib.request.Request(
        url=SBER_SPEECH_OAUTH_URL,
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        ssl_context = ssl._create_unverified_context()
        with urllib.request.urlopen(request, timeout=15, context=ssl_context) as response:
            body = response.read().decode("utf-8")
        data = json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8") if error.fp else ""
        return None, body or f"OAuth error {error.code}"
    except urllib.error.URLError as error:
        return None, str(error)
    except json.JSONDecodeError:
        return None, "Invalid OAuth response"

    access_token, expires_at = _parse_sber_token_response(data)
    if not access_token:
        return None, "Missing access_token in response"

    _sber_token_cache["access_token"] = access_token
    _sber_token_cache["expires_at"] = expires_at
    return access_token, None


def _write_analysis_marker(marker_file: Path, marker_line: int) -> bool:
    """Persist marker line to analysis marker file."""
    try:
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        marker_file.write_text(f"{max(0, marker_line)}\n", encoding="utf-8")
        return True
    except Exception:
        return False


class RealtimeConnectionHub:
    """In-memory WebSocket hub for broadcasting realtime frontend events."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, event: dict) -> None:
        if not self._connections:
            return

        dead_connections: list[WebSocket] = []
        for connection in list(self._connections):
            try:
                await connection.send_json(event)
            except Exception:
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)


realtime_hub = RealtimeConnectionHub()

runtime_analysis_state: dict[str, object] = {
    "processing": False,
    "current_batch_started_at": None,
    "current_source": None,
    "current_records": 0,
    "current_batch_end_record_seq": None,
    "last_batch_completed_at": None,
    "last_completed_end_record_seq": None,
    "last_events_found": None,
    "last_error": None,
}
log_upload_cancel_events: dict[int, asyncio.Event] = {}
log_upload_cancel_lock = asyncio.Lock()


def _mark_runtime_processing(
    source_label: str,
    records_count: int,
    batch_end_record_seq: int | None,
) -> None:
    """Track current Kafka batch processing stage for status endpoint."""
    runtime_analysis_state["processing"] = True
    runtime_analysis_state["current_batch_started_at"] = datetime.now(UTC).isoformat()
    runtime_analysis_state["current_source"] = source_label
    runtime_analysis_state["current_records"] = records_count
    runtime_analysis_state["current_batch_end_record_seq"] = batch_end_record_seq
    runtime_analysis_state["last_error"] = None


def _mark_runtime_idle(
    events_found: int | None = None,
    error_text: str | None = None,
    completed_end_record_seq: int | None = None,
) -> None:
    """Mark Kafka batch processing completion for status endpoint."""
    runtime_analysis_state["processing"] = False
    runtime_analysis_state["last_batch_completed_at"] = datetime.now(UTC).isoformat()
    runtime_analysis_state["last_events_found"] = events_found
    runtime_analysis_state["last_error"] = error_text
    runtime_analysis_state["current_batch_end_record_seq"] = None

    if error_text is None and completed_end_record_seq is not None:
        previous = runtime_analysis_state.get("last_completed_end_record_seq")
        previous_value = previous if isinstance(previous, int) and previous >= 0 else 0
        completed_marker = max(
            previous_value,
            completed_end_record_seq,
        )
        runtime_analysis_state["last_completed_end_record_seq"] = completed_marker
        processed_dir = Path(
            os.getenv("PIPELINE_PROCESSED_LOGS_DIR", "/app/shared/processed")
        )
        marker_file = _resolve_analysis_marker_file(processed_dir)
        _write_analysis_marker(marker_file, completed_marker)


async def _start_log_upload_cancellation_scope(user_id: int) -> asyncio.Event:
    """Create/reset cancellation flag for an active log upload."""
    async with log_upload_cancel_lock:
        cancel_event = asyncio.Event()
        log_upload_cancel_events[user_id] = cancel_event
        return cancel_event


async def _finish_log_upload_cancellation_scope(
    user_id: int, cancel_event: asyncio.Event
) -> None:
    """Remove cancellation flag only for the same active upload scope."""
    async with log_upload_cancel_lock:
        current_event = log_upload_cancel_events.get(user_id)
        if current_event is cancel_event:
            del log_upload_cancel_events[user_id]


def _raise_if_log_upload_canceled(cancel_event: asyncio.Event) -> None:
    """Abort request flow if current upload has been cancelled by user."""
    if cancel_event.is_set():
        raise HTTPException(status_code=499, detail="Анализ лога отменен пользователем")


def _map_severity_for_frontend(severity_level_id: int | None) -> str:
    """Map backend severity level IDs to frontend severity labels."""
    if severity_level_id == 1:
        return "critical"
    if severity_level_id == 2:
        return "warning"
    return "normal"


async def _broadcast_chat_response_event(
    user_id: int,
    response_text: str,
    mode: str | None,
) -> None:
    """Notify connected frontend clients about a new agent chat response."""
    try:
        await realtime_hub.broadcast(
            {
                "type": "chat_response",
                "user_id": user_id,
                "mode": mode,
                "preview": response_text[:200],
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
    except Exception as error:
        logger.warning("Failed to broadcast chat_response event: %s", error)


async def _broadcast_incident_event(
    title: str,
    description: str,
    severity_level_id: int | None,
    source: str,
) -> None:
    """Broadcast a newly created incident/report event to connected clients."""
    try:
        await realtime_hub.broadcast(
            {
                "type": "incident",
                "incident": {
                    "id": int(datetime.now(UTC).timestamp() * 1000),
                    "title": title,
                    "description": description,
                    "severity": _map_severity_for_frontend(severity_level_id),
                    "status": "open",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "source": source,
                    "details": {},
                },
            }
        )
    except Exception as error:
        logger.warning("Failed to broadcast incident event: %s", error)


async def _broadcast_report_created_event(
    report_id: int,
    source: str,
    severity_level_id: int | None,
) -> None:
    """Broadcast report creation event so report views can refresh in realtime."""
    try:
        await realtime_hub.broadcast(
            {
                "type": "report_created",
                "report_id": report_id,
                "source": source,
                "severity": _map_severity_for_frontend(severity_level_id),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
    except Exception as error:
        logger.warning("Failed to broadcast report_created event: %s", error)


def _schedule_background_task(coro, task_name: str) -> None:
    """Run a coroutine in background and log failures without blocking request flow."""
    task = asyncio.create_task(coro)

    def _handle_task_result(done_task: asyncio.Task) -> None:
        try:
            done_task.result()
        except Exception as error:
            logger.warning("Background task %s failed: %s", task_name, error)

    task.add_done_callback(_handle_task_result)


async def _insert_agent_log(
    action_type_id: int,
    description: str,
) -> None:
    """Persist a short agent action log into AgentLogs table."""
    try:
        async with get_async_session() as session:
            log = AgentLog(action_type_id=action_type_id, description=description)
            session.add(log)
            await session.commit()
    except Exception:
        # Swallow to keep best-effort behaviour
        return


async def _try_insert_agent_log(
    action_type_id: int,
    description: str,
) -> None:
    """Best-effort wrapper for AgentLogs writes to avoid breaking main flow."""
    try:
        await _insert_agent_log(action_type_id, description)
    except Exception as error:
        logger.warning(
            "Failed to write AgentLogs entry (action_type_id=%s): %s",
            action_type_id,
            error,
        )


async def _insert_user_log(
    user_id: int,
    action_type_id: int,
    description: str,
) -> None:
    """Persist a short user action log into UserLogs table."""
    try:
        async with get_async_session() as session:
            log = UserLog(user_id=user_id, action_type_id=action_type_id, description=description)
            session.add(log)
            await session.commit()
    except Exception:
        return


async def _try_insert_user_log(
    user_id: int,
    action_type_id: int,
    description: str,
) -> None:
    """Best-effort wrapper for UserLogs writes to avoid breaking main flow."""
    try:
        await _insert_user_log(user_id, action_type_id, description)
    except Exception as error:
        logger.warning(
            "Failed to write UserLogs entry (user_id=%s, action_type_id=%s): %s",
            user_id,
            action_type_id,
            error,
        )


async def _process_kafka_log_batch(payload: dict) -> None:
    """Analyze Kafka batch with AI Agent v2 pipeline and store result in DB."""
    if not PIPELINE_KAFKA_AUTO_ANALYZE:
        return

    batch = payload.get("log") if isinstance(payload.get("log"), dict) else payload

    records = batch.get("records")
    if not isinstance(records, list) or not records:
        return

    messages = []
    for record in records:
        if isinstance(record, dict):
            message = str(record.get("message", "")).strip()
            if message:
                messages.append(message)

    if not messages:
        return

    source_file = batch.get("source_file", "unknown")
    source_files = batch.get("source_files")
    source_label = (
        ", ".join(source_files)
        if isinstance(source_files, list) and source_files
        else source_file
    )
    batch_end_record_seq = _extract_marker_from_payload(payload)
    _mark_runtime_processing(source_label, len(messages), batch_end_record_seq)

    log_content = "\n".join(messages)
    events_found: int | None = None
    runtime_error: str | None = None
    analysis_completed = False

    try:
        analysis_result = await analyze_log_v2(log_content)
        analysis_error = str(analysis_result.get("error") or "")
        lowered_analysis_error = analysis_error.lower()

        if analysis_error and (
            "payment required" in lowered_analysis_error
            or "402" in lowered_analysis_error
        ):
            runtime_error = analysis_error
            logger.warning(
                "Kafka batch analysis skipped due to external AI payment error: %s",
                analysis_error,
            )
            return

        events_found = analysis_result.get("events_found", 0)
        if events_found <= 0:
            logger.info(
                "Kafka batch has no incidents, skipping auto-report and chat notification: source=%s, records=%s",
                source_label,
                len(messages),
            )
            analysis_completed = True
            return

        report_datetime = datetime.now(CLI_TZ).strftime("%d.%m.%Y %H:%M")
        report_description = (
            f"Дата и время: {report_datetime}\n"
            f"Размер батча: {batch.get('batch_size', len(messages))}\n"
            f"Событий найдено: {events_found}\n"
            f"\n{analysis_result['description']}"
        )

        await _try_insert_agent_log(
            AGENT_ACTION_RECEIVE_LOGS,
            f"Получение логов из Kafka: источник={source_label}, записей={len(messages)}",
        )
        await _try_insert_agent_log(
            AGENT_ACTION_ANALYZE_LOGS,
            "Анализ логов через AI Agent v2 (Kafka batch)",
        )
        await _try_insert_agent_log(
            AGENT_ACTION_MATCH_THREATS,
            "Сопоставление событий с базой угроз/MITRE (Kafka batch)",
        )
        await _try_insert_agent_log(
            AGENT_ACTION_BUILD_REPORT,
            "Формирование итогового отчета по Kafka batch",
        )

        async with get_async_session() as session:
            log = Log(file_content=log_content)
            session.add(log)
            await session.flush()
            log_id = log.log_id

            report = Report(
                log_id=log_id,
                severity_level_id=analysis_result.get("severity_level_id"),
                threat_type_id=analysis_result.get("threat_type_id"),
                description=report_description,
            )
            session.add(report)
            await session.flush()
            report_id = report.report_id

            await _try_insert_agent_log(
                AGENT_ACTION_SAVE_REPORT,
                f"Сохранение отчета по Kafka batch: log_id={log_id}, report_id={report_id}",
            )

            chat_message = f"# Автоотчет по входящим логам\n\n{report_description}\n\n"

            # Post a message for every user
            result = await session.execute(select(User.user_id))
            user_ids = result.scalars().all()
            messages_to_add = [Message(user_id=uid, role="agent", content=chat_message) for uid in user_ids]
            session.add_all(messages_to_add)
            await session.commit()

            await _try_insert_agent_log(
                AGENT_ACTION_RESPOND,
                "Отправка автоотчета пользователям через чат",
            )

            logger.info(
                "Kafka batch analyzed and saved via v2: source=%s, records=%s, events_found=%s, log_id=%s, report_id=%s",
                source_label,
                len(messages),
                events_found,
                log_id,
                report_id,
            )
            logger.info(
                "Kafka report auto-posted to chat for users: %s",
                len(user_ids),
            )

            for uid in user_ids:
                await _broadcast_chat_response_event(
                    user_id=uid,
                    response_text=chat_message,
                    mode="auto_report",
                )

        await _broadcast_incident_event(
            title=f"Инцидент из Kafka потока ({source_label})",
            description=report_description,
            severity_level_id=analysis_result.get("severity_level_id"),
            source="Kafka Pipeline",
        )
        await _broadcast_report_created_event(
            report_id=report_id,
            source="Kafka Pipeline",
            severity_level_id=analysis_result.get("severity_level_id"),
        )
        analysis_completed = True
    except Exception as error:
        runtime_error = str(error)
        raise
    finally:
        _mark_runtime_idle(
            events_found=events_found,
            error_text=runtime_error,
            completed_end_record_seq=(
                batch_end_record_seq if analysis_completed else None
            ),
        )


kafka_log_consumer = KafkaLogBatchConsumer(
    enabled=KAFKA_ENABLED,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    topic=KAFKA_TOPIC,
    group_id=KAFKA_GROUP_ID,
    auto_offset_reset=KAFKA_AUTO_OFFSET_RESET,
    output_file=PIPELINE_CONSUMED_LOGS_FILE,
    retry_attempts=KAFKA_PROCESS_RETRY_ATTEMPTS,
    retry_backoff_seconds=KAFKA_RETRY_BACKOFF_SECONDS,
    dlq_enabled=KAFKA_DLQ_ENABLED,
    dlq_topic=KAFKA_DLQ_TOPIC,
    payload_handler=_process_kafka_log_batch,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events для приложения"""
    logger.info("🚀 Starting Wavescan Backend...")
    logger.info(f"📊 Database URL: {DATABASE_URL}")
    logger.info(f"📦 Pipeline collected logs file: {PIPELINE_COLLECTED_LOGS_FILE}")

    try:
        logger.info("Прогрев AI-пайплайна запущен. Ожидайте, пожалуйста...")
        await warmup_pipeline()
        logger.info("Прогрев AI-пайплайна завершен. Система готова к работе.")
    except Exception:
        logger.exception(
            "Ошибка во время прогрева AI-пайплайна при старте; повторная попытка будет выполнена при первом запросе"
        )

    if KAFKA_ENABLED:
        await kafka_log_consumer.start()

    yield

    if KAFKA_ENABLED:
        await kafka_log_consumer.stop()

    logger.info("🛑 Shutting down Wavescan Backend...")
    # Close AI Agent v2 resources
    await close_pipeline()


# Создание FastAPI приложения
app = FastAPI(
    title="Wavescan API",
    description="Backend API for AI-powered log analysis and incident monitoring",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(pipeline_ingest_router)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Endpoints ---


# Модели данных для API
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: dict | None = None
    token: str | None = None


class ChatMessageRequest(BaseModel):
    user_id: int
    role: str  # 'user', 'agent' или 'notice'
    content: str


class ChatMessageResponse(BaseModel):
    message_id: int
    user_id: int
    role: str
    content: str
    created_at: str


class RuleContentUpdateRequest(BaseModel):
    content: str


class SigmaFileCreateRequest(BaseModel):
    filename: str


class YaraFileCreateRequest(BaseModel):
    filename: str


@app.get("/")
async def root():
    """Главная страница API"""
    return {"message": "Wavescan API", "status": "running", "version": "1.0.0"}


async def _serve_websocket(websocket: WebSocket):
    """Realtime WebSocket endpoint for frontend notifications."""
    await realtime_hub.connect(websocket)
    try:
        while True:
            # Keep connection alive; client messages are optional in current flow.
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            text_payload = message.get("text")
            if not text_payload:
                continue

            try:
                payload = json.loads(text_payload)
            except json.JSONDecodeError:
                continue

            if payload.get("type") == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                        "ts": datetime.now(UTC).isoformat(),
                    }
                )
    except WebSocketDisconnect:
        realtime_hub.disconnect(websocket)
    except Exception as error:
        logger.warning("WebSocket connection error: %s", error)
        realtime_hub.disconnect(websocket)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await _serve_websocket(websocket)


@app.websocket("/ws/")
async def websocket_endpoint_slash(websocket: WebSocket):
    await _serve_websocket(websocket)


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Аутентификация пользователя"""
    try:
        success, user_data = commands.verify_user_credentials(
            request.username, request.password
        )

        if success:
            # Генерируем простой токен (в production использовать JWT)
            import secrets

            token = secrets.token_urlsafe(32)
            AUTH_TOKENS[token] = user_data["user_id"]

            if DATABASE_URL and user_data and user_data.get("user_id"):
                await _try_insert_user_log(
                    user_data["user_id"],
                    USER_ACTION_LOGIN,
                    f"Вход в систему: login={user_data.get('login', request.username)}",
                )

            return LoginResponse(
                success=True,
                message="Успешная авторизация",
                user=user_data,
                token=token,
            )
        else:
            return LoginResponse(
                success=False,
                message="Введен неверный логин или пароль",
                user=None,
                token=None,
            )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current authenticated user from token."""
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    user_id = AUTH_TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Недействительный токен")

    user_data = commands.get_user_by_id(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {"success": True, "user": user_data}


@app.post("/api/auth/logout")
async def logout(user_id: int, request: Request):
    """Выход пользователя из системы (логирование пользовательского действия)."""
    try:
        token = _extract_bearer_token(request)
        if token:
            AUTH_TOKENS.pop(token, None)

        if DATABASE_URL:
            await _try_insert_user_log(
                user_id,
                USER_ACTION_LOGOUT,
                "Выход из системы",
            )

        return {
            "success": True,
            "message": "Выход выполнен",
        }
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    db_status = "disconnected"
    db_error = None

    # Проверка подключения к базе данных
    if DATABASE_URL:
        try:
            async with get_async_session() as session:
                await session.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_error = str(e)
            logger.error(f"Database health check failed: {e}")

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "database_error": db_error if db_error else None,
    }


@app.get("/api/system/status")
async def get_system_status():
    """Return runtime status for backend, Kafka consumer and current analysis stage."""
    return {
        "kafka_enabled": KAFKA_ENABLED,
        "consumer_running": bool(getattr(kafka_log_consumer, "_running", False)),
        "analysis": runtime_analysis_state,
    }


@app.get("/api/speech/validate")
async def validate_sber_speech_key():
    if not SBER_SPEECH_AUTH_KEY:
        return {
            "success": False,
            "reason": "missing_key",
            "message": "SaluteSpeech API key is not configured",
        }

    access_token, token_error = await asyncio.to_thread(_get_sber_access_token)
    if not access_token:
        return {
            "success": False,
            "reason": "token_error",
            "message": token_error or "Failed to получить access token",
        }

    return {"success": True}


@app.post("/api/speech/transcribe")
async def transcribe_sber_speech(file: UploadFile = File(...)):
    if not SBER_SPEECH_AUTH_KEY:
        raise HTTPException(status_code=400, detail="SaluteSpeech API key is not configured")

    if not SBER_SPEECH_API_URL:
        raise HTTPException(status_code=400, detail="SaluteSpeech API URL is not configured")

    allowed_content_types = {
        "audio/ogg;codecs=opus",
        "audio/ogg",
    }

    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported audio content type",
                "received": file.content_type,
                "allowed": sorted(allowed_content_types),
            },
        )

    access_token, token_error = await asyncio.to_thread(_get_sber_access_token)
    if not access_token:
        raise HTTPException(status_code=502, detail=token_error or "Failed to получить access token")

    payload = await file.read()
    content_type = file.content_type or "audio/ogg;codecs=opus"

    status_code, body = await asyncio.to_thread(
        _perform_sber_speech_request,
        SBER_SPEECH_API_URL,
        "POST",
        payload,
        content_type,
        access_token,
    )

    if 200 <= status_code < 300:
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=502, detail="Invalid SaluteSpeech response")

    logger.warning("SaluteSpeech transcribe failed: status=%s body=%s", status_code, body)
    raise HTTPException(
        status_code=502,
        detail={
            "upstream_status": status_code,
            "upstream_body": body or "",
        },
    )


def _resolve_sigma_file_path(filename: str) -> Path:
    """Validate sigma filename and return normalized file path."""
    if not filename:
        raise HTTPException(status_code=400, detail="Имя файла обязательно")

    normalized_name = Path(filename).name
    if normalized_name != filename:
        raise HTTPException(status_code=400, detail="Некорректное имя файла")

    suffix = Path(normalized_name).suffix.lower()
    if suffix not in {".yml", ".yaml"}:
        raise HTTPException(status_code=400, detail="Допустимы только .yml или .yaml")

    if any(char in normalized_name for char in ("\\", "/", ":")):
        raise HTTPException(status_code=400, detail="Некорректное имя файла")

    return (SIGMA_RULES_DIR / normalized_name).resolve()


def _resolve_yara_file_path(filename: str) -> Path:
    """Validate Yara filename and return normalized file path."""
    if not filename:
        raise HTTPException(status_code=400, detail="Имя файла обязательно")

    normalized_name = Path(filename).name
    if normalized_name != filename:
        raise HTTPException(status_code=400, detail="Некорректное имя файла")

    suffix = Path(normalized_name).suffix.lower()
    if suffix not in {".yar", ".yara"}:
        raise HTTPException(status_code=400, detail="Допустимы только .yar или .yara")

    if any(char in normalized_name for char in ("\\", "/", ":")):
        raise HTTPException(status_code=400, detail="Некорректное имя файла")

    return (YARA_RULES_DIR / normalized_name).resolve()


async def _reload_detection_pipeline() -> None:
    """Reload AI pipeline to pick up updated YARA/Sigma rules."""
    await close_pipeline()
    await warmup_pipeline()


def _sync_rule_change_to_docker_container(
    file_path: Path,
    *,
    deleted: bool = False,
) -> bool:
    """Mirror updated rule file into running backend container when available.

    This is useful when backend API runs outside Docker, but analysis runtime
    uses a running backend container.
    """
    if not ENABLE_DOCKER_RULE_SYNC:
        return False

    # When backend already runs in a container, local writes are already in target FS.
    if Path("/.dockerenv").exists():
        return False

    docker_bin = shutil.which("docker")
    if docker_bin is None:
        return False

    try:
        relative_path = file_path.resolve().relative_to(AI_AGENT_RULES_DIR.resolve())
    except Exception:
        logger.warning("Skip docker sync: file outside rules dir: %s", file_path)
        return False

    container_target = (DOCKER_RULES_ROOT / relative_path).as_posix()
    container_parent = str(Path(container_target).parent).replace("\\", "/")

    try:
        subprocess.run(
            [
                docker_bin,
                "exec",
                DOCKER_RULE_SYNC_CONTAINER,
                "sh",
                "-lc",
                f"mkdir -p {shlex.quote(container_parent)}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if deleted:
            subprocess.run(
                [
                    docker_bin,
                    "exec",
                    DOCKER_RULE_SYNC_CONTAINER,
                    "sh",
                    "-lc",
                    f"rm -f {shlex.quote(container_target)}",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
        else:
            subprocess.run(
                [
                    docker_bin,
                    "cp",
                    str(file_path),
                    f"{DOCKER_RULE_SYNC_CONTAINER}:{container_target}",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )

        logger.info(
            "Rule synced to container %s: %s",
            DOCKER_RULE_SYNC_CONTAINER,
            container_target,
        )
        return True
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        logger.warning(
            "Docker rule sync failed for '%s': %s",
            file_path,
            stderr or str(e),
        )
        return False
    except Exception as e:
        logger.warning("Docker rule sync error for '%s': %s", file_path, e)
        return False


@app.get("/api/config/sigma/files")
async def list_sigma_rule_files():
    """Get list of Sigma rule files from rules directory."""
    try:
        SIGMA_RULES_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            file.name
            for file in SIGMA_RULES_DIR.iterdir()
            if file.is_file() and file.suffix.lower() in {".yml", ".yaml"}
        )
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listing Sigma files: {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка чтения каталога Sigma правил"
        )


@app.post("/api/config/sigma/files")
async def create_sigma_rule_file(request: SigmaFileCreateRequest):
    """Create empty Sigma rule file."""
    try:
        SIGMA_RULES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = _resolve_sigma_file_path(request.filename)

        if file_path.exists():
            raise HTTPException(status_code=409, detail="Файл уже существует")

        initial_content = (
            "title: New Sigma Rule\n"
            "id: \n"
            "status: experimental\n"
            "description: \n"
            "logsource:\n"
            "  category: webserver\n"
            "detection:\n"
            "  selection:\n"
            '    raw|contains: ""\n'
            "  condition: selection\n"
            "level: medium\n"
        )
        file_path.write_text(initial_content, encoding="utf-8")
        _sync_rule_change_to_docker_container(file_path)
        await _reload_detection_pipeline()
        return {"success": True, "filename": file_path.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Sigma file: {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка создания файла Sigma правила"
        )


@app.get("/api/config/sigma/files/{filename}")
async def get_sigma_rule_file_content(filename: str):
    """Get Sigma rule file content."""
    try:
        file_path = _resolve_sigma_file_path(filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Файл не найден")

        return {
            "filename": file_path.name,
            "content": file_path.read_text(encoding="utf-8"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading Sigma file '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Ошибка чтения файла Sigma правила")


@app.put("/api/config/sigma/files/{filename}")
async def update_sigma_rule_file_content(
    filename: str, request: RuleContentUpdateRequest
):
    """Update Sigma rule file content and reload detection pipeline."""
    try:
        file_path = _resolve_sigma_file_path(filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Файл не найден")

        file_path.write_text(request.content, encoding="utf-8")
        _sync_rule_change_to_docker_container(file_path)
        await _reload_detection_pipeline()
        return {"success": True, "filename": file_path.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating Sigma file '{filename}': {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка сохранения файла Sigma правила"
        )


@app.delete("/api/config/sigma/files/{filename}")
async def delete_sigma_rule_file(filename: str):
    """Delete Sigma rule file and reload detection pipeline."""
    try:
        file_path = _resolve_sigma_file_path(filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Файл не найден")

        file_path.unlink()
        _sync_rule_change_to_docker_container(file_path, deleted=True)
        await _reload_detection_pipeline()
        return {"success": True, "filename": file_path.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting Sigma file '{filename}': {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка удаления файла Sigma правила"
        )


@app.get("/api/config/yara/files")
async def list_yara_rule_files():
    """Get list of Yara rule files from rules directory."""
    try:
        YARA_RULES_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            file.name
            for file in YARA_RULES_DIR.iterdir()
            if file.is_file() and file.suffix.lower() in {".yar", ".yara"}
        )
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listing Yara files: {e}")
        raise HTTPException(status_code=500, detail="Ошибка чтения каталога Yara правил")


@app.post("/api/config/yara/files")
async def create_yara_rule_file(request: YaraFileCreateRequest):
    """Create empty Yara rule file."""
    try:
        YARA_RULES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = _resolve_yara_file_path(request.filename)

        if file_path.exists():
            raise HTTPException(status_code=409, detail="Файл уже существует")

        initial_content = (
            "rule NewYaraRule\n"
            "{\n"
            "  meta:\n"
            "    description = \"\"\n"
            "    severity = \"medium\"\n"
            "  strings:\n"
            "    $s1 = \"example\"\n"
            "  condition:\n"
            "    $s1\n"
            "}\n"
        )
        file_path.write_text(initial_content, encoding="utf-8")
        _sync_rule_change_to_docker_container(file_path)
        await _reload_detection_pipeline()
        return {"success": True, "filename": file_path.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Yara file: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания файла Yara правила")


@app.get("/api/config/yara/files/{filename}")
async def get_yara_rule_file_content_multi(filename: str):
    """Get Yara rule file content."""
    try:
        file_path = _resolve_yara_file_path(filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Файл не найден")

        return {
            "filename": file_path.name,
            "content": file_path.read_text(encoding="utf-8"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading Yara file '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Ошибка чтения файла Yara правила")


@app.put("/api/config/yara/files/{filename}")
async def update_yara_rule_file_content_multi(
    filename: str, request: RuleContentUpdateRequest
):
    """Update Yara rule file content and reload detection pipeline."""
    try:
        file_path = _resolve_yara_file_path(filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Файл не найден")

        file_path.write_text(request.content, encoding="utf-8")
        _sync_rule_change_to_docker_container(file_path)
        await _reload_detection_pipeline()
        return {"success": True, "filename": file_path.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating Yara file '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения файла Yara правила")


@app.delete("/api/config/yara/files/{filename}")
async def delete_yara_rule_file(filename: str):
    """Delete Yara rule file and reload detection pipeline."""
    try:
        file_path = _resolve_yara_file_path(filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Файл не найден")

        file_path.unlink()
        _sync_rule_change_to_docker_container(file_path, deleted=True)
        await _reload_detection_pipeline()
        return {"success": True, "filename": file_path.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting Yara file '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Ошибка удаления файла Yara правила")


@app.get("/api/config/yara")
async def get_yara_rule_file_content():
    """Get single YARA rules file content."""
    try:
        if not YARA_RULE_FILE.exists() or not YARA_RULE_FILE.is_file():
            raise HTTPException(status_code=404, detail="Yara файл не найден")

        return {
            "filename": YARA_RULE_FILE.name,
            "content": YARA_RULE_FILE.read_text(encoding="utf-8"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading Yara file: {e}")
        raise HTTPException(status_code=500, detail="Ошибка чтения Yara файла")


@app.put("/api/config/yara")
async def update_yara_rule_file_content(request: RuleContentUpdateRequest):
    """Update YARA rules file content and reload detection pipeline."""
    try:
        YARA_RULES_DIR.mkdir(parents=True, exist_ok=True)
        YARA_RULE_FILE.write_text(request.content, encoding="utf-8")
        _sync_rule_change_to_docker_container(YARA_RULE_FILE)
        await _reload_detection_pipeline()
        return {"success": True, "filename": YARA_RULE_FILE.name}
    except Exception as e:
        logger.error(f"Error updating Yara file: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения Yara файла")


@app.get("/api/statistics/severity")
async def get_severity_statistics(start_date: str = None, end_date: str = None):
    """Получить статистику по уровням серьезности"""
    try:
        async with get_async_session() as session:
            # Формируем запрос с учетом фильтров по датам
            if start_date and end_date:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

                count_expr = func.count(
                    case((Report.created_at.between(start_dt, end_dt), Report.report_id))
                ).label("count")
            else:
                count_expr = func.count(Report.report_id).label("count")

            stmt = (
                select(SeverityLevel.severity_level_id, SeverityLevel.name, count_expr)
                .outerjoin(Report, SeverityLevel.severity_level_id == Report.severity_level_id)
                .group_by(SeverityLevel.severity_level_id, SeverityLevel.name)
                .order_by(SeverityLevel.severity_level_id)
            )

            rows = await session.execute(stmt)
            records = rows.all()
            result = [
                {"id": r[0], "name": r[1], "count": int(r[2] or 0)} for r in records
            ]

            return {"data": result}
    except Exception as e:
        logger.error(f"Error getting severity statistics: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")


@app.get("/api/statistics/threats")
async def get_threat_statistics(start_date: str = None, end_date: str = None):
    """Получить статистику по типам угроз"""
    try:
        async with get_async_session() as session:
            if start_date and end_date:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                count_expr = func.count(
                    case((Report.created_at.between(start_dt, end_dt), Report.report_id))
                ).label("count")
                order_expr = func.count(
                    case((Report.created_at.between(start_dt, end_dt), Report.report_id))
                ).desc()
            else:
                count_expr = func.count(Report.report_id).label("count")
                order_expr = func.count(Report.report_id).desc()

            stmt = (
                select(ThreatType.threat_type_id, ThreatType.name, count_expr)
                .outerjoin(Report, ThreatType.threat_type_id == Report.threat_type_id)
                .group_by(ThreatType.threat_type_id, ThreatType.name)
                .order_by(order_expr, ThreatType.name)
            )

            rows = await session.execute(stmt)
            records = rows.all()
            result = [
                {"id": r[0], "name": r[1], "count": int(r[2] or 0)} for r in records
            ]

            return {"data": result}
    except Exception as e:
        logger.error(f"Error getting threat statistics: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")


@app.get("/api/statistics/activity")
async def get_activity_statistics(
    period_type: str = "week", start_date: str = None, end_date: str = None
):
    """Получить статистику активности по дням

    Args:
        period_type: тип периода - 'week' или 'month'
        start_date: начало периода (ISO format)
        end_date: конец периода (ISO format)

    """
    try:
        from datetime import datetime, timedelta

        if start_date and end_date:
            # Парсим даты напрямую, игнорируя время и часовой пояс
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

            # Используем только дату без времени, затем создаем datetime для работы с БД
            start = datetime.combine(start_dt.date(), datetime.min.time())
            end = datetime.combine(end_dt.date(), datetime.max.time())

            logger.info(
                f"Activity stats - Received dates: start={start_date}, end={end_date}"
            )
            logger.info(f"Activity stats - Normalized: start={start}, end={end}")
        else:
            # По умолчанию - текущая неделя/месяц
            now = datetime.now()
            if period_type == "week":
                # Текущая неделя (понедельник - воскресенье)
                start = now - timedelta(days=now.weekday())
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=6)
                end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                # Текущий месяц
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                # Последний день месяца
                if now.month == 12:
                    end = now.replace(
                        year=now.year + 1,
                        month=1,
                        day=1,
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                    ) - timedelta(days=1)
                else:
                    end = now.replace(
                        month=now.month + 1,
                        day=1,
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                    ) - timedelta(days=1)
                end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Получаем количество отчетов по дням
        async with get_async_session() as session:
            stmt = (
                select(func.date(Report.created_at).label("date"), func.count().label("count"))
                .where(Report.created_at >= start, Report.created_at <= end)
                .group_by(func.date(Report.created_at))
                .order_by(func.date(Report.created_at))
            )
            rows = await session.execute(stmt)
            rows = rows.all()

        # Создаем полный список дней с нулями для дней без данных
        result = []
        day_counts = {r[0]: int(r[1] or 0) for r in rows}

        # Вычисляем количество дней между start и end
        start_date_obj = start.date()
        end_date_obj = end.date()

        # Рассчитываем количество дней (разница + 1 день, так как включаем оба концы)
        days_count = (end_date_obj - start_date_obj).days + 1

        # Генерируем даты: для недели будет 7 дней, для месяца - количество дней в месяце
        for i in range(days_count):
            current_date = start_date_obj + timedelta(days=i)
            result.append(
                {
                    "date": current_date.isoformat(),
                    "count": day_counts.get(current_date, 0),
                }
            )

        return {
            "data": result,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting activity statistics: {e}")
        raise HTTPException(
            status_code=500, detail="Ошибка получения статистики активности"
        )


@app.get("/api/reports/history")
async def get_reports_history(
    date_from: str = None,
    date_to: str = None,
    severity_level_id: int = None,
    threat_type_id: int = None,
    page: int = 1,
    page_size: int = 10,
):
    """Получение истории отчетов с фильтрацией и пагинацией"""
    try:
        async with get_async_session() as session:
            # Build base query
            base = (
                select(
                    Report.report_id,
                    Report.description,
                    Report.created_at,
                    SeverityLevel.severity_level_id,
                    SeverityLevel.name.label("severity_name"),
                    ThreatType.threat_type_id,
                    ThreatType.name.label("threat_name"),
                )
                .outerjoin(SeverityLevel, Report.severity_level_id == SeverityLevel.severity_level_id)
                .outerjoin(ThreatType, Report.threat_type_id == ThreatType.threat_type_id)
            )

            filters = []
            if date_from:
                filters.append(Report.created_at >= datetime.fromisoformat(date_from.replace("Z", "+00:00")))
            if date_to:
                filters.append(Report.created_at <= datetime.fromisoformat(date_to.replace("Z", "+00:00")))
            if severity_level_id:
                filters.append(Report.severity_level_id == severity_level_id)
            if threat_type_id:
                filters.append(Report.threat_type_id == threat_type_id)

            if filters:
                base = base.where(*filters)

            # total count
            count_stmt = select(func.count()).select_from(Report)
            if filters:
                count_stmt = count_stmt.where(*filters)
            total_res = await session.execute(count_stmt)
            total = int(total_res.scalar() or 0)

            # pagination
            offset = (page - 1) * page_size
            stmt = base.order_by(Report.created_at.desc()).limit(page_size).offset(offset)
            rows = await session.execute(stmt)
            records = rows.all()

            result = [
                {
                    "id": r[0],
                    "description": r[1],
                    "created_at": r[2].isoformat() if r[2] else None,
                    "severity_level_id": r[3],
                    "severity_name": r[4],
                    "threat_type_id": r[5],
                    "threat_name": r[6],
                }
                for r in records
            ]

            return {
                "data": result,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            }
    except Exception as e:
        logger.error(f"Error getting reports history: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения истории отчетов")


@app.get("/api/reports/filters")
async def get_reports_filters():
    """Получение всех доступных фильтров для отчетов"""
    try:
        async with get_async_session() as session:
            sev_res = await session.execute(select(SeverityLevel).order_by(SeverityLevel.severity_level_id))
            severity_levels = sev_res.scalars().all()

            th_res = await session.execute(select(ThreatType).order_by(ThreatType.threat_type_id))
            threat_types = th_res.scalars().all()

            return {
                "severity_levels": [{"id": s.severity_level_id, "name": s.name} for s in severity_levels],
                "threat_types": [{"id": t.threat_type_id, "name": t.name} for t in threat_types],
            }
    except Exception as e:
        logger.error(f"Error getting reports filters: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения фильтров отчетов")


@app.get("/api/reports/{report_id}")
async def get_report_details(report_id: int):
    """Получение детальной информации об отчете"""
    try:
        async with get_async_session() as session:
            stmt = (
                select(
                    Report.report_id,
                    Report.description,
                    Report.created_at,
                    Report.log_id,
                    SeverityLevel.name.label("severity_name"),
                    ThreatType.name.label("threat_name"),
                    Log.file_content,
                )
                .outerjoin(SeverityLevel, Report.severity_level_id == SeverityLevel.severity_level_id)
                .outerjoin(ThreatType, Report.threat_type_id == ThreatType.threat_type_id)
                .outerjoin(Log, Report.log_id == Log.log_id)
                .where(Report.report_id == report_id)
            )
            res = await session.execute(stmt)
            row = res.mappings().one_or_none()

        if not row:
            raise HTTPException(status_code=404, detail="Отчет не найден")

        return {
            "id": row["report_id"],
            "description": row["description"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "severity_name": row["severity_name"] or None,
            "threat_name": row["threat_name"] or None,
            "file_content": row["file_content"] or "Логи отсутствуют",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report details: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения деталей отчета")


@app.post("/api/chat/messages", response_model=ChatMessageResponse)
async def save_chat_message(request: ChatMessageRequest):
    """Сохранение сообщения в чат"""
    try:
        async with get_async_session() as session:
            msg = Message(user_id=request.user_id, role=request.role, content=request.content)
            session.add(msg)
            await session.flush()
            await session.commit()

            return ChatMessageResponse(
                message_id=msg.message_id,
                user_id=msg.user_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat() if msg.created_at else None,
            )
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения сообщения")


@app.get("/api/chat/messages")
async def get_chat_messages(user_id: int, limit: int = 50):
    """Получение последних сообщений чата"""
    try:
        async with get_async_session() as session:
            stmt = (
                select(Message)
                .where(Message.user_id == user_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            rows = await session.execute(stmt)
            messages_rows = rows.scalars().all()

        messages = [
            {
                "message_id": m.message_id,
                "user_id": m.user_id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in reversed(messages_rows)
        ]

        return {"data": messages, "total": len(messages)}
    except Exception as e:
        logger.error(f"Error getting chat messages: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения сообщений чата")


@app.delete("/api/chat/messages")
async def clear_chat_messages(user_id: int):
    """Очистка всех сообщений чата пользователя и контекста AI агента"""
    try:
        # Используем специальную функцию для очистки контекста
        deleted_count = await clear_user_context(user_id, DATABASE_URL)

        logger.info(
            f"Chat cleared for user {user_id}: {deleted_count} messages deleted, AI context reset"
        )

        return {
            "success": True,
            "message": "Чат и контекст AI очищены",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        logger.error(f"Error clearing chat messages: {e}")
        raise HTTPException(status_code=500, detail="Ошибка очистки чата")


class ChatSendRequest(BaseModel):
    user_id: int
    message: str


class ChatSendResponse(BaseModel):
    success: bool
    user_message: str
    agent_response: str
    mode: str | None = None
    message: str | None = None


async def _store_agent_fallback_message(user_id: int, text: str) -> None:
    """Persist fallback assistant message so chat history remains consistent."""
    if not DATABASE_URL:
        return

    try:
        async with get_async_session() as session:
            msg = Message(user_id=user_id, role="agent", content=text)
            session.add(msg)
            await session.commit()
    except Exception:
        return


@app.post("/api/chat/send", response_model=ChatSendResponse)
async def send_chat_message(request: ChatSendRequest):
    """Отправить сообщение AI агенту и получить ответ.

    Процесс:
    1. Пользовательское сообщение уже сохранено фронтендом
    2. Получает последние 20 сообщений для контекста
    3. Отправляет в LLM для получения ответа
    4. Сохраняет ответ в БД с ролью 'agent'
    5. Возвращает ответ агента
    """
    try:
        # Проверяем, что сообщение не пустое
        if not request.message or not request.message.strip():
            raise HTTPException(
                status_code=400, detail="Сообщение не может быть пустым"
            )

        if DATABASE_URL:
            await _try_insert_user_log(
                request.user_id,
                USER_ACTION_SEND_MESSAGE,
                "Отправка сообщения в чат AI-агента",
            )

        # Обрабатываем сообщение через LLM
        result = await process_chat_message(
            user_id=request.user_id,
            user_message=request.message,
            database_url=DATABASE_URL,
        )

        logger.info(
            f"Chat message processed for user {request.user_id}, mode: {result['mode']}"
        )

        await _broadcast_chat_response_event(
            user_id=request.user_id,
            response_text=result["response"],
            mode=result.get("mode"),
        )

        return ChatSendResponse(
            success=True,
            user_message=request.message,
            agent_response=result["response"],
            mode=result["mode"],
            message="Сообщение успешно обработано",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        error_text = str(e)

        if "Payment Required" in error_text or "402" in error_text:
            fallback_text = (
                "Сервис AI временно недоступен: внешний провайдер вернул ошибку тарифа "
                "(402 Payment Required). Попробуйте позже или проверьте тариф/баланс API."
            )
            fallback_mode = "agent_unavailable_payment_required"
            fallback_message = "Ответ сформирован в режиме деградации"
        elif "All connection attempts failed" in error_text:
            fallback_text = (
                "Сервис AI временно недоступен из-за сетевой ошибки при обращении к LLM. "
                "Попробуйте отправить сообщение еще раз через 1-2 минуты."
            )
            fallback_mode = "agent_unavailable_network"
            fallback_message = "Ответ сформирован в режиме деградации"
        else:
            raise HTTPException(
                status_code=500,
                detail="Ошибка обработки сообщения на сервере",
            )

        try:
            await _store_agent_fallback_message(request.user_id, fallback_text)
        except Exception as db_error:
            logger.error(f"Failed to persist fallback chat message: {db_error}")

        await _broadcast_chat_response_event(
            user_id=request.user_id,
            response_text=fallback_text,
            mode=fallback_mode,
        )

        return ChatSendResponse(
            success=False,
            user_message=request.message,
            agent_response=fallback_text,
            mode=fallback_mode,
            message=fallback_message,
        )


@app.post("/api/logs/upload/cancel")
async def cancel_log_upload_analysis(user_id: int):
    """Cancel active log analysis for a user."""
    async with log_upload_cancel_lock:
        cancel_event = log_upload_cancel_events.get(user_id)
        if cancel_event is not None:
            cancel_event.set()
            return {"success": True, "message": "Запрошена отмена анализа лога"}

    return {"success": False, "message": "Активный анализ для отмены не найден"}


@app.post("/api/logs/upload")
async def upload_log_file(
    request: Request,
    user_id: int,
    file: UploadFile = File(...),
    use_v2: bool = True,
):
    """Загрузка и анализ лог-файла.

    Процесс:
    1. Проверка формата файла (.log)
    2. Классический анализ логов
    3. Сохранение в таблицу Logs
    4. Анализ через LLM с учетом ThreatTypes и SeverityLevels
    5. Создание отчета в таблице Reports
    6. Возврат результатов пользователю

    Args:
        user_id: ID пользователя
        file: Log file to analyze
        use_v2: Deprecated. Анализ всегда выполняется через AI Agent v2.

    """
    cancel_event = await _start_log_upload_cancellation_scope(user_id)

    try:
        # Проверяем расширение файла
        if not file.filename.endswith(".log"):
            raise HTTPException(
                status_code=400,
                detail="Можно загружать только файлы с расширением .log",
            )

        # Читаем содержимое файла
        file_content = await file.read()

        # Декодируем содержимое
        try:
            content_str = file_content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content_str = file_content.decode("windows-1251")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Не удалось декодировать файл. Используйте UTF-8 или Windows-1251",
                )

        # Проверяем, что файл не пустой
        if not content_str or len(content_str.strip()) == 0:
            raise HTTPException(
                status_code=400, detail="Файл пустой. Загрузите файл с содержимым."
            )

        # Проверяем допустимый диапазон строк в логе
        non_empty_lines_count = sum(
            1 for line in content_str.splitlines() if line.strip()
        )
        if not (MIN_LOG_LINES <= non_empty_lines_count <= MAX_LOG_LINES):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Файл должен содержать от {MIN_LOG_LINES} до {MAX_LOG_LINES} непустых строк. "
                    f"Этот файл содержит: {non_empty_lines_count}."
                ),
            )

        logger.info(
            f"Получен файл {file.filename} от пользователя {user_id}, "
            f"размер: {len(content_str)} байт, строк: {non_empty_lines_count}"
        )

        if await request.is_disconnected():
            raise HTTPException(status_code=499, detail="Клиент прервал загрузку")
        _raise_if_log_upload_canceled(cancel_event)

        try:
            await _try_insert_user_log(
                user_id,
                USER_ACTION_SEND_LOGS,
                f"Отправка логов: файл={file.filename}, размер={len(content_str)} байт",
            )

            await _try_insert_agent_log(
                AGENT_ACTION_RECEIVE_LOGS,
                f"Получение логов: файл={file.filename}, user_id={user_id}, размер={len(content_str)} байт",
            )

            if not use_v2:
                logger.info("Параметр use_v2=false устарел, используется AI Agent v2")
            logger.info("Используем AI Agent v2 для анализа")

            await _try_insert_agent_log(
                AGENT_ACTION_ANALYZE_LOGS,
                f"Анализ логов через AI Agent v2: файл={file.filename}",
            )
            analyze_task = asyncio.create_task(analyze_log_v2(content_str))
            cancel_wait_task = asyncio.create_task(cancel_event.wait())
            done, pending = await asyncio.wait(
                {analyze_task, cancel_wait_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for pending_task in pending:
                pending_task.cancel()

            if cancel_wait_task in done and cancel_event.is_set():
                analyze_task.cancel()
                with suppress(asyncio.CancelledError):
                    await analyze_task
                raise HTTPException(
                    status_code=499, detail="Анализ лога отменен пользователем"
                )

            analysis_result = await analyze_task

            if await request.is_disconnected():
                raise HTTPException(status_code=499, detail="Клиент прервал загрузку")
            _raise_if_log_upload_canceled(cancel_event)

            analysis_error = str(analysis_result.get("error") or "")
            lowered_analysis_error = analysis_error.lower()

            if analysis_error and (
                "payment required" in lowered_analysis_error
                or "402" in lowered_analysis_error
            ):
                await _try_insert_agent_log(
                    AGENT_ACTION_RESPOND,
                    "Ответ на запрос: отчет не создан из-за ошибки внешнего AI сервиса (402 Payment Required)",
                )
                raise HTTPException(
                    status_code=503,
                    detail=analysis_result.get(
                        "description",
                        "⚠️ Ошибка анализа: внешний AI сервис вернул 402 Payment Required.",
                    ),
                )

            await _try_insert_agent_log(
                AGENT_ACTION_MATCH_THREATS,
                (
                    "Сопоставление с базой угроз/MITRE: "
                    f"threat_type_id={analysis_result.get('threat_type_id', 'n/a')}"
                ),
            )

            await _try_insert_agent_log(
                AGENT_ACTION_BUILD_REPORT,
                "Формирование итогового отчета по результатам анализа",
            )
            _raise_if_log_upload_canceled(cancel_event)

            # Сохраняем содержимое лога
            async with get_async_session() as session:
                log = Log(file_content=content_str)
                session.add(log)
                await session.flush()
                log_id = log.log_id
                _raise_if_log_upload_canceled(cancel_event)

                report = Report(
                    log_id=log_id,
                    severity_level_id=analysis_result.get("severity_level_id"),
                    threat_type_id=analysis_result.get("threat_type_id"),
                    description=analysis_result.get("description"),
                )
                session.add(report)
                await session.flush()
                report_id = report.report_id

                await _try_insert_agent_log(
                    AGENT_ACTION_SAVE_REPORT,
                    f"Сохранение отчета в БД: log_id={log_id}, report_id={report_id}",
                )
                
                # Явно коммитим перед отправкой broadcast событий
                await session.commit()

            logger.info(
                f"Файл {file.filename} успешно обработан. "
                f"Log ID: {log_id}, Report ID: {report_id}"
            )

            response = {
                "success": True,
                "log_id": log_id,
                "report_id": report_id,
                "ai_analysis": analysis_result["description"],
            }

            # Добавляем метаданные v2 если доступны
            response["ai_version"] = "v2"
            if "mitre_techniques" in analysis_result:
                response["mitre_techniques"] = analysis_result["mitre_techniques"]
            if "processing_time_ms" in analysis_result:
                response["processing_time_ms"] = analysis_result["processing_time_ms"]

            await _try_insert_agent_log(
                AGENT_ACTION_RESPOND,
                f"Ответ на запрос загрузки логов: user_id={user_id}, report_id={report_id}",
            )

            _schedule_background_task(
                _broadcast_incident_event(
                    title="Найден новый инцидент",
                    description=analysis_result["description"],
                    severity_level_id=analysis_result.get("severity_level_id"),
                    source="Manual Log Upload",
                ),
                "broadcast_incident_event",
            )
            _schedule_background_task(
                _broadcast_chat_response_event(
                    user_id=user_id,
                    response_text=analysis_result["description"],
                    mode="manual_upload_report",
                ),
                "broadcast_manual_upload_chat_response_event",
            )
            _schedule_background_task(
                _broadcast_report_created_event(
                    report_id=report_id,
                    source="Manual Log Upload",
                    severity_level_id=analysis_result.get("severity_level_id"),
                ),
                "broadcast_report_created_event",
            )

            return response
        finally:
            pass

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading log file: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}"
        )
    finally:
        await _finish_log_upload_cancellation_scope(user_id, cancel_event)


# --- CLI Commands ---

# Словарь доступных команд
AVAILABLE_COMMANDS = {
    "register": "Зарегистрировать нового пользователя",
    "users": "Показать всех пользователей и признак администратора",
    "set_admin": "Назначить/снять админа: set_admin <login> <on|off>",
    "agent_logs": "Просмотр логов агента (опционально: agent_logs <limit>)",
    "user_logs": "Просмотр логов пользователей (опционально: user_logs <limit>)",
    "pipeline_lines": "Показать текущее количество строк в external и processed",
    "processed_lines": "Показать последние строки из processed (опционально: processed_lines <limit>)",
    "clear_pipeline_logs": "Полная очистка логов в external и processed",
    "agent_status": "Показать текущий этап агента по последнему AgentLogs",
    "help": "Показать справку",
    "interactive": "Запустить консоль",
    "exit": "Выйти из консоли",
}


def _parse_limit_arg(parts: list[str], default: int = 50) -> int:
    """Parse optional numeric limit argument from CLI command."""
    if len(parts) < 2:
        return default

    try:
        value = int(parts[1])
        return value if value > 0 else default
    except ValueError:
        print(f"⚠ Некорректный лимит '{parts[1]}', используется {default}")
        return default


def _format_cli_datetime(value: datetime) -> str:
    """Format timestamp for CLI output in configured timezone without offset suffix."""
    if not isinstance(value, datetime):
        return str(value)

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)

    return value.astimezone(CLI_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _format_runtime_timestamp(value: object) -> str:
    """Format ISO timestamp string from runtime status to CLI timezone."""
    if value in (None, ""):
        return "unknown"

    if isinstance(value, datetime):
        return _format_cli_datetime(value)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return "unknown"

        # Support both ISO with offset and trailing 'Z'.
        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return _format_cli_datetime(parsed)
        except ValueError:
            return raw

    return str(value)


def show_agent_logs(limit: int = 50):
    """Show latest agent action logs for admin console."""
    try:
        with get_sync_session() as session:
            stmt = (
                select(AgentLog.agent_log_id, AgentLog.action_type_id, ActionType.name, AgentLog.description, AgentLog.date)
                .outerjoin(ActionType, AgentLog.action_type_id == ActionType.action_type_id)
                .order_by(AgentLog.date.desc())
                .limit(limit)
            )
            res = session.execute(stmt)
            rows = res.fetchall()

        print("\n" + "=" * 60)
        print(f"  Логи агента (последние {limit}")
        print("=" * 60)

        if not rows:
            print("\nЗаписей нет\n")
        else:
            for row in reversed(rows):
                date_str = _format_cli_datetime(row[4])
                print(f"[{date_str}] id={row[0]} type={row[1]} ({row[2]}) | {row[3]}")
            print()
    except Exception as e:
        print(f"❌ Ошибка получения логов агента: {e}")


def show_user_logs(limit: int = 50):
    """Show latest user action logs for admin console."""
    try:
        with get_sync_session() as session:
            stmt = (
                select(
                    UserLog.user_log_id,
                    UserLog.user_id,
                    User.login,
                    UserLog.action_type_id,
                    ActionType.name,
                    UserLog.description,
                    UserLog.date,
                )
                .outerjoin(User, UserLog.user_id == User.user_id)
                .outerjoin(ActionType, UserLog.action_type_id == ActionType.action_type_id)
                .order_by(UserLog.date.desc())
                .limit(limit)
            )
            res = session.execute(stmt)
            rows = res.fetchall()

        print("\n" + "=" * 60)
        print(f"  Логи пользователей (последние {limit})")
        print("=" * 60)

        if not rows:
            print("\nЗаписей нет\n")
        else:
            for row in reversed(rows):
                date_str = _format_cli_datetime(row[6])
                print(
                    f"[{date_str}] id={row[0]} user_id={row[1]} ({row[2]}) type={row[3]} ({row[4]}) | {row[5]}"
                )
            print()
    except Exception as e:
        print(f"❌ Ошибка получения логов пользователей: {e}")


def show_users_with_admin_flags() -> None:
    """Show all users with admin status for CLI."""
    try:
        users = commands.list_users_admin_status()
        print("\n" + "=" * 60)
        print("  Пользователи")
        print("=" * 60)

        if not users:
            print("\nПользователи не найдены\n")
            return

        for user in users:
            role = "admin" if user.get("is_admin") else "user"
            print(
                f"{user.get('login')} | is_admin={str(bool(user.get('is_admin'))).lower()} | role={role}"
            )
        print("")
    except Exception as e:
        print(f"❌ Ошибка получения списка пользователей: {e}")


def update_user_admin_role(parts: list[str]) -> None:
    """Grant/revoke admin role for user from CLI command args."""
    if len(parts) < 3:
        print("❌ Использование: set_admin <login> <on|off>")
        return

    login = parts[1].strip()
    mode = parts[2].strip().lower()
    if mode not in {"on", "off"}:
        print("❌ Третий аргумент должен быть on или off")
        return

    try:
        success, message = commands.set_user_admin_status(login, mode == "on")
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
    except Exception as e:
        print(f"❌ Ошибка обновления прав администратора: {e}")


def _count_lines_in_file(path: Path) -> int:
    """Count lines in a file using binary chunks for robustness."""
    try:
        with path.open("rb") as file_obj:
            chunk_size = 1024 * 1024
            line_count = 0
            last_byte = None

            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break

                line_count += chunk.count(b"\n")
                last_byte = chunk[-1]

            if last_byte is not None and last_byte != ord("\n"):
                line_count += 1

            return line_count
    except Exception:
        return 0


def _collect_directory_stats(
    path: Path,
    exclude_file_names: set[str] | None = None,
) -> tuple[int, int]:
    """Return (files_count, lines_count) for all files under directory."""
    files_count = 0
    lines_count = 0
    excluded_names = exclude_file_names or set()

    if not path.exists() or not path.is_dir():
        return files_count, lines_count

    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.name in excluded_names:
            continue

        files_count += 1
        lines_count += _count_lines_in_file(file_path)

    return files_count, lines_count


def _read_chunk_marker_line(state_file: Path) -> int | None:
    """Read last emitted stream sequence (marker line) from chunk state file."""
    if not state_file.exists() or not state_file.is_file():
        return None

    try:
        with state_file.open("r", encoding="utf-8", errors="replace") as file_obj:
            for raw_line in file_obj:
                line = raw_line.strip()
                if not line or not line.startswith("H\t"):
                    continue

                fields = line.split("\t")
                if len(fields) < 5:
                    return None

                marker_line = int(fields[4])
                return marker_line if marker_line >= 0 else 0
    except Exception:
        return None

    return None


def _read_chunk_state_progress(state_file: Path) -> tuple[int, int] | None:
    """Read (marker_line, pending_lines) from Vector chunk state header line."""
    if not state_file.exists() or not state_file.is_file():
        return None

    try:
        with state_file.open("r", encoding="utf-8", errors="replace") as file_obj:
            for raw_line in file_obj:
                line = raw_line.strip()
                if not line or not line.startswith("H\t"):
                    continue

                fields = line.split("\t")
                if len(fields) < 5:
                    return None

                next_record_seq = int(fields[2])
                last_emitted_record_seq = int(fields[4])

                marker_line = max(0, last_emitted_record_seq)
                pending_lines = max(0, (next_record_seq - 1) - last_emitted_record_seq)
                return marker_line, pending_lines
    except Exception:
        return None

    return None


def _extract_marker_from_payload(payload: object) -> int | None:
    """Extract processed marker from known payload shapes."""
    if not isinstance(payload, dict):
        return None

    log_payload = (
        payload.get("log") if isinstance(payload.get("log"), dict) else payload
    )

    end_record_sequence = log_payload.get("end_record_sequence")
    if isinstance(end_record_sequence, int) and end_record_sequence >= 0:
        return end_record_sequence

    records = log_payload.get("records")
    if isinstance(records, list) and records:
        last_seq = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            stream_seq = record.get("stream_seq")
            if isinstance(stream_seq, int) and stream_seq > last_seq:
                last_seq = stream_seq

        if last_seq > 0:
            return last_seq

    return None


def _read_chunk_marker_line_from_processed(processed_dir: Path) -> int | None:
    """Infer marker line from processed files when chunk state file is unavailable."""
    if not processed_dir.exists() or not processed_dir.is_dir():
        return None

    max_marker: int | None = None
    files = sorted(path for path in processed_dir.rglob("*") if path.is_file())

    for file_path in files:
        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as file_obj:
                for line in file_obj:
                    text = line.strip()
                    if not text:
                        continue

                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        continue

                    marker = _extract_marker_from_payload(payload)
                    if marker is not None and (
                        max_marker is None or marker > max_marker
                    ):
                        max_marker = marker
        except Exception:
            continue

    return max_marker


def _clear_directory_contents(path: Path) -> tuple[int, int]:
    """Delete all files and subdirectories inside the given directory.

    Returns:
        tuple: (files_deleted, lines_deleted)

    """
    files_deleted = 0
    lines_deleted = 0

    for entry in path.iterdir():
        if entry.is_dir():
            for nested_file in entry.rglob("*"):
                if nested_file.is_file():
                    files_deleted += 1
                    lines_deleted += _count_lines_in_file(nested_file)
            shutil.rmtree(entry)
            continue

        lines_deleted += _count_lines_in_file(entry)
        entry.unlink()
        files_deleted += 1

    return files_deleted, lines_deleted


def show_pipeline_lines() -> None:
    """Show current line counts in external and processed pipeline directories."""
    external_logs_dir = os.getenv("PIPELINE_EXTERNAL_LOGS_DIR", "/app/shared/external")
    processed_logs_dir = os.getenv(
        "PIPELINE_PROCESSED_LOGS_DIR", "/app/shared/processed"
    )
    chunk_state_file = Path(
        os.getenv("CHUNK_STATE_FILE", "/var/lib/vector/chunk_logs_state.tsv")
    )
    chunk_reset_marker = Path(
        os.getenv(
            "PIPELINE_CHUNK_RESET_MARKER_FILE",
            "/app/shared/external/.chunk_state_reset",
        )
    )
    analysis_marker_file = _resolve_analysis_marker_file(Path(processed_logs_dir))

    targets = {
        "external": Path(external_logs_dir),
        "processed": Path(processed_logs_dir),
    }
    external_excluded_names = {
        ".chunk_state_reset",
        chunk_state_file.name,
        f"{chunk_state_file.name}.tmp",
    }
    processed_excluded_names = {
        analysis_marker_file.name,
    }

    print("\n" + "=" * 60)
    print("  Статистика строк pipeline")
    print("=" * 60)

    external_lines = 0

    for label, target in targets.items():
        excluded_names = (
            external_excluded_names if label == "external" else processed_excluded_names
        )
        files_count, lines_count = _collect_directory_stats(
            target,
            exclude_file_names=excluded_names,
        )
        if label == "external":
            external_lines = lines_count
        print(f"{label:10} lines={lines_count:<10} path={target}")

    marker_line: int | None = None
    pending_lines: int | None = None

    if chunk_reset_marker.exists():
        marker_line = 0
        pending_lines = external_lines
    else:
        persisted_marker = _read_analysis_marker(analysis_marker_file)
        if isinstance(persisted_marker, int) and persisted_marker >= 0:
            marker_line = persisted_marker
            pending_lines = max(0, external_lines - marker_line)
        else:
            runtime_status = _fetch_runtime_status_from_api()
            analysis_state = runtime_analysis_state
            if runtime_status and isinstance(runtime_status.get("analysis"), dict):
                analysis_state = runtime_status["analysis"]

            completed_marker = analysis_state.get("last_completed_end_record_seq")
            if (
                isinstance(completed_marker, int)
                and completed_marker >= 0
                and completed_marker <= external_lines
            ):
                marker_line = completed_marker
                pending_lines = max(0, external_lines - marker_line)

    if marker_line is None or pending_lines is None:
        state_progress = _read_chunk_state_progress(chunk_state_file)
        if state_progress is not None:
            marker_line, _ = state_progress
            pending_lines = max(0, external_lines - marker_line)
        else:
            marker_line = _read_chunk_marker_line(chunk_state_file)
            if marker_line is None:
                marker_line = _read_chunk_marker_line_from_processed(
                    targets["processed"]
                )
            if marker_line is not None:
                pending_lines = max(0, external_lines - marker_line)

    if marker_line is None or pending_lines is None:
        print("Остановился на неизвестной строке, осталось строк неизвестно.")
    else:
        marker_line = min(marker_line, external_lines)
        pending_lines = max(0, external_lines - marker_line)
        print(f"Остановился на {marker_line} строке, осталось строк {pending_lines}.")

    print("")


def show_processed_lines(limit: int = 20) -> None:
    """Show last N lines from files in processed pipeline directory."""
    processed_logs_dir = os.getenv(
        "PIPELINE_PROCESSED_LOGS_DIR", "/app/shared/processed"
    )
    target = Path(processed_logs_dir)

    print("\n" + "=" * 60)
    print("  Последние строки из processed")
    print("=" * 60)

    if not target.exists():
        print(f"⚠ Путь не существует: {target}\n")
        return

    if not target.is_dir():
        print(f"⚠ Путь не является директорией: {target}\n")
        return

    files = sorted([path for path in target.rglob("*") if path.is_file()])
    if not files:
        print(f"Файлы не найдены в: {target}\n")
        return

    collected_lines: list[tuple[str, int, str]] = []
    for file_path in files:
        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as file_obj:
                for line_no, line in enumerate(file_obj, start=1):
                    collected_lines.append((str(file_path), line_no, line.rstrip("\n")))
        except Exception as exc:
            print(f"⚠ Не удалось прочитать {file_path}: {exc}")

    if not collected_lines:
        print("Строки не найдены\n")
        return

    effective_limit = max(1, limit)
    lines_to_show = collected_lines[-effective_limit:]

    print(
        f"Всего файлов: {len(files)}, всего строк: {len(collected_lines)}, "
        f"показываю последние: {len(lines_to_show)}"
    )
    print("-" * 60)

    for file_path, line_no, content in lines_to_show:
        print(f"{file_path}:{line_no} | {content}")

    print("")


def clear_pipeline_logs() -> None:
    """Clear pipeline logs from external and processed shared directories."""
    external_logs_dir = os.getenv("PIPELINE_EXTERNAL_LOGS_DIR", "/app/shared/external")
    processed_logs_dir = os.getenv(
        "PIPELINE_PROCESSED_LOGS_DIR", "/app/shared/processed"
    )
    chunk_reset_marker = Path(
        os.getenv(
            "PIPELINE_CHUNK_RESET_MARKER_FILE",
            "/app/shared/external/.chunk_state_reset",
        )
    )
    analysis_marker_file = _resolve_analysis_marker_file(Path(processed_logs_dir))

    targets = {
        "external": Path(external_logs_dir),
        "processed": Path(processed_logs_dir),
    }

    print("\n" + "=" * 60)
    print("  Очистка pipeline логов")
    print("=" * 60)

    total_files = 0
    total_lines = 0

    for label, target in targets.items():
        if not target.exists():
            print(f"⚠ Пропуск {label}: путь не существует -> {target}")
            continue

        if not target.is_dir():
            print(f"⚠ Пропуск {label}: путь не является директорией -> {target}")
            continue

        files_deleted, lines_deleted = _clear_directory_contents(target)
        total_files += files_deleted
        total_lines += lines_deleted

        print(
            "✓ Очищено %s: файлов=%s, строк=%s, путь=%s"
            % (label, files_deleted, lines_deleted, target)
        )

    marker_created = False
    marker_error = None
    try:
        chunk_reset_marker.parent.mkdir(parents=True, exist_ok=True)
        chunk_reset_marker.write_text(
            f"reset_requested_at={datetime.now(UTC).isoformat()}\n",
            encoding="utf-8",
        )
        marker_created = True
    except Exception as exc:
        marker_error = str(exc)

    print("-" * 60)
    if marker_created:
        print(f"✓ Маркер сброса прогресса создан: {chunk_reset_marker}")
    else:
        print(
            "⚠ Не удалось создать маркер сброса прогресса: "
            f"{chunk_reset_marker} ({marker_error})"
        )

    marker_reset_written = _write_analysis_marker(analysis_marker_file, 0)
    if marker_reset_written:
        print(f"✓ Маркер анализа сброшен: {analysis_marker_file}")
    else:
        print(f"⚠ Не удалось сбросить маркер анализа: {analysis_marker_file}")

    runtime_analysis_state["last_completed_end_record_seq"] = 0
    runtime_analysis_state["current_batch_end_record_seq"] = None

    print(f"Итог: удалено файлов={total_files}, строк={total_lines}\n")


def _setup_cli_history() -> None:
    """Enable CLI command history navigation with arrow keys when readline is available."""
    if readline is None:
        return

    history_path = Path.home() / ".wavescan_cli_history"

    try:
        if history_path.exists():
            readline.read_history_file(str(history_path))
    except Exception:
        pass

    readline.set_history_length(200)

    def _persist_history() -> None:
        try:
            readline.write_history_file(str(history_path))
        except Exception:
            pass

    import atexit

    atexit.register(_persist_history)


def _fetch_runtime_status_from_api() -> dict | None:
    """Fetch status from running backend process for accurate CLI diagnostics."""
    status_url = os.getenv(
        "WAVESCAN_STATUS_URL", "http://127.0.0.1:8000/api/system/status"
    )

    try:
        with urllib.request.urlopen(status_url, timeout=2) as response:
            if response.status != 200:
                return None
            payload = response.read().decode("utf-8")
            import json

            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return parsed
            return None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def show_agent_status() -> None:
    """Show the latest known agent stage from AgentLogs."""
    try:
        with get_sync_session() as session:
            stmt = (
                select(AgentLog.action_type_id, ActionType.name, AgentLog.description, AgentLog.date)
                .outerjoin(ActionType, AgentLog.action_type_id == ActionType.action_type_id)
                .order_by(AgentLog.date.desc())
                .limit(1)
            )
            res = session.execute(stmt)
            row = res.fetchone()

        print("\n" + "=" * 60)
        print("  Статус:")
        print("=" * 60)

        runtime_status = _fetch_runtime_status_from_api()

        if KAFKA_ENABLED:
            if runtime_status:
                consumer_running = bool(runtime_status.get("consumer_running", False))
                consumer_state = "запущен" if consumer_running else "остановлен"
                print(f"Kafka consumer: {consumer_state}")

                analysis = runtime_status.get("analysis")
                if isinstance(analysis, dict):
                    if analysis.get("processing"):
                        started_at = _format_runtime_timestamp(
                            analysis.get("current_batch_started_at")
                        )
                        print(
                            "Обработка batch: выполняется | "
                            f"source={analysis.get('current_source', 'unknown')} | "
                            f"records={analysis.get('current_records', 0)} | "
                            f"started_at={started_at}"
                        )
                    else:
                        last_completed_at = _format_runtime_timestamp(
                            analysis.get("last_batch_completed_at")
                        )
                        print(
                            "Обработка batch: простаивает | "
                            f"last_completed_at={last_completed_at} | "
                            f"last_events_found={analysis.get('last_events_found', 'unknown')}"
                        )

                    last_error = analysis.get("last_error")
                    if last_error:
                        print(f"Последняя ошибка batch: {last_error}")
            else:
                consumer_state = (
                    "запущен" if kafka_log_consumer._running else "остановлен"
                )
                print(f"Kafka consumer: {consumer_state} (локальный процесс CLI)")
                print(
                    "Примечание: если консоль запущена отдельной командой python app.py interactive, "
                    "этот статус может не отражать состояние основного backend-процесса."
                )

        print()

        print("=" * 60)
        print("  Последнее действие агента:")
        print("=" * 60)

        if not row:
            print("Нет записей AgentLogs. Агент еще не выполнял действий.\n")
            return

        action_type_id, action_name, description, action_date = row
        formatted_date = _format_cli_datetime(action_date)

        print(f"Этап: {action_name or 'неизвестно'} (action_type_id={action_type_id})")
        print(f"Время: {formatted_date}")
        print(f"Описание: {description}")

    except Exception as e:
        print(f"❌ Ошибка получения текущего этапа агента: {e}")


def show_help():
    """Показать справку по использованию консоли."""
    print("\n" + "=" * 60)
    print("  Wavescan - CLI Команды")
    print("=" * 60)
    print("\nДоступные команды:")
    print("-" * 60)
    for cmd, description in AVAILABLE_COMMANDS.items():
        print(f"  {cmd:15} - {description}")
    print("-" * 60 + "\n")


def execute_command(command: str):
    """Выполнить одну CLI команду"""
    command = command.strip()
    parts = command.split()
    cmd = parts[0] if parts else ""

    if not command:
        return True

    if cmd in ["exit", "quit", "q"]:
        return False

    if cmd in ["help", "?"]:
        show_help()
    elif cmd == "register":
        commands.register()
    elif cmd == "users":
        show_users_with_admin_flags()
    elif cmd == "set_admin":
        update_user_admin_role(parts)
    elif cmd == "agent_logs":
        limit = _parse_limit_arg(parts)
        show_agent_logs(limit)
    elif cmd == "user_logs":
        limit = _parse_limit_arg(parts)
        show_user_logs(limit)
    elif cmd == "pipeline_lines":
        show_pipeline_lines()
    elif cmd == "processed_lines":
        limit = _parse_limit_arg(parts, default=20)
        show_processed_lines(limit)
    elif cmd == "clear_pipeline_logs":
        clear_pipeline_logs()
    elif cmd == "agent_status":
        show_agent_status()
    else:
        print(f"❌ Ошибка: неизвестная команда '{command}'")
        print("Введите 'help' чтобы увидеть доступные команды")

    return True


def _colorize_gradient_text(
    text: str,
    start_rgb: tuple[int, int, int],
    end_rgb: tuple[int, int, int],
) -> str:
    """Apply a left-to-right ANSI truecolor gradient to text."""
    if not text:
        return text

    length = len(text)
    if length == 1:
        r, g, b = start_rgb
        return f"\033[38;2;{r};{g};{b}m{text}\033[0m"

    chars: list[str] = []
    for idx, char in enumerate(text):
        ratio = idx / (length - 1)
        red = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        green = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        blue = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        chars.append(f"\033[38;2;{red};{green};{blue}m{char}")

    return "".join(chars) + "\033[0m"


def run_interactive():
    """Запустить CLI консоль"""
    _setup_cli_history()

    use_colored_prompt = (
        os.getenv("NO_COLOR") is None and os.getenv("TERM", "").lower() != "dumb"
    )
    prompt = "\033[95mwavescan>\033[0m " if use_colored_prompt else "wavescan> "

    logo_lines = [
        " ██╗    ██╗ █████╗ ██╗   ██╗███████╗███████╗ ██████╗ █████╗ ███╗   ██╗",
        " ██║    ██║██╔══██╗██║   ██║██╔════╝██╔════╝██╔════╝██╔══██╗████╗  ██║",
        " ██║ █╗ ██║███████║██║   ██║█████╗  ███████╗██║     ███████║██╔██╗ ██║",
        " ██║███╗██║██╔══██║╚██╗ ██╔╝██╔══╝  ╚════██║██║     ██╔══██║██║╚██╗██║",
        " ╚███╔███╔╝██║  ██║ ╚████╔╝ ███████╗███████║╚██████╗██║  ██║██║ ╚████║",
        "  ╚══╝╚══╝ ╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝",
    ]

    print("")
    if use_colored_prompt:
        for line in logo_lines:
            print(_colorize_gradient_text(line, (168, 85, 247), (56, 189, 248)))
    else:
        for line in logo_lines:
            print(line)
    print("\n" + "=" * 60)
    print("\n  Введите 'help' для просмотра доступных команд")
    print("  Введите 'exit' для выхода из консоли\n")
    print("=" * 60 + "\n")

    while True:
        try:
            command = input(prompt).strip()
            if not execute_command(command):
                print("\nВыход из консоли...\n")
                break
        except KeyboardInterrupt:
            print("\n\nПрервано. Введите 'exit' для выхода или продолжайте работать.\n")
            continue
        except EOFError:
            print("\n\nВыход из консоли...\n")
            break


def run_cli():
    """Запустить CLI команды"""
    if len(sys.argv) <= 1:
        print("\n❌ Ошибка: команда не указана")
        show_help()
        sys.exit(1)

    command = " ".join(sys.argv[1:])

    # Обработка команды help
    if command in ["--help", "-h", "help"]:
        show_help()
        sys.exit(0)

    # Обработка консоли
    if command in ["interactive", "i", "shell"]:
        run_interactive()
        sys.exit(0)

    # Выполнить одну команду
    result = execute_command(command)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    # Check if CLI command is provided
    if len(sys.argv) > 1 and (
        sys.argv[1] in AVAILABLE_COMMANDS
        or sys.argv[1] in ["--help", "-h", "i", "shell"]
    ):
        run_cli()
    else:
        # Start web server
        import uvicorn

        logger.info(f"Starting server on {HOST}:{PORT}")
        uvicorn.run("app:app", host=HOST, port=PORT, reload=True, log_level="info")
