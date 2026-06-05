"""MITRE ATT&CK knowledge base initializer.

Loads the project-bundled mitre_processed.json (a curated/modified subset
of MITRE ATT&CK techniques) into ChromaDB. No external downloads.
"""

import json
import logging
from pathlib import Path

from .manager import ChromaDBManager

logger = logging.getLogger(__name__)


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


def initialize_mitre_knowledge_base(
    persist_directory: str,
    collection_name: str = "mitre_collection",
    embedding_model: str | None = None,
) -> ChromaDBManager:
    """Initialize ChromaDB and populate with MITRE ATT&CK data.

    Loads from the project-bundled mitre_processed.json file only.
    Raises FileNotFoundError if the file is missing.

    Args:
        persist_directory: Directory to store ChromaDB
        collection_name: Name of the collection
        embedding_model: Embedding model to use

    Returns:
        Initialized ChromaDBManager

    Raises:
        FileNotFoundError: If mitre_processed.json is not found
        RuntimeError: If no techniques could be loaded

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

    processed_file = (
        Path(persist_directory).parent / "knowledge_base" / "mitre_processed.json"
    )

    if not processed_file.exists():
        raise FileNotFoundError(
            f"MITRE processed file not found at {processed_file}. "
            f"Ensure mitre_processed.json is included in the deployment."
        )

    techniques = _load_processed_techniques(processed_file)
    if not techniques:
        raise RuntimeError(f"No techniques found in {processed_file}")

    count = chroma_mgr.load_mitre_techniques(techniques)
    logger.info(
        f"Knowledge base initialized with {count} processed techniques"
    )
    return chroma_mgr
