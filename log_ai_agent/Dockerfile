# syntax=docker/dockerfile:1
FROM python:3.13.0-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

RUN uv pip install --system huggingface_hub hf_transfer
WORKDIR /app

# --- ШАГ 1: Только файлы для установки зависимостей ---
COPY pyproject.toml ./
# Создаем пустую папку, чтобы pip install -e . не ругался на отсутствие исходников
# Но НЕ копируем пока весь код
RUN mkdir log_ai_agent

# Install CPU torch
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --index-url https://download.pytorch.org/whl/cpu torch

# --- ШАГ 2: Скачивание модели (теперь закешируется) ---
# Создаем путь заранее
RUN mkdir -p /app/log_ai_agent/ai_agent_v2/embedding/models/multilingual-e5-base && \
    pip install tqdm && \
    hf download intfloat/multilingual-e5-base \
    --local-dir /app/log_ai_agent/ai_agent_v2/embedding/models/multilingual-e5-base

# --- ШАГ 3: Теперь копируем ВЕСЬ код ---
# Этот слой будет меняться часто, но он идет ПОСЛЕ тяжелых скачиваний   йй
COPY log_ai_agent/ ./log_ai_agent/

# Доустанавливаем проект (теперь с кодом) и чистим мусор
RUN uv pip install --system -e . && \
    find /usr/local/lib/python3.13/site-packages -type d \( -name tests -o -name test \) -prune -exec rm -rf '{}' + && \
    find /usr/local/lib/python3.13/site-packages -type d -name __pycache__ -prune -exec rm -rf '{}' + && \
    find /usr/local/lib/python3.13/site-packages -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

FROM python:3.13.0-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Пути остаются идентичными вашим
COPY --from=builder /usr/local /usr/local
COPY log_ai_agent/ ./log_ai_agent/
COPY --from=builder /app/log_ai_agent/ai_agent_v2/embedding/models /app/log_ai_agent/ai_agent_v2/embedding/models

RUN cp /app/log_ai_agent/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh \
    && sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /app/log_ai_agent
EXPOSE 8000
ENTRYPOINT ["bash", "/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "app.py"]