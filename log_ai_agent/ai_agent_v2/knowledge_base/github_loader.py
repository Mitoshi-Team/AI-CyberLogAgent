"""Загрузка MITRE ATT&CK с GitHub и сохранение локально."""

import json
import logging
from pathlib import Path

import requests

from .local_loader import load_techniques_from_stix

logger = logging.getLogger(__name__)

# Прямая ссылка на актуальную версию MITRE ATT&CK Enterprise
MITRE_GITHUB_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"


def download_mitre_from_github(output_path: Path) -> bool:
    """Загрузить MITRE ATT&CK Enterprise с GitHub и сохранить в файл.

    Args:
        output_path: Путь для сохранения JSON файла

    Returns:
        True если загрузка успешна

    """
    logger.info("Downloading MITRE ATT&CK from GitHub...")
    logger.info(f"URL: {MITRE_GITHUB_URL}")

    try:
        response = requests.get(MITRE_GITHUB_URL, timeout=120)
        response.raise_for_status()

        attack_data = response.json()

        # Сохранение в файл
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(attack_data, f, ensure_ascii=False, indent=2)

        obj_count = len(attack_data.get("objects", []))
        logger.info(f"✓ Downloaded and saved {obj_count} objects to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to download MITRE data: {e}")
        return False


def download_and_load_mitre(chroma_mgr, stix_file: Path) -> int:
    """Скачать MITRE с GitHub, сохранить локально и загрузить в ChromaDB.

    Args:
        chroma_mgr: ChromaDB менеджер для загрузки данных
        stix_file: Путь для сохранения STIX JSON файла

    Returns:
        Количество загруженных техник

    """
    # Скачать с GitHub
    if not download_mitre_from_github(stix_file):
        raise RuntimeError("Failed to download MITRE data from GitHub")

    # Загрузить техники из локального файла
    techniques = load_techniques_from_stix(stix_file)

    if not techniques:
        raise RuntimeError("No techniques extracted from downloaded MITRE data")

    # Загрузить в ChromaDB
    count = chroma_mgr.load_mitre_techniques(techniques)

    return count
