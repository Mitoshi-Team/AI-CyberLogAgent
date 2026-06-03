#!/usr/bin/env python
from pathlib import Path
from log_ai_agent.ai_agent_v2.knowledge_base.mitre_loader import (
    initialize_mitre_knowledge_base,
)

chroma_path = Path(__file__).parent / "chroma_db"
print(f"Initializing MITRE knowledge base at: {chroma_path}")
initialize_mitre_knowledge_base(str(chroma_path))
print("Done")