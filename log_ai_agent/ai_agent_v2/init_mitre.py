#!/usr/bin/env python
from log_ai_agent.ai_agent_v2.knowledge_base.mitre_loader import (
    initialize_mitre_knowledge_base,
)

initialize_mitre_knowledge_base("/app/log_ai_agent/ai_agent_v2/chroma_db")
