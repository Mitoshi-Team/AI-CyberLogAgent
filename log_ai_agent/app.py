import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    KAFKA_ENABLED,
    KAFKA_GROUP_ID,
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


async def _insert_agent_log(
    conn: asyncpg.Connection,
    action_type_id: int,
    description: str,
) -> None:
    """Persist a short agent action log into AgentLogs table."""
    await conn.execute(
        """
        INSERT INTO public."AgentLogs" (action_type_id, description, date)
        VALUES ($1, $2, NOW())
        """,
        action_type_id,
        description,
    )


async def _try_insert_agent_log(
    conn: asyncpg.Connection,
    action_type_id: int,
    description: str,
) -> None:
    """Best-effort wrapper for AgentLogs writes to avoid breaking main flow."""
    try:
        await _insert_agent_log(conn, action_type_id, description)
    except Exception as error:
        logger.warning(
            "Failed to write AgentLogs entry (action_type_id=%s): %s",
            action_type_id,
            error,
        )


async def _insert_user_log(
    conn: asyncpg.Connection,
    user_id: int,
    action_type_id: int,
    description: str,
) -> None:
    """Persist a short user action log into UserLogs table."""
    await conn.execute(
        """
        INSERT INTO public."UserLogs" (user_id, action_type_id, description, date)
        VALUES ($1, $2, $3, NOW())
        """,
        user_id,
        action_type_id,
        description,
    )


async def _try_insert_user_log(
    conn: asyncpg.Connection,
    user_id: int,
    action_type_id: int,
    description: str,
) -> None:
    """Best-effort wrapper for UserLogs writes to avoid breaking main flow."""
    try:
        await _insert_user_log(conn, user_id, action_type_id, description)
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

    log_content = "\n".join(messages)
    analysis_result = await analyze_log_v2(log_content)
    analysis_error = str(analysis_result.get("error") or "")
    lowered_analysis_error = analysis_error.lower()

    if analysis_error and (
        "payment required" in lowered_analysis_error or "402" in lowered_analysis_error
    ):
        logger.warning(
            "Kafka batch analysis skipped due to external AI payment error: %s",
            analysis_error,
        )
        return

    source_file = batch.get("source_file", "unknown")
    source_files = batch.get("source_files")
    source_label = (
        ", ".join(source_files)
        if isinstance(source_files, list) and source_files
        else source_file
    )
    events_found = analysis_result.get("events_found", 0)
    if events_found <= 0:
        logger.info(
            "Kafka batch has no incidents, skipping auto-report and chat notification: source=%s, records=%s",
            source_label,
            len(messages),
        )
        return

    report_description = (
        "AI pipeline: Agent1 -> RAG -> Agent2\n"
        f"Источник: {source_label}\n"
        f"Размер батча: {batch.get('batch_size', len(messages))}\n"
        f"Событий выделено Agent1: {events_found}\n"
        f"\n{analysis_result['description']}"
    )

    conn = await asyncpg.connect(DATABASE_URL, timeout=10)
    try:
        await _try_insert_agent_log(
            conn,
            AGENT_ACTION_RECEIVE_LOGS,
            f"Получение логов из Kafka: источник={source_label}, записей={len(messages)}",
        )
        await _try_insert_agent_log(
            conn,
            AGENT_ACTION_ANALYZE_LOGS,
            "Анализ логов через AI Agent v2 (Kafka batch)",
        )
        await _try_insert_agent_log(
            conn,
            AGENT_ACTION_MATCH_THREATS,
            "Сопоставление событий с базой угроз/MITRE (Kafka batch)",
        )
        await _try_insert_agent_log(
            conn,
            AGENT_ACTION_BUILD_REPORT,
            "Формирование итогового отчета по Kafka batch",
        )

        log_row = await conn.fetchrow(
            """
            INSERT INTO public."Logs" (file_content, date)
            VALUES ($1, NOW())
            RETURNING log_id
            """,
            log_content,
        )
        log_id = log_row["log_id"]

        await conn.execute(
            """
            INSERT INTO public."Reports" (
                log_id,
                severity_level_id,
                threat_type_id,
                description,
                created_at
            )
            VALUES ($1, $2, $3, $4, NOW())
            """,
            log_id,
            analysis_result["severity_level_id"],
            analysis_result["threat_type_id"],
            report_description,
        )

        await _try_insert_agent_log(
            conn,
            AGENT_ACTION_SAVE_REPORT,
            f"Сохранение отчета по Kafka batch: log_id={log_id}",
        )

        chat_message = f"# Автоотчет по входящим логам\n\n{report_description}\n\n"
        inserted_messages = await conn.execute(
            """
            INSERT INTO public."Messages" (user_id, role, content, created_at)
            SELECT user_id, 'agent', $1, NOW()
            FROM public."Users"
            """,
            chat_message,
        )

        await _try_insert_agent_log(
            conn,
            AGENT_ACTION_RESPOND,
            "Ответ на запрос: автоответ опубликован в чат пользователя",
        )

        logger.info(
            "Kafka batch analyzed and saved via v2: source=%s, records=%s, events_found=%s, log_id=%s",
            source_label,
            len(messages),
            events_found,
            log_id,
        )
        logger.info("Kafka report auto-posted to chat: %s", inserted_messages)
    finally:
        await conn.close()


kafka_log_consumer = KafkaLogBatchConsumer(
    enabled=KAFKA_ENABLED,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    topic=KAFKA_TOPIC,
    group_id=KAFKA_GROUP_ID,
    auto_offset_reset=KAFKA_AUTO_OFFSET_RESET,
    output_file=PIPELINE_CONSUMED_LOGS_FILE,
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
    role: str  # 'user' или 'assistant'
    content: str


class ChatMessageResponse(BaseModel):
    message_id: int
    user_id: int
    role: str
    content: str
    created_at: str


@app.get("/")
async def root():
    """Главная страница API"""
    return {"message": "Wavescan API", "status": "running", "version": "1.0.0"}


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

            if DATABASE_URL and user_data and user_data.get("user_id"):
                conn = await asyncpg.connect(DATABASE_URL, timeout=10)
                try:
                    await _try_insert_user_log(
                        conn,
                        user_data["user_id"],
                        USER_ACTION_LOGIN,
                        f"Вход в систему: login={user_data.get('login', request.username)}",
                    )
                finally:
                    await conn.close()

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


@app.post("/api/auth/logout")
async def logout(user_id: int):
    """Выход пользователя из системы (логирование пользовательского действия)."""
    try:
        if DATABASE_URL:
            conn = await asyncpg.connect(DATABASE_URL, timeout=10)
            try:
                await _try_insert_user_log(
                    conn,
                    user_id,
                    USER_ACTION_LOGOUT,
                    "Выход из системы",
                )
            finally:
                await conn.close()

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
            conn = await asyncpg.connect(DATABASE_URL, timeout=5)
            await conn.execute("SELECT 1")
            await conn.close()
            db_status = "connected"
        except Exception as e:
            db_error = str(e)
            logger.error(f"Database health check failed: {e}")

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "database_error": db_error if db_error else None,
    }


@app.get("/api/statistics/severity")
async def get_severity_statistics(start_date: str = None, end_date: str = None):
    """Получить статистику по уровням серьезности"""
    try:
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

        # Формируем запрос с учетом фильтров по датам
        if start_date and end_date:
            # Преобразуем строки в datetime
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

            rows = await conn.fetch(
                """
                SELECT 
                    sl.severity_level_id,
                    sl.name,
                    COUNT(CASE WHEN r.created_at BETWEEN $1 AND $2 THEN r.report_id END) as count
                FROM public."SeverityLevels" sl
                LEFT JOIN public."Reports" r ON sl.severity_level_id = r.severity_level_id
                GROUP BY sl.severity_level_id, sl.name
                ORDER BY sl.severity_level_id
            """,
                start_dt,
                end_dt,
            )
        else:
            rows = await conn.fetch("""
                SELECT 
                    sl.severity_level_id,
                    sl.name,
                    COUNT(r.report_id) as count
                FROM public."SeverityLevels" sl
                LEFT JOIN public."Reports" r ON sl.severity_level_id = r.severity_level_id
                GROUP BY sl.severity_level_id, sl.name
                ORDER BY sl.severity_level_id
            """)

        await conn.close()

        result = [
            {"id": row["severity_level_id"], "name": row["name"], "count": row["count"]}
            for row in rows
        ]

        return {"data": result}
    except Exception as e:
        logger.error(f"Error getting severity statistics: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")


@app.get("/api/statistics/threats")
async def get_threat_statistics(start_date: str = None, end_date: str = None):
    """Получить статистику по типам угроз"""
    try:
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

        # Формируем запрос с учетом фильтров по датам
        if start_date and end_date:
            # Преобразуем строки в datetime
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

            rows = await conn.fetch(
                """
                SELECT 
                    tt.threat_type_id,
                    tt.name,
                    COUNT(CASE WHEN r.created_at BETWEEN $1 AND $2 THEN r.report_id END) as count
                FROM public."ThreatTypes" tt
                LEFT JOIN public."Reports" r ON tt.threat_type_id = r.threat_type_id
                GROUP BY tt.threat_type_id, tt.name
                ORDER BY COUNT(CASE WHEN r.created_at BETWEEN $1 AND $2 THEN r.report_id END) DESC, tt.name
            """,
                start_dt,
                end_dt,
            )
        else:
            rows = await conn.fetch("""
                SELECT 
                    tt.threat_type_id,
                    tt.name,
                    COUNT(r.report_id) as count
                FROM public."ThreatTypes" tt
                LEFT JOIN public."Reports" r ON tt.threat_type_id = r.threat_type_id
                GROUP BY tt.threat_type_id, tt.name
                ORDER BY COUNT(r.report_id) DESC, tt.name
            """)

        await conn.close()

        result = [
            {"id": row["threat_type_id"], "name": row["name"], "count": row["count"]}
            for row in rows
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
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

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
        rows = await conn.fetch(
            """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM public."Reports"
            WHERE created_at >= $1 AND created_at <= $2
            GROUP BY DATE(created_at)
            ORDER BY date
        """,
            start,
            end,
        )

        await conn.close()

        # Создаем полный список дней с нулями для дней без данных
        result = []
        day_counts = {row["date"]: row["count"] for row in rows}

        # Вычисляем количество дней между start и end
        start_date_obj = start.date()
        end_date_obj = end.date()

        # Рассчитываем количество дней (разница + 1 день, так как включаем оба конца)
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
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

        # Базовый SQL запрос для подсчета общего количества
        count_query = """
            SELECT COUNT(*) as total
            FROM public."Reports" r
            WHERE 1=1
        """

        # Базовый SQL запрос для получения данных
        query = """
            SELECT 
                r.report_id,
                r.description,
                r.created_at,
                sl.severity_level_id,
                sl.name as severity_name,
                tt.threat_type_id,
                tt.name as threat_name
            FROM public."Reports" r
            LEFT JOIN public."SeverityLevels" sl ON r.severity_level_id = sl.severity_level_id
            LEFT JOIN public."ThreatTypes" tt ON r.threat_type_id = tt.threat_type_id
            WHERE 1=1
        """
        params = []
        param_count = 1

        # Добавляем фильтры к обоим запросам
        filter_conditions = ""

        if date_from:
            filter_conditions += f" AND r.created_at >= ${param_count}"
            params.append(datetime.fromisoformat(date_from.replace("Z", "+00:00")))
            param_count += 1

        if date_to:
            filter_conditions += f" AND r.created_at <= ${param_count}"
            params.append(datetime.fromisoformat(date_to.replace("Z", "+00:00")))
            param_count += 1

        if severity_level_id:
            filter_conditions += f" AND r.severity_level_id = ${param_count}"
            params.append(severity_level_id)
            param_count += 1

        if threat_type_id:
            filter_conditions += f" AND r.threat_type_id = ${param_count}"
            params.append(threat_type_id)
            param_count += 1

        # Добавляем фильтры к запросам
        count_query += filter_conditions
        query += filter_conditions

        # Получаем общее количество записей
        total_row = await conn.fetchrow(count_query, *params)
        total = total_row["total"]

        # Вычисляем offset
        offset = (page - 1) * page_size

        # Добавляем сортировку, лимит и offset
        query += f" ORDER BY r.created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([page_size, offset])

        rows = await conn.fetch(query, *params)
        await conn.close()

        # Форматируем результаты
        result = [
            {
                "id": row["report_id"],
                "description": row["description"],
                "created_at": row["created_at"].isoformat(),
                "severity_level_id": row["severity_level_id"],
                "severity_name": row["severity_name"],
                "threat_type_id": row["threat_type_id"],
                "threat_name": row["threat_name"],
            }
            for row in rows
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
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

        # Получаем уровни серьезности
        severity_levels = await conn.fetch("""
            SELECT severity_level_id, name
            FROM public."SeverityLevels"
            ORDER BY severity_level_id
        """)

        # Получаем типы угроз
        threat_types = await conn.fetch("""
            SELECT threat_type_id, name
            FROM public."ThreatTypes"
            ORDER BY threat_type_id
        """)

        await conn.close()

        return {
            "severity_levels": [
                {"id": row["severity_level_id"], "name": row["name"]}
                for row in severity_levels
            ],
            "threat_types": [
                {"id": row["threat_type_id"], "name": row["name"]}
                for row in threat_types
            ],
        }
    except Exception as e:
        logger.error(f"Error getting reports filters: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения фильтров отчетов")


@app.get("/api/reports/{report_id}")
async def get_report_details(report_id: int):
    """Получение детальной информации об отчете"""
    try:
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

        # Получаем отчет с логами
        report = await conn.fetchrow(
            """
            SELECT 
                r.report_id,
                r.description,
                r.created_at,
                r.log_id,
                sl.name as severity_name,
                tt.name as threat_name,
                l.file_content
            FROM public."Reports" r
            LEFT JOIN public."SeverityLevels" sl ON r.severity_level_id = sl.severity_level_id
            LEFT JOIN public."ThreatTypes" tt ON r.threat_type_id = tt.threat_type_id
            LEFT JOIN public."Logs" l ON r.log_id = l.log_id
            WHERE r.report_id = $1
        """,
            report_id,
        )

        await conn.close()

        if not report:
            raise HTTPException(status_code=404, detail="Отчет не найден")

        return {
            "id": report["report_id"],
            "description": report["description"],
            "created_at": report["created_at"].isoformat(),
            "severity_name": report["severity_name"],
            "threat_name": report["threat_name"],
            "file_content": report["file_content"] or "Логи отсутствуют",
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
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

        # Сохраняем сообщение в базу данных
        row = await conn.fetchrow(
            """
            INSERT INTO public."Messages" (user_id, role, content, created_at)
            VALUES ($1, $2, $3, NOW())
            RETURNING message_id, user_id, role, content, created_at
        """,
            request.user_id,
            request.role,
            request.content,
        )

        await conn.close()

        return ChatMessageResponse(
            message_id=row["message_id"],
            user_id=row["user_id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"].isoformat(),
        )
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения сообщения")


@app.get("/api/chat/messages")
async def get_chat_messages(user_id: int, limit: int = 50):
    """Получение последних сообщений чата"""
    try:
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

        # Получаем последние N сообщений для пользователя
        rows = await conn.fetch(
            """
            SELECT message_id, user_id, role, content, created_at
            FROM public."Messages"
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """,
            user_id,
            limit,
        )

        await conn.close()

        # Возвращаем в обратном порядке (от старых к новым)
        messages = [
            {
                "message_id": row["message_id"],
                "user_id": row["user_id"],
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in reversed(rows)
        ]

        return {"data": messages, "total": len(messages)}
    except Exception as e:
        logger.error(f"Error getting chat messages: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения сообщений чата")


@app.delete("/api/chat/messages")
async def clear_chat_messages(user_id: int):
    """Очистка всех сообщений чата пользователя и контекста GigaChat агента"""
    try:
        # Используем специальную функцию для очистки контекста
        deleted_count = await clear_user_context(user_id, DATABASE_URL)

        logger.info(
            f"Chat cleared for user {user_id}: {deleted_count} messages deleted, GigaChat context reset"
        )

        return {
            "success": True,
            "message": "Чат и контекст GigaChat очищены",
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

    conn = await asyncpg.connect(DATABASE_URL, timeout=10)
    try:
        await conn.execute(
            """
            INSERT INTO public."Messages" (user_id, role, content, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            user_id,
            "agent",
            text,
        )
    finally:
        await conn.close()


@app.post("/api/chat/send", response_model=ChatSendResponse)
async def send_chat_message(request: ChatSendRequest):
    """Отправить сообщение AI агенту и получить ответ.

    Процесс:
    1. Сохраняет сообщение пользователя в БД с ролью 'user'
    2. Получает последние 20 сообщений для контекста
    3. Отправляет в GigaChat для получения ответа
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
            conn = await asyncpg.connect(DATABASE_URL, timeout=10)
            try:
                await _try_insert_user_log(
                    conn,
                    request.user_id,
                    USER_ACTION_SEND_MESSAGE,
                    "Отправка сообщения в чат AI-агента",
                )
            finally:
                await conn.close()

        # Обрабатываем сообщение через GigaChat
        result = await process_chat_message(
            user_id=request.user_id,
            user_message=request.message,
            database_url=DATABASE_URL,
        )

        logger.info(
            f"Chat message processed for user {request.user_id}, mode: {result['mode']}"
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

        return ChatSendResponse(
            success=False,
            user_message=request.message,
            agent_response=fallback_text,
            mode=fallback_mode,
            message=fallback_message,
        )


@app.post("/api/logs/upload")
async def upload_log_file(
    user_id: int,
    file: UploadFile = File(...),
    use_v2: bool = True,
):
    """Загрузка и анализ лог-файла.

    Процесс:
    1. Проверка формата файла (.log)
    2. Классический анализ логов
    3. Сохранение в таблицу Logs
    4. Анализ через GigaChat с учетом ThreatTypes и SeverityLevels
    5. Создание отчета в таблице Reports
    6. Возврат результатов пользователю

    Args:
        user_id: ID пользователя
        file: Log file to analyze
        use_v2: Deprecated. Анализ всегда выполняется через AI Agent v2.

    """
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

        conn = await asyncpg.connect(DATABASE_URL, timeout=10)
        try:
            await _try_insert_user_log(
                conn,
                user_id,
                USER_ACTION_SEND_LOGS,
                f"Отправка логов: файл={file.filename}, размер={len(content_str)} байт",
            )

            await _try_insert_agent_log(
                conn,
                AGENT_ACTION_RECEIVE_LOGS,
                f"Получение логов: файл={file.filename}, user_id={user_id}, размер={len(content_str)} байт",
            )

            if not use_v2:
                logger.info("Параметр use_v2=false устарел, используется AI Agent v2")
            logger.info("Используем AI Agent v2 для анализа")

            await _try_insert_agent_log(
                conn,
                AGENT_ACTION_ANALYZE_LOGS,
                f"Анализ логов через AI Agent v2: файл={file.filename}",
            )
            analysis_result = await analyze_log_v2(content_str)
            analysis_error = str(analysis_result.get("error") or "")
            lowered_analysis_error = analysis_error.lower()

            if analysis_error and (
                "payment required" in lowered_analysis_error
                or "402" in lowered_analysis_error
            ):
                await _try_insert_agent_log(
                    conn,
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
                conn,
                AGENT_ACTION_MATCH_THREATS,
                (
                    "Сопоставление с базой угроз/MITRE: "
                    f"threat_type_id={analysis_result.get('threat_type_id', 'n/a')}"
                ),
            )

            await _try_insert_agent_log(
                conn,
                AGENT_ACTION_BUILD_REPORT,
                "Формирование итогового отчета по результатам анализа",
            )

            # Сохраняем содержимое лога
            log_row = await conn.fetchrow(
                """
                INSERT INTO public."Logs" (file_content, date)
                VALUES ($1, NOW())
                RETURNING log_id
                """,
                content_str,
            )
            log_id = log_row["log_id"]

            # Создаем отчет на основе анализа GigaChat
            report_row = await conn.fetchrow(
                """
                INSERT INTO public."Reports" (
                    log_id,
                    severity_level_id,
                    threat_type_id,
                    description,
                    created_at
                )
                VALUES ($1, $2, $3, $4, NOW())
                RETURNING report_id
                """,
                log_id,
                analysis_result["severity_level_id"],
                analysis_result["threat_type_id"],
                analysis_result["description"],
            )
            report_id = report_row["report_id"]

            await _try_insert_agent_log(
                conn,
                AGENT_ACTION_SAVE_REPORT,
                f"Сохранение отчета в БД: log_id={log_id}, report_id={report_id}",
            )

            logger.info(
                f"Файл {file.filename} успешно обработан. "
                f"Log ID: {log_id}, Report ID: {report_id}"
            )

            response = {
                "success": True,
                "log_id": log_id,
                "report_id": report_id,
                "gigachat_analysis": analysis_result["description"],
            }

            # Добавляем метаданные v2 если доступны
            response["ai_version"] = "v2"
            if "mitre_techniques" in analysis_result:
                response["mitre_techniques"] = analysis_result["mitre_techniques"]
            if "processing_time_ms" in analysis_result:
                response["processing_time_ms"] = analysis_result["processing_time_ms"]

            await _try_insert_agent_log(
                conn,
                AGENT_ACTION_RESPOND,
                f"Ответ на запрос загрузки логов: user_id={user_id}, report_id={report_id}",
            )

            return response

        finally:
            await conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading log file: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}"
        )


# --- CLI Commands ---

# Словарь доступных команд
AVAILABLE_COMMANDS = {
    "register": "Зарегистрировать нового пользователя",
    "agent_logs": "Просмотр логов агента (опционально: agent_logs <limit>)",
    "user_logs": "Просмотр логов пользователей (опционально: user_logs <limit>)",
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


def show_agent_logs(limit: int = 50):
    """Show latest agent action logs for admin console."""
    try:
        conn = commands.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                al.agent_log_id,
                al.action_type_id,
                at.name,
                al.description,
                al.date
            FROM public."AgentLogs" al
            LEFT JOIN public."ActionTypes" at ON at.action_type_id = al.action_type_id
            ORDER BY al.date DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cursor.fetchall()

        print("\n" + "=" * 90)
        print(f"  Логи агента (последние {limit}")
        print("=" * 90)

        if not rows:
            print("\nЗаписей нет\n")
        else:
            for row in reversed(rows):
                date_str = _format_cli_datetime(row[4])
                print(f"[{date_str}] id={row[0]} type={row[1]} ({row[2]}) | {row[3]}")
            print()

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка получения логов агента: {e}")


def show_user_logs(limit: int = 50):
    """Show latest user action logs for admin console."""
    try:
        conn = commands.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                ul.user_log_id,
                ul.user_id,
                u.login,
                ul.action_type_id,
                at.name,
                ul.description,
                ul.date
            FROM public."UserLogs" ul
            LEFT JOIN public."Users" u ON u.user_id = ul.user_id
            LEFT JOIN public."ActionTypes" at ON at.action_type_id = ul.action_type_id
            ORDER BY ul.date DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cursor.fetchall()

        print("\n" + "=" * 110)
        print(f"  Логи пользователей (последние {limit})")
        print("=" * 110)

        if not rows:
            print("\nЗаписей нет\n")
        else:
            for row in reversed(rows):
                date_str = _format_cli_datetime(row[6])
                print(
                    f"[{date_str}] id={row[0]} user_id={row[1]} ({row[2]}) type={row[3]} ({row[4]}) | {row[5]}"
                )
            print()

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка получения логов пользователей: {e}")


def show_help():
    """Показать справку по использованию консоли."""
    print("\n" + "=" * 60)
    print("  Wavescan - CLI Команды")
    print("=" * 60)
    print("\nДоступные команды:")
    print("-" * 60)
    for cmd, description in AVAILABLE_COMMANDS.items():
        print(f"  {cmd:15} - {description}")
    print("\n")
    print("=" * 60 + "\n")


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
    elif cmd == "agent_logs":
        limit = _parse_limit_arg(parts)
        show_agent_logs(limit)
    elif cmd == "user_logs":
        limit = _parse_limit_arg(parts)
        show_user_logs(limit)
    else:
        print(f"❌ Ошибка: неизвестная команда '{command}'")
        print("Введите 'help' чтобы увидеть доступные команды")

    return True


def run_interactive():
    """Запустить CLI консоль"""
    print("\n" + "=" * 60)
    print("  Wavescan - CLI")
    print("=" * 60)
    print("\n  Введите 'help' для просмотра доступных команд")
    print("  Введите 'exit' для выхода из консоли\n")
    print("=" * 60 + "\n")

    while True:
        try:
            command = input("wavescan> ").strip()
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

    command = sys.argv[1]

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
