#!/bin/bash
set -e

CHROMA_DB="/app/log_ai_agent/ai_agent_v2/chroma_db"

if [ -f "$CHROMA_DB/chroma.sqlite3" ]; then
    echo "=== MITRE ATT&CK already initialized ==="
else
    echo "=== Initializing MITRE ATT&CK knowledge base ==="
    python /app/log_ai_agent/ai_agent_v2/init_mitre.py
    echo "=== MITRE ATT&CK loaded ==="
fi

exec python app.py