#!/bin/bash
set -e

MODEL_DIR="/app/log_ai_agent/ai_agent_v2/embedding/models/multilingual-e5-base"
MODEL_NAME="intfloat/multilingual-e5-base"
MAX_RETRIES=3
TIMEOUT_SECONDS=600

download_model() {
    local attempt=1
    local wait_times=(10 30 60)

    while [ $attempt -le $MAX_RETRIES ]; do
        echo "=== Downloading embedding model (attempt $attempt/$MAX_RETRIES) ==="
        echo "  Target: $MODEL_DIR"
        echo "  Model: $MODEL_NAME"
        echo "  Timeout: ${TIMEOUT_SECONDS}s"

        mkdir -p "$MODEL_DIR"

        python3 << 'PYEOF' || {
            exit_code=$?
            if [ $exit_code -eq 104 ]; then
                echo "  HTTP 429 - Rate limited, waiting ${wait_times[$((attempt-1))]}s..."
                exit 104
            fi
            echo "  Download failed with exit code: $exit_code"
            exit $exit_code
        }
import sys
import os
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
from huggingface_hub import snapshot_download

try:
    print("  Starting download (~1.1 GB)...")
    snapshot_download(
        local_dir="$MODEL_DIR",
        local_dir_use_symlinks=False,
    )
    print("  Download completed!")
    sys.exit(0)
except Exception as e:
    error_msg = str(e)
    print(f"  Error: {error_msg}")
    if "429" in error_msg or "rate" in error_msg.lower():
        sys.exit(104)
    sys.exit(1)
PYEOF

        exit_code=$?

        if [ $exit_code -eq 0 ]; then
            echo "  Success!"
            return 0
        elif [ $exit_code -eq 104 ]; then
            wait_time=${wait_times[$((attempt-1))]}
            echo "  Rate limited, waiting ${wait_time}s before retry..."
            sleep $wait_time
            attempt=$((attempt + 1))
            continue
        else
            echo "  Attempt $attempt failed, trying again..."
            attempt=$((attempt + 1))
            sleep 5
        fi
    done

    echo "  Failed to download after $MAX_RETRIES attempts!"
    echo "  RAG will be disabled. Pipeline will continue without MITRE ATT&CK."
    return 1
}

check_model() {
    [ -f "$MODEL_DIR/config.json" ] && [ -f "$MODEL_DIR/model.safetensors" ]
}

if [ "${SKIP_EMBEDDING_DOWNLOAD:-0}" = "1" ]; then
    echo "=== Embedding model download skipped (SKIP_EMBEDDING_DOWNLOAD=1) ==="
elif check_model; then
    echo "=== Embedding model already present ==="
else
    echo "=== Embedding model not found, downloading... ==="
    download_model || true
fi

echo "=== Starting AI-CyberLogAgent ==="
exec python app.py