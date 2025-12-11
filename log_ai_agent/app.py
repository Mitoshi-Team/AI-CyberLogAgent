import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from log_ai_agent.config import commands

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events для приложения"""
    logger.info("🚀 Starting AI CyberLog Agent Backend...")
    logger.info(f"📊 Database URL: {DATABASE_URL}")
    yield
    logger.info("🛑 Shutting down AI CyberLog Agent Backend...")


# Создание FastAPI приложения
app = FastAPI(
    title="AI CyberLog Agent API",
    description="Backend API for AI-powered log analysis and incident monitoring",
    version="1.0.0",
    lifespan=lifespan,
)

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


@app.get("/")
async def root():
    """Главная страница API"""
    return {"message": "AI CyberLog Agent API", "status": "running", "version": "1.0.0"}


@app.post("/auth/login", response_model=LoginResponse)
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
async def get_severity_statistics():
    """Получить статистику по уровням серьезности"""
    try:
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

        # Получаем все уровни серьезности и количество отчетов для каждого
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
async def get_threat_statistics():
    """Получить статистику по типам угроз"""
    try:
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)

        # Получаем все типы угроз и количество отчетов для каждого
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


# --- CLI Commands ---

# Словарь доступных команд
AVAILABLE_COMMANDS = {
    "collect_logs": "Собрать системные логи",
    "show_logs": "Показать логи",
    "hide_logs": "Скрыть логи",
    "get_history": "Получить историю инцидентов",
    "register": "Зарегистрировать нового пользователя или изменить существующего",
    "help": "Показать справку",
    "interactive": "Запустить консоль",
    "exit": "Выйти из консоли",
}


def show_help():
    """Показать справку по использованию консоли."""
    print("\n" + "=" * 60)
    print("  AI CyberLog Agent - CLI Команды")
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

    if not command:
        return True

    if command in ["exit", "quit", "q"]:
        return False

    if command in ["help", "--help", "-h", "?"]:
        show_help()
    elif command == "collect_logs":
        commands.collect_logs()
    elif command == "show_logs":
        commands.show_logs()
    elif command == "hide_logs":
        commands.hide_logs()
    elif command == "get_history":
        commands.get_history()
    elif command == "register":
        commands.register()
    else:
        print(f"❌ Ошибка: неизвестная команда '{command}'")
        print("💡 Введите 'help' чтобы увидеть доступные команды")

    return True


def run_interactive():
    """Запустить CLI консоль"""
    print("\n" + "=" * 60)
    print("  🤖 AI CyberLog Agent - CLI")
    print("=" * 60)
    print("\n  Введите 'help' для просмотра доступных команд")
    print("  Введите 'exit' или 'quit' для выхода из консоли\n")
    print("=" * 60 + "\n")

    while True:
        try:
            command = input("cyberlog> ").strip()
            if not execute_command(command):
                print("\n👋 Выход из консоли...\n")
                break
        except KeyboardInterrupt:
            print("\n\n👋 Прервано. Введите 'exit' для выхода или продолжайте.\n")
            continue
        except EOFError:
            print("\n\n👋 Выход из консоли...\n")
            break


def run_cli():
    """Запустить CLI команды"""
    if len(sys.argv) <= 1:
        print("\nОшибка: команда не указана")
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
