"""Загрузка техник MITRE ATT&CK из локального STIX JSON файла."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_techniques_from_stix(stix_path: Path | None = None) -> list[dict]:
    """Загрузить техники из STIX JSON файла.

    Args:
        stix_path: Путь к файлу STIX JSON. Если None, используется путь по умолчанию.

    Returns:
        List of technique dictionaries

    """
    if stix_path is None:
        # Путь по умолчанию относительно этого файла
        base_dir = Path(__file__).parent.parent
        stix_path = base_dir / "mitre_data" / "enterprise-attack.json"

    if not stix_path.exists():
        logger.error(f"STIX file not found: {stix_path}")
        return []

    logger.info(f"Loading techniques from {stix_path}...")

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

    logger.info(f"✓ Extracted {len(techniques)} techniques from local STIX file")
    return techniques
