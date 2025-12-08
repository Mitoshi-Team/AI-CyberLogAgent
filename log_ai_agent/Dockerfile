# Dockerfile для Python приложения
FROM python:3.13-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов проекта
COPY pyproject.toml ./
COPY log_ai-agent/ ./log_ai-agent/

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Установка дополнительных зависимостей для веб-сервера
RUN pip install --no-cache-dir fastapi uvicorn[standard] psycopg2-binary sqlalchemy

WORKDIR /app/log_ai-agent

# Открываем порт для API
EXPOSE 8000

# Запуск приложения
CMD ["python", "app.py"]
