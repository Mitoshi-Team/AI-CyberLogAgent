#!/usr/bin/env python3
"""Загрузка полной базы MITRE ATT&CK из локального JSON файла в ChromaDB."""

import asyncio
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from log_ai_agent.ai_agent_v2.knowledge_base.manager import ChromaDBManager


def load_techniques_from_stix(stix_path: Path) -> list[dict]:
    """Загрузить техники из STIX JSON файла.

    Args:
        stix_path: Путь к файлу STIX JSON

    Returns:
        List of technique dictionaries

    """
    print(f"Загрузка техник из {stix_path}...")

    with open(stix_path, encoding="utf-8") as f:
        data = json.load(f)

    techniques = []
    objects = data.get("objects", [])

    for obj in objects:
        # Только техники (attack-pattern)
        if obj.get("type") != "attack-pattern":
            continue

        # Извлечь внешний ID (Txxxx)
        external_id = ""
        external_refs = obj.get("external_references", [])
        for ref in external_refs:
            if ref.get("external_id", "").startswith("T"):
                external_id = ref["external_id"]
                break

        # Извлечь тактику
        tactic = "Unknown"
        kill_chain_phases = obj.get("kill_chain_phases", [])
        if kill_chain_phases:
            tactic = kill_chain_phases[0].get("phase_name", "Unknown")

        # Извлечь платформы
        platforms = obj.get("x_mitre_platforms", [])

        # Извлечь источники данных
        data_sources = obj.get("x_mitre_data_sources", [])

        technique = {
            "technique_id": external_id,
            "technique_name": obj.get("name", ""),
            "description": obj.get("description", ""),
            "tactic": tactic,
            "platforms": platforms,
            "data_sources": data_sources,
        }
        techniques.append(technique)

    print(f"✓ Извлечено {len(techniques)} техник")
    return techniques


async def main():
    """Загрузить полную базу MITRE в ChromaDB."""
    chroma_path = project_root / "log_ai_agent" / "ai_agent_v2" / "chroma_db"
    stix_file = (
        project_root
        / "log_ai_agent"
        / "ai_agent_v2"
        / "mitre_data"
        / "enterprise-attack.json"
    )

    print("=" * 60)
    print("  Загрузка полной базы MITRE ATT&CK в ChromaDB")
    print("=" * 60)

    # Проверка наличия STIX файла
    if not stix_file.exists():
        print(f"✗ Файл не найден: {stix_file}")
        print("Сначала запустите download_mitre.py")
        sys.exit(1)

    # Очистка существующей базы
    import shutil

    if chroma_path.exists():
        print(f"Очистка существующей базы: {chroma_path}")
        shutil.rmtree(chroma_path)

    # Инициализация ChromaDB
    print("\nИнициализация ChromaDB...")
    chroma_mgr = ChromaDBManager(
        persist_directory=str(chroma_path),
        collection_name="mitre_collection",
    )

    chroma_mgr.initialize()

    # Загрузка техник из STIX
    print("\nОбработка техник MITRE ATT&CK...")
    techniques = load_techniques_from_stix(stix_file)

    if not techniques:
        print("✗ Не удалось извлечь техники")
        sys.exit(1)

    # Загрузка в ChromaDB
    print(f"\nЗагрузка {len(techniques)} техник в ChromaDB (это может занять время)...")
    count = chroma_mgr.load_mitre_techniques(techniques)

    print(f"\n✓ Успешно загружено {count} техник MITRE ATT&CK")
    print(f"  Путь к базе: {chroma_path}")
    print("\nТеперь можно запустить test_rag_flow.py")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
