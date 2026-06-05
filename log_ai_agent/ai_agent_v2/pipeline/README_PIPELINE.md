# Pipeline Architecture

## Overview

This document describes the LangGraph-based analysis pipeline for processing security logs.

## Pipeline Flow

```
┌─────────────────────────────────────────────┐
│           log_content (input)              │
└────┬────────────┬─────────────┬───────────┘
     │            │             │
┌────▼────┐ ┌───▼─────┐ ┌───▼──────┐
│Prefilter │ │parse_log│ │  YARA     │
└────┬────┘ └────┬─────┘ └────┬─────┘
     │            │             │
┌────▼────┐     │       ┌─────▼─────┐
│ Agent 1 │     │       │  Sigma    │
└────┬────┘     └───────┴────┬─────┘
     │                        │
     │            ┌──────────┴──────────┐
     ▼            │                     ▼
┌──────────────────┴────┐      ┌──────────┐
│  Description Agent   │      │ Agent 3  │
└──────────────┬───────┘      └──────────┘
               │
┌──────────────▼───────┐
│       Agent 2 (RAG)  │──────▶│ Agent 3 │
└──────────────────────┘       └──────────┘
```

## Nodes

### 1. Prefilter Node
- **Input**: `log_content` (raw log data)
- **Output**: `log_content` (filtered), `prefilter_stats`
- **Purpose**: Lightweight filtering to reduce volume before expensive LLM processing

### 2. Agent 1 (Primary Analysis)
- **Input**: `log_content` (filtered)
- **Output**: `primary_analysis`, `mini_report`, `groups`, `events_found`
- **Purpose**: Analyze logs and identify suspicious activity, output groups of related events
- **Key Feature**: Groups events by potential connection (user, attack_pattern, IP, etc.), **NOT by timestamp**

### 3. Description Agent
- **Input**: `groups` (from Agent 1)
- **Output**: `group_descriptions`
- **Purpose**: Generate coherent descriptions for each event group
- **Key Feature**: Parallel processing, one description per group

### 4. Agent 2 (RAG Search)
- **Input**: `group_descriptions`
- **Output**: `mitre_context`, `mitre_techniques_final`, `technique_ids`
- **Purpose**: Search MITRE ATT&CK knowledge base for each group description
- **Key Feature**: Improved accuracy by searching on rich group descriptions instead of individual log lines

### 5. YARA Scan
- **Input**: `parsed_logs`
- **Output**: `yara_matches`, `yara_rules_matched`, `yara_context`
- **Purpose**: Rule-based malware detection

### 6. Sigma Scan
- **Input**: `parsed_logs`
- **Output**: `sigma_matches`, `sigma_rules_matched`, `sigma_context`
- **Purpose**: Rule-based SIEM detection

### 7. Agent 3 (Final Report)
- **Input**: All previous nodes' outputs
- **Output**: `final_report`, `severity_level_id`, `threat_type_id`, `recommendations`
- **Purpose**: Generate comprehensive security incident report

### 8. YARA Generator (Post-processing)
- **Input**: MITRE techniques from Agent 2, existing YARA rules
- **Output**: Generated YARA rules (saved to DB as suggestions)
- **Purpose**: Auto-generate YARA rules for uncovered MITRE techniques
- **How it works**:
  1. For each MITRE technique found by RAG, checks if already covered by existing YARA rules
  2. If uncovered → LLM generates a YARA rule for the technique using log samples as reference
  3. Rule is validated: compiled with `yara-python`, scanned against original logs, reviewed by LLM
  4. If passes all checks → saved as a `PendingYaraRule` (visible in Web UI as suggestion)
  5. Admin can accept/reject via Web UI

## Data Types

### EventGroup
```python
{
    "group_id": str,        # Unique identifier (g1, g2, ...)
    "events": [             # List of related events
        {
            "description": str,
            "timestamp": str,
            "log_line": str
        }
    ],
    "first_seen": str,      # Timestamp of first event in group
    "last_seen": str,       # Timestamp of last event in group
    "keywords": list[str], # English keywords for RAG search
    "description": str      # Detailed description from Agent1 (optional)
}
```

### GroupDescription
```python
{
    "group_id": str,        # Same as EventGroup.group_id
    "description": str,      # Coherent description (e.g., "Series of 15 SSH brute-force attempts...")
    "first_seen": str,       # From EventGroup
    "last_seen": str,        # From EventGroup
    "keywords": list[str] # English keywords for RAG search
}
```

## State Management

### AnalysisState Fields
```python
{
    # Input
    "log_content": str,
    "parsed_logs": list[ParsedLog],

    # Agent 1 Output
    "primary_analysis": str,
    "mini_report": str,
    "groups": list[EventGroup],
    "events_found": int,

    # Description Agent Output
    "group_descriptions": list[GroupDescription],

    # RAG + Agent 2 Output
    "mitre_context": str,
    "mitre_techniques_final": list[MITRETechnique],
    "technique_ids": list[str],

    # YARA/Sigma Output
    "yara_matches": list,
    "yara_rules_matched": list[str],
    "yara_context": str,
    "sigma_matches": list,
    "sigma_rules_matched": list[str],
    "sigma_context": str,

    # Agent 3 Output
    "final_report": str,
    "recommendations": list[str],
    "severity_level_id": int,
    "threat_type_id": int,
}
```

## Grouping Logic (Agent 1)

Agent 1 groups events based on potential connections:
- **User**: Same username across multiple events
- **IP Address**: Same source IP
- **Attack Pattern**: Similar attack type (brute-force, SQL injection, etc.)
- **Service/Destination**: Same target service
- **Request Path**: Same URL/path being accessed

**Important**:
- Groups are NOT based on timestamp (logs already arrive at 5-minute intervals)
- One event CAN belong to multiple groups if it relates to different activities
- If an event is suspicious but unrelated to others, it forms a single-event group

## RAG Improvement

### Before (Individual Events)
- Problem: Similar events from different techniques produce similar embeddings
- Example: T1110 and T1187 both produce "Authentication failed" logs
- Result: RAG confusion and wrong technique retrieval

### After (Group Descriptions)
- Solution: Richer context from grouped events
- Example: "15 SSH brute-force attempts for user admin from IP 89.23.74.19"
- Result: More distinctive embedding, better MITRE matching

## Usage

```python
from log_ai_agent.ai_agent_v2.pipeline.langgraph_pipeline import create_pipeline

async def analyze():
    pipeline = await create_pipeline(
        chroma_path="./chroma_db",
        use_rag=True,
    )
    result = await pipeline.analyze(log_content)
    print(result["final_report"])
```

## Testing

Run tests:
```bash
uv run pytest log_ai_agent/ai_agent_v2/pipeline_tests/
```

Key test files:
- `test_agent1.py` - Tests Agent 1 grouping logic
- `test_rag.py` - Tests RAG search accuracy
- `test_full_pipeline.py` - End-to-end pipeline test