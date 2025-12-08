"""AI CyberLog Agent - Backend Application
Заглушка для основного приложения
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    allow_origins=["*"],  # В продакшене указать конкретные домены
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
    return {
        "status": "healthy",
        "database": "connected",  # TODO: добавить реальную проверку БД
    }


@app.get("/api/incidents")
async def get_incidents():
    """Получить список инцидентов (заглушка)"""
    return {
        "incidents": [
            {
                "id": 1,
                "title": "Suspicious Login Activity",
                "severity": "high",
                "status": "active",
                "timestamp": "2025-12-08T10:30:00Z",
            },
            {
                "id": 2,
                "title": "High CPU Usage Detected",
                "severity": "medium",
                "status": "resolved",
                "timestamp": "2025-12-08T09:15:00Z",
            },
        ],
        "total": 2,
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True, log_level="info")
