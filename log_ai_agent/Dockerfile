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

# Install huggingface_hub + hf_transfer for model download
RUN uv pip install --system huggingface_hub hf_transfer
WORKDIR /app

COPY pyproject.toml ./
COPY log_ai_agent/ ./log_ai_agent/

# Install CPU torch and project dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --index-url https://download.pytorch.org/whl/cpu torch && \
    uv pip install --system -e . && \
    find /usr/local/lib/python3.13/site-packages -type d \( -name tests -o -name test \) -prune -exec rm -rf '{}' + && \
    find /usr/local/lib/python3.13/site-packages -type d -name __pycache__ -prune -exec rm -rf '{}' + && \
    find /usr/local/lib/python3.13/site-packages -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

# Download embedding model at build time (~1.1 GB, CPU)
RUN pip install tqdm && \
    huggingface-cli download intfloat/multilingual-e5-base \
    --local-dir /app/log_ai_agent/ai_agent_v2/embedding/models/multilingual-e5-base

FROM python:3.13.0-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime needs bash for the entrypoint script.
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Копируем готовый Python runtime из builder, затем код, затем модель (последней чтобы не перезаписалась)
COPY --from=builder /usr/local /usr/local
COPY log_ai_agent/ ./log_ai_agent/
COPY --from=builder /app/log_ai_agent/ai_agent_v2/embedding/models /app/log_ai_agent/ai_agent_v2/embedding/models

# Copy entrypoint script to a non-mounted location (prevents CRLF from host bind mount)
RUN cp /app/log_ai_agent/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh \
    && sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /app/log_ai_agent

EXPOSE 8000

ENTRYPOINT ["bash", "/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "app.py"]
