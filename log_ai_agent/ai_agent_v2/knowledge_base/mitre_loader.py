"""MITRE ATT&CK knowledge base initializer.

Priority:
1. Use existing ChromaDB if already populated
2. Load from local STIX JSON file (mitre_data/enterprise-attack.json)
3. Download from GitHub and save locally (fallback)
"""

import logging
from pathlib import Path

from .manager import ChromaDBManager

logger = logging.getLogger(__name__)


def initialize_mitre_knowledge_base(
    persist_directory: str,
    collection_name: str = "mitre_collection",
    embedding_model: str | None = None,
    domain: str = "enterprise-attack",
) -> ChromaDBManager:
    """Initialize ChromaDB and populate with MITRE ATT&CK data.

    Args:
        persist_directory: Directory to store ChromaDB
        collection_name: Name of the collection
        embedding_model: Embedding model to use
        domain: MITRE domain (not used with GitHub)

    Returns:
        Initialized ChromaDBManager

    """
    logger.info("Initializing MITRE ATT&CK knowledge base...")

    # Initialize ChromaDB
    chroma_mgr = ChromaDBManager(
        persist_directory=persist_directory,
        collection_name=collection_name,
        embedding_model=embedding_model,
    )

    # Check if already initialized
    has_data = chroma_mgr.initialize()

    if has_data:
        logger.info("✓ MITRE ATT&CK knowledge base already exists")
        return chroma_mgr

    # Try to load from local STIX file first (faster, no network)
    stix_file = Path(persist_directory).parent / "mitre_data" / "enterprise-attack.json"
    if stix_file.exists():
        logger.info(f"Loading MITRE ATT&CK from local file: {stix_file}")
        from .local_loader import load_techniques_from_stix

        techniques = load_techniques_from_stix(stix_file)
        if techniques:
            count = chroma_mgr.load_mitre_techniques(techniques)
            logger.info(
                f"✓ Knowledge base initialized with {count} techniques from local file"
            )
            return chroma_mgr

    # Fallback: Download from GitHub and load
    logger.info("Local MITRE data not found. Downloading from GitHub...")
    try:
        from .github_loader import download_and_load_mitre

        count = download_and_load_mitre(chroma_mgr, stix_file)
        logger.info(f"✓ Knowledge base initialized with {count} techniques from GitHub")
        return chroma_mgr
    except Exception as e:
        logger.error(f"Failed to load MITRE data from GitHub: {e}")
        raise RuntimeError(f"Failed to load MITRE ATT&CK data: {e}")
