# syntax=docker/dockerfile:1
FROM python:3.13.0-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Build-зависимости оставляем только в builder-слое.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Install huggingface_hub CLI for model download
RUN uv pip install --system huggingface_hub

WORKDIR /app

COPY pyproject.toml ./
COPY log_ai_agent/ ./log_ai_agent/

# Устанавливаем CPU-сборку torch, чтобы не тянуть CUDA runtime в контейнер.
# Функциональность RAG/embeddings при этом сохраняется.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --index-url https://download.pytorch.org/whl/cpu torch && \
    uv pip install --system -e . && \
    find /usr/local/lib/python3.13/site-packages -type d \( -name tests -o -name test \) -prune -exec rm -rf '{}' + && \
    find /usr/local/lib/python3.13/site-packages -type d -name __pycache__ -prune -exec rm -rf '{}' + && \
    find /usr/local/lib/python3.13/site-packages -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

FROM python:3.13.0-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Копируем только готовый Python runtime из builder.
COPY --from=builder /usr/local /usr/local
COPY log_ai_agent/ ./log_ai_agent/

# Copy entrypoint script
RUN chmod +x /app/log_ai_agent/docker-entrypoint.sh

WORKDIR /app/log_ai_agent

EXPOSE 8000

# Download model at startup, then start app
ENTRYPOINT ["/app/log_ai_agent/docker-entrypoint.sh"]