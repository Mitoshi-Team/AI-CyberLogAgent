import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/")
async def root():
    """Главная страница API"""
    return {"message": "AI CyberLog Agent API", "status": "running", "version": "1.0.0"}


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


# --- CLI Commands ---

# Словарь доступных команд
AVAILABLE_COMMANDS = {
    "collect_logs": "Собрать системные логи",
    "show_logs": "Показать логи",
    "hide_logs": "Скрыть логи",
    "get_history": "Получить историю инцидентов",
    "register": "Зарегистрировать нового пользователя или изменить существующего",
    "help": "Показать справку",
    "interactive": "Запустить консоль CLI",
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
    print("\nИспользование:")
    print("  python app.py <команда>           # Режим одной команды")
    print("  python app.py interactive         # Консоль")
    print("  python app.py --help")
    print("\nПримеры:")
    print("  python app.py collect_logs")
    print("  python app.py register")
    print("  python app.py interactive         # Запустить консоль")
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
