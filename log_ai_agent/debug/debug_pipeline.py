#!/usr/bin/env python3
"""Debug script: runs pipeline step by step with full verbose output.

Usage:
    cd log_ai_agent
    uv run python debug/debug_pipeline.py

Requires:
    - .env file with OLLAMA_URL / OLLAMA_MODEL
    - Ollama running
    - PostgreSQL + YaraRules / SigmaRules tables populated (optional)
    - ChromaDB initialized (optional)
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# ── ensure project is on sys.path ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# ── load .env ──────────────────────────────────────────────────────────
from dotenv import load_dotenv
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[ENV] Loaded .env from {env_path}")
else:
    print(f"[WARN] No .env at {env_path}")

# ── disable noisy logs ─────────────────────────────────────────────────
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("ai_agent_v2").setLevel(logging.WARNING)

# ── imports ─────────────────────────────────────────────────────────────
from log_ai_agent.ai_agent_v2.chains.agent1 import (
    create_agent1_chain,
    parse_groups_from_response,
    extract_mini_report,
)
from log_ai_agent.ai_agent_v2.chains.description_agent import generate_group_descriptions
from log_ai_agent.ai_agent_v2.chains.yara_generator import YaraGenerator
from log_ai_agent.ai_agent_v2.engines.yara_engine import YaraEngine
from log_ai_agent.ai_agent_v2.engines.sigma_engine import SigmaEngine
from log_ai_agent.ai_agent_v2.parsers.apache_parser import ApacheLogParser
from log_ai_agent.ai_agent_v2.chains.llm import create_llm
from log_ai_agent.ai_agent_v2.knowledge_base.manager import ChromaDBManager
from log_ai_agent.ai_agent_v2.knowledge_base.mitre_loader import initialize_mitre_knowledge_base
from log_ai_agent.ai_agent_v2.chains.rag_chain import rag_search_single_event

# ── helpers ─────────────────────────────────────────────────────────────

def safe_encode(text: str, maxlen: int = 0) -> str:
    """Encode text to ASCII-safe for Windows cp1251 console."""
    s = text[:maxlen] if maxlen else text
    return s.encode("ascii", errors="replace").decode("ascii")


def print_sep(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


async def main():
    # ── 0. Read sample log ──────────────────────────────────────────
    log_file = PROJECT_ROOT / "debug" / "sample_logs" / "incident.log"
    log_content = log_file.read_text(encoding="utf-8")
    lines = [l for l in log_content.split("\n") if l.strip()]
    print_sep(f"LOG FILE: {log_file.name} ({len(lines)} lines)")

    # ── 1. LLM (real Ollama) ────────────────────────────────────────
    print_sep("1. LLM SETUP")
    raw_ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    # Windows host can't resolve host.docker.internal — fix automatically
    if "host.docker.internal" in raw_ollama_url and sys.platform == "win32":
        raw_ollama_url = raw_ollama_url.replace("host.docker.internal", "localhost")
        print("   [FIX] Changed host.docker.internal -> localhost for local run")

    llm_config = {
        "ollama_url": raw_ollama_url,
    }
    if os.getenv("OLLAMA_MODEL"):
        llm_config["ollama_model"] = os.getenv("OLLAMA_MODEL")

    print(f"   Ollama URL:   {llm_config.get('ollama_url')}")
    print(f"   Model:        {llm_config.get('ollama_model') or os.getenv('OLLAMA_MODEL', 'not set')}")
    print(f"   Temperature:  {os.getenv('LLM_TEMPERATURE', '0.1')}")
    print(f"   Timeout:      {os.getenv('LLM_TIMEOUT', '90')}s")

    llm = create_llm(**llm_config)
    print("   [OK] LLM created")

    # ── 2. Agent 1 chain ────────────────────────────────────────────
    print_sep("2. AGENT 1 — RAW LLM CALL")
    chain = create_agent1_chain(llm)
    print("   Invoking LLM...")
    agent1_response = await chain.ainvoke({"log_content": log_content})

    print(f"\n   --- RAW RESPONSE (first 2000 chars) ---")
    print(safe_encode(agent1_response, 2000))
    print("   ... (truncated)")
    print("   --- END RAW RESPONSE ---")

    # ── 3. Parse groups from Agent 1 response ───────────────────────
    print_sep("3. AGENT 1 — PARSE GROUPS")

    has_groups_marker = "---GROUPS---" in agent1_response
    print(f"   Has ---GROUPS--- marker: {has_groups_marker}")

    mini_report = extract_mini_report(agent1_response)
    print(f"\n   Mini report:\n   {safe_encode(mini_report, 500)}")



    sm = "---GROUPS---"
    si = agent1_response.find(sm)
    if si != -1:
        si += len(sm)
        ei = agent1_response.find(sm, si)
        if ei == -1:
            ei = len(agent1_response)
        region = agent1_response[si:ei].strip()
        print(f"\n   JSON region ({len(region)} chars, has closing marker: {ei != len(agent1_response)})")

    groups = parse_groups_from_response(agent1_response)
    print(f"\n   Parsed groups: {len(groups)}")

    for g in groups:
        print(f"\n   -- Group {g['group_id']} --")
        print(f"      First seen: {g.get('first_seen', 'N/A')}")
        print(f"      Last seen:  {g.get('last_seen', 'N/A')}")
        print(f"      Events:     {len(g.get('events', []))}")
        print(f"      Keywords:   {g.get('keywords', [])}")
        print(f"      Description: {safe_encode(g.get('description', ''), 200)}...")
        for evt in g.get("events", []):
            st = evt.get('timestamp', 'N/A')
            desc = evt.get('description', 'N/A')
            print(f"        [{st}] {safe_encode(desc, 100)}")

    if not groups:
        print("\n   [!!] NO GROUPS PARSED — check the raw response above")
        print("   Agent 1 returned 0 groups. Debugging tips:")
        print("   1. Does ---GROUPS--- appear in the raw response?")
        print("   2. Is the JSON inside valid?")
        print("   3. Does the model follow the response format?")
        print("   Pipeline cannot continue without groups.")
        return

    # ── 4. Description Agent ────────────────────────────────────────
    print_sep("4. DESCRIPTION AGENT")
    try:
        descriptions = await generate_group_descriptions(llm=llm, groups=groups)
        print(f"   Generated {len(descriptions)} descriptions")
        for d in descriptions:
            print(f"\n   -- Group {d.get('group_id', '?')} --")
            print(f"      Description: {safe_encode(d.get('description', 'N/A'), 200)}")
            print(f"      Keywords:    {d.get('keywords_ru', [])}")
    except Exception as e:
        print(f"   [ERROR] Description Agent failed: {e}")
        descriptions = []

    if not descriptions:
        print("   No descriptions — RAG will be skipped")
        # Continue with empty descriptions

    # ── 5. YARA Engine ──────────────────────────────────────────────
    print_sep("5. YARA ENGINE")
    yara_path = PROJECT_ROOT / "ai_agent_v2" / "rules" / "yara"
    yara_engine = None
    if yara_path.exists():
        try:
            yara_engine = YaraEngine(str(yara_path))
            print(f"   YARA engine loaded: {yara_engine.rules_count} rule files")
        except Exception as e:
            print(f"   [WARN] YARA engine failed: {e}")
    else:
        print(f"   YARA rules path not found: {yara_path}")

    # ── 6. Sigma Engine ─────────────────────────────────────────────
    print_sep("6. SIGMA ENGINE")
    sigma_path = PROJECT_ROOT / "ai_agent_v2" / "rules" / "sigma"
    sigma_engine = None
    if sigma_path.exists():
        try:
            sigma_engine = SigmaEngine(str(sigma_path))
            print(f"   Sigma engine loaded: {len(sigma_engine._rules)} rules")
        except Exception as e:
            print(f"   [WARN] Sigma engine failed: {e}")
    else:
        print(f"   Sigma rules path not found: {sigma_path}")

    # ── 7. Parse logs + YARA/Sigma scan ─────────────────────────────
    print_sep("7. LOG SCANNING")

    parser = ApacheLogParser()
    parsed_logs = parser.parse(log_content)
    print(f"   Parsed {len(parsed_logs)} log entries")

    if yara_engine:
        yara_matches = yara_engine.scan(parsed_logs)
        print(f"   YARA matches: {len(yara_matches)}")
        for m in yara_matches:
            print(f"     - {m.get('rule', '?')}: {m.get('description', '')[:100]}")
    else:
        yara_matches = []
        print("   YARA scan skipped (no engine)")

    if sigma_engine:
        sigma_matches = sigma_engine.scan(parsed_logs)
        print(f"   Sigma matches: {len(sigma_matches)}")
        for m in sigma_matches:
            print(f"     - {m.get('title', '?')}: {m.get('description', '')[:100]}")
    else:
        sigma_matches = []
        print("   Sigma scan skipped (no engine)")

    # ── 8. ChromaDB + RAG (Agent 2) ─────────────────────────────────
    print_sep("8. RAG (AGENT 2)")
    chroma_mgr = None
    try:
        chroma_path = PROJECT_ROOT / "ai_agent_v2" / "chroma_db"
        chroma_mgr = initialize_mitre_knowledge_base(
            persist_directory=str(chroma_path),
        )
        if chroma_mgr and chroma_mgr.is_initialized:
            coll = chroma_mgr._vectorstore._client.get_collection(
                name=chroma_mgr.collection_name
            )
            print(f"   ChromaDB initialized: {coll.count()} documents")
        else:
            print("   ChromaDB not initialized")
    except Exception as e:
        print(f"   ChromaDB init failed: {e}")

    mitre_techniques = []
    if descriptions and chroma_mgr and chroma_mgr.is_initialized:
        for i, desc in enumerate(descriptions):
            description = desc.get("description", "")
            keywords = desc.get("keywords_ru", desc.get("keywords", []))
            print(f"\n   -- RAG search for group {desc.get('group_id', i)} --")
            print(f"      Description: {safe_encode(description, 150)}...")
            print(f"      Keywords:    {keywords}")
            try:
                rag_result = await rag_search_single_event(
                    llm=llm,
                    chroma_mgr=chroma_mgr,
                    description=description,
                    keywords=keywords,
                    k=5,
                    score_threshold=0.3,
                )
                print(f"      Result: has_match={rag_result.get('has_match')}, "
                      f"technique={rag_result.get('technique_id', 'N/A')} "
                      f"({rag_result.get('name', 'N/A')}) "
                      f"confidence={rag_result.get('confidence', 0):.3f}")
                if rag_result.get("has_match"):
                    mitre_techniques.append(rag_result)
            except Exception as e:
                print(f"      [ERROR] RAG failed: {e}")
    else:
        print("   RAG skipped (no descriptions or ChromaDB)")

    print(f"\n   Total MITRE techniques found: {len(mitre_techniques)}")

    # ── 9. YARA Generator ───────────────────────────────────────────
    print_sep("9. YARA GENERATOR")
    if mitre_techniques:
        try:
            yara_gen = YaraGenerator(llm=llm, chroma_mgr=chroma_mgr)
            for t in mitre_techniques:
                print(f"\n   -- Generating rule for {t.get('technique_id', '?')} --")
                print(f"      Name:          {t.get('name', 'N/A')}")
                print(f"      Confidence:    {t.get('confidence', 0):.3f}")

                log_lines = [p.get("raw", "") for p in parsed_logs if p.get("raw", "")]

                print(f"      Log lines:     {len(log_lines)}")

                matching_group = next(
                    (g for g in groups if g.get("group_id") == t.get("group_id", "")),
                    None
                )
                rule = await yara_gen.generate(
                    technique=t,
                    group=matching_group,
                    parsed_logs=parsed_logs,
                )

                if rule:
                    print(f"      [OK] Generated rule: {rule.rule_name}")
                    print(f"      Content (first 300 chars):")
                    print(f"      {rule.rule_content[:300]}")
                else:
                    print(f"      [!!] Generation failed (validation rejected)")

        except Exception as e:
            print(f"   [ERROR] YARA Generator: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("   No MITRE techniques found — skipping YARA generation")

    # ── 10. Summary ─────────────────────────────────────────────────
    print_sep("SUMMARY")
    print(f"   Log file:         {log_file.name}")
    print(f"   Lines:            {len(lines)}")
    print(f"   Groups (Agent 1): {len(groups)}")
    print(f"   Descriptions:     {len(descriptions)}")
    print(f"   MITRE techniques: {len(mitre_techniques)}")
    print(f"   YARA matches:     {len(yara_matches)}")
    print(f"   Sigma matches:    {len(sigma_matches)}")
    print()
    print("   Done!")


if __name__ == "__main__":
    asyncio.run(main())
