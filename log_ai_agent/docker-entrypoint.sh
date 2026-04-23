#!/bin/bash
# docker-entrypoint.sh — Download embedding model and start the app

set -e

MODEL_DIR="/app/log_ai_agent/ai_agent_v2/embedding/models/multilingual-e5-base"
HF_CACHE="${HF_HOME:-/root/.cache/huggingface}/models--intfloat--multilingual-e5-base"

download_model() {
    echo "=== Downloading embedding model ==="
    echo "  Target: $MODEL_DIR"
    
    mkdir -p "$MODEL_DIR"
    
    # Try 1: Copy from HF cache if present
    if [ -f "$HF_CACHE/refs/main" ]; then
        echo "  Found in HF cache, copying..."
        COMMIT=$(cat "$HF_CACHE/refs/main")
        cp -r "$HF_CACHE/snapshots/$COMMIT/"* "$MODEL_DIR/" 2>/dev/null && {
            echo "  ✓ Copied from cache"
            return 0
        }
    fi
    
    # Try 2: Download from HuggingFace
    echo "  Not in cache, downloading from HuggingFace (~1.1 GB)..."
    if hf download intfloat/multilingual-e5-base --local-dir "$MODEL_DIR" 2>/dev/null; then
        echo "  ✓ Downloaded"
        return 0
    fi
    
    # Try 3: Python fallback
    echo "  Trying Python download..."
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('intfloat/multilingual-e5-base', local_dir='$MODEL_DIR', local_dir_use_symlinks=False)
" && {
        echo "  ✓ Downloaded via Python"
        return 0
    }
    
    echo "  ✗ Failed to download embedding model!"
    echo "  RAG will be disabled. Pipeline will continue without MITRE ATT&CK."
    return 1
}

# Download model (non-blocking)
if [ -d "$MODEL_DIR/config.json" ]; then
    echo "=== Embedding model already present ==="
else
    download_model || true
fi

# Start the application
echo "=== Starting AI-CyberLogAgent ==="
exec python app.py
