# syntax=docker/dockerfile:1
FROM python:3.13.0-slim

# Установка системных зависимостей + uv
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Install huggingface_hub CLI for model download
RUN uv pip install --system huggingface_hub

WORKDIR /app

COPY pyproject.toml ./
COPY log_ai_agent/ ./log_ai_agent/

# Установка зависимостей через uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e . && \
    uv pip install --system fastapi "uvicorn[standard]" psycopg2-binary sqlalchemy python-multipart

# Copy entrypoint script
RUN chmod +x /app/log_ai_agent/docker-entrypoint.sh

WORKDIR /app/log_ai_agent

EXPOSE 8000

# Download model at startup, then start app
ENTRYPOINT ["/app/log_ai_agent/docker-entrypoint.sh"]