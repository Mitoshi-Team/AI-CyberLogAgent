"""MITRE ATT&CK knowledge base initializer.

Priority:
1. Use existing ChromaDB if already populated
2. Load from local STIX JSON file (mitre_data/enterprise-attack.json)
3. Download from GitHub and save locally (fallback)
"""

import json
import logging
from pathlib import Path

import requests

from .manager import ChromaDBManager

logger = logging.getLogger(__name__)

MITRE_GITHUB_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"


def _load_techniques_from_stix(stix_path: Path) -> list[dict]:
    """Load techniques from STIX JSON file.

    Args:
        stix_path: Path to STIX JSON file

    Returns:
        List of technique dictionaries
    """
    logger.info(f"Loading techniques from {stix_path}...")

    with open(stix_path, encoding="utf-8") as f:
        data = json.load(f)

    techniques = []
    for obj in data.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue

        external_id = ""
        for ref in obj.get("external_references", []):
            if ref.get("external_id", "").startswith("T"):
                external_id = ref["external_id"]
                break

        if not external_id:
            continue

        tactic = "Unknown"
        kill_chain_phases = obj.get("kill_chain_phases", [])
        if kill_chain_phases:
            tactic = kill_chain_phases[0].get("phase_name", "Unknown")

        technique = {
            "technique_id": external_id,
            "technique_name": obj.get("name", ""),
            "description": obj.get("description", ""),
            "tactic": tactic,
            "platforms": obj.get("x_mitre_platforms", []),
            "data_sources": obj.get("x_mitre_data_sources", []),
        }
        techniques.append(technique)

    logger.info(f"Extracted {len(techniques)} techniques from STIX file")
    return techniques


def _load_summarized_techniques(summary_path: Path) -> list[dict]:
    """Load pre-summarized techniques from JSON file.

    Args:
        summary_path: Path to summarized JSON file

    Returns:
        List of technique dictionaries with 'summary' field
    """
    logger.info(f"Loading summarized techniques from {summary_path}...")

    with open(summary_path, encoding="utf-8") as f:
        summarized = json.load(f)

    techniques = []
    for item in summarized:
        technique = {
            "technique_id": item.get("external_id", ""),
            "technique_name": item.get("name", ""),
            "description": item.get("summary", item.get("original_description", "")),
            "summary": item.get("summary"),
            "tactic": item.get("tactic", "Unknown"),
        }
        techniques.append(technique)

    logger.info(f"Loaded {len(techniques)} summarized techniques")
    return techniques


def _load_processed_techniques(processed_path: Path) -> list[dict]:
    """Load processed techniques from clean JSON file.

    This file has only main techniques (no sub-techniques) with fields:
    - technique_id
    - technique_name
    - description
    - tactic

    Args:
        processed_path: Path to processed JSON file (mitre_processed.json)

    Returns:
        List of technique dictionaries
    """
    logger.info(f"Loading processed techniques from {processed_path}...")

    with open(processed_path, encoding="utf-8") as f:
        techniques = json.load(f)

    logger.info(f"Loaded {len(techniques)} processed techniques")
    return techniques


def _download_mitre_from_github(output_path: Path) -> bool:
    """Download MITRE ATT&CK from GitHub and save locally.

    Args:
        output_path: Path to save JSON file

    Returns:
        True if successful

    """
    logger.info("Downloading MITRE ATT&CK from GitHub...")
    logger.info(f"URL: {MITRE_GITHUB_URL}")

    try:
        response = requests.get(MITRE_GITHUB_URL, timeout=120)
        response.raise_for_status()

        attack_data = response.json()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(attack_data, f, ensure_ascii=False, indent=2)

        obj_count = len(attack_data.get("objects", []))
        logger.info(f"Downloaded and saved {obj_count} objects to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to download MITRE data: {e}")
        return False


def initialize_mitre_knowledge_base(
    persist_directory: str,
    collection_name: str = "mitre_collection",
    embedding_model: str | None = None,
    domain: str = "enterprise-attack",
    use_processed: bool = True,
) -> ChromaDBManager:
    """Initialize ChromaDB and populate with MITRE ATT&CK data.

    Args:
        persist_directory: Directory to store ChromaDB
        collection_name: Name of the collection
        embedding_model: Embedding model to use
        domain: MITRE domain (not used with GitHub)
        use_processed: Whether to use processed JSON (mitre_processed.json)

    Returns:
        Initialized ChromaDBManager
    """
    logger.info("Initializing MITRE ATT&CK knowledge base...")

    chroma_mgr = ChromaDBManager(
        persist_directory=persist_directory,
        collection_name=collection_name,
        embedding_model=embedding_model,
    )

    has_data = chroma_mgr.initialize()
    if has_data:
        logger.info("MITRE ATT&CK knowledge base already exists")
        return chroma_mgr

    # Try processed techniques first (clean JSON with only main techniques)
    if use_processed:
        processed_file = Path(persist_directory).parent / "knowledge_base" / "mitre_processed.json"
        if processed_file.exists():
            logger.info(f"Loading processed techniques from: {processed_file}")
            techniques = _load_processed_techniques(processed_file)
            if techniques:
                count = chroma_mgr.load_mitre_techniques(techniques)
                logger.info(
                    f"Knowledge base initialized with {count} processed techniques"
                )
                return chroma_mgr
            else:
                logger.warning("No techniques in processed file, falling back to STIX")

    # Fallback to STIX file
    stix_file = Path(persist_directory).parent / "mitre_data" / "enterprise-attack.json"
    if stix_file.exists():
        logger.info(f"Loading MITRE ATT&CK from local file: {stix_file}")
        techniques = _load_techniques_from_stix(stix_file)
        if techniques:
            count = chroma_mgr.load_mitre_techniques(techniques)
            logger.info(
                f"Knowledge base initialized with {count} techniques from local file"
            )
            return chroma_mgr

    logger.info("Local MITRE data not found. Downloading from GitHub...")
    try:
        if not _download_mitre_from_github(stix_file):
            raise RuntimeError("Failed to download MITRE data from GitHub")

        techniques = _load_techniques_from_stix(stix_file)
        if not techniques:
            raise RuntimeError("No techniques extracted from downloaded MITRE data")

        count = chroma_mgr.load_mitre_techniques(techniques)
        logger.info(f"Knowledge base initialized with {count} techniques from GitHub")
        return chroma_mgr

    except Exception as e:
        logger.error(f"Failed to load MITRE data: {e}")
        raise RuntimeError(f"Failed to load MITRE ATT&CK data: {e}")
