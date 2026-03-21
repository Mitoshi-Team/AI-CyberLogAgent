"""MITRE ATT&CK data loader for ChromaDB."""

import json
import logging
from typing import Optional

from mitreattack.stix20 import MitreAttackData

from .chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


class MitreLoader:
    """
    Loads MITRE ATT&CK data and populates ChromaDB.
    
    Uses mitreattack-python library to fetch technique data.
    """

    def __init__(self, chroma_manager: ChromaManager):
        """
        Initialize MITRE loader.
        
        Args:
            chroma_manager: Initialized ChromaManager instance
        """
        self.chroma_manager = chroma_manager
        self.mitre_data: Optional[MitreAttackData] = None

    def load_mitre_data(self, domain: str = "enterprise-attack") -> bool:
        """
        Load MITRE ATT&CK data using mitreattack-python.
        
        Args:
            domain: MITRE domain (enterprise-attack, ics-attack, mobile-attack)
            
        Returns:
            True if loading successful
        """
        try:
            logger.info(f"Loading MITRE ATT&CK data: {domain}")
            self.mitre_data = MitreAttackData(domain)
            logger.info(f"Loaded MITRE ATT&CK: {domain}")
            return True
        except Exception as e:
            logger.error(f"Failed to load MITRE ATT&CK data: {e}")
            return False

    def extract_techniques(self) -> list[dict]:
        """
        Extract techniques from loaded MITRE data.
        
        Returns:
            List of technique dictionaries with id, name, description, tactic
        """
        if not self.mitre_data:
            raise ValueError("MITRE data not loaded. Call load_mitre_data first.")
        
        techniques = []
        
        try:
            # Get all techniques
            stix_objects = self.mitre_data.get_objects_by_type("attack-pattern")
            
            for obj in stix_objects:
                try:
                    technique = {
                        "technique_id": obj.get("external_references", [{}])[0].get("external_id", ""),
                        "technique_name": obj.get("name", ""),
                        "description": obj.get("description", ""),
                        "tactic": self._get_primary_tactic(obj),
                        "platforms": obj.get("x_mitre_platforms", []),
                        "permissions_required": obj.get("x_mitre_permissions_required", []),
                        "data_sources": obj.get("x_mitre_data_sources", []),
                    }
                    techniques.append(technique)
                except Exception as e:
                    logger.warning(f"Error extracting technique: {e}")
                    continue
            
            logger.info(f"Extracted {len(techniques)} techniques from MITRE ATT&CK")
            return techniques
            
        except Exception as e:
            logger.error(f"Error extracting techniques: {e}")
            return []

    def _get_primary_tactic(self, obj) -> str:
        """Get primary tactic for a technique."""
        try:
            # Try to get tactic from kill chain phases
            kill_chain_phases = obj.get("kill_chain_phases", [])
            if kill_chain_phases:
                # Get the phase name (tactic)
                return kill_chain_phases[0].get("phase_name", "Unknown")
        except Exception:
            pass
        return "Unknown"

    def populate_chromadb(
        self, 
        techniques: Optional[list[dict]] = None,
        clear_existing: bool = True,
    ) -> int:
        """
        Populate ChromaDB with MITRE techniques.
        
        Args:
            techniques: List of techniques (if None, will extract from loaded data)
            clear_existing: Whether to clear existing documents first
            
        Returns:
            Number of documents added
        """
        if techniques is None:
            techniques = self.extract_techniques()
        
        if not techniques:
            logger.warning("No techniques to add to ChromaDB")
            return 0
        
        # Clear existing if requested
        if clear_existing:
            logger.info("Clearing existing documents from ChromaDB")
            self.chroma_manager.clear_collection()
        
        # Prepare documents for ChromaDB
        documents = []
        for tech in techniques:
            # Create searchable text combining all fields
            searchable_text = (
                f"{tech['technique_id']} {tech['technique_name']}\n"
                f"Тактика: {tech['tactic']}\n"
                f"Описание: {tech['description']}\n"
                f"Платформы: {', '.join(tech['platforms']) if tech['platforms'] else 'N/A'}\n"
                f"Источники данных: {', '.join(tech['data_sources']) if tech['data_sources'] else 'N/A'}"
            )
            
            metadata = {
                "technique_id": tech["technique_id"],
                "technique_name": tech["technique_name"],
                "tactic": tech["tactic"],
                "platforms": json.dumps(tech["platforms"]),
            }
            
            documents.append((searchable_text, metadata))
        
        # Add to ChromaDB
        logger.info(f"Adding {len(documents)} techniques to ChromaDB")
        self.chroma_manager.add_documents(documents)
        
        return len(documents)


def initialize_mitre_knowledge_base(
    chroma_path: Optional[str] = None,
    embedding_model: str = "sentence-transformers/rubert-base-cased",
    domain: str = "enterprise-attack",
) -> ChromaManager:
    """
    Initialize ChromaDB and populate with MITRE ATT&CK data.
    
    Args:
        chroma_path: Path to ChromaDB persistence
        embedding_model: Embedding model to use
        domain: MITRE domain
        
    Returns:
        Initialized ChromaManager
    """
    logger.info("Initializing MITRE ATT&CK knowledge base...")
    
    # Initialize ChromaDB
    chroma_mgr = ChromaManager(
        chroma_path=chroma_path,
        embedding_model=embedding_model,
    )
    
    if not chroma_mgr.initialize():
        raise RuntimeError("Failed to initialize ChromaDB")
    
    # Load MITRE data
    loader = MitreLoader(chroma_mgr)
    
    if not loader.load_mitre_data(domain):
        raise RuntimeError("Failed to load MITRE ATT&CK data")
    
    # Populate ChromaDB
    count = loader.populate_chromadb()
    
    logger.info(f"Knowledge base initialized with {count} techniques")
    
    return chroma_mgr


if __name__ == "__main__":
    # Script to initialize knowledge base from command line
    logging.basicConfig(level=logging.INFO)
    
    try:
        chroma_mgr = initialize_mitre_knowledge_base()
        print(f"✓ MITRE ATT&CK knowledge base initialized successfully!")
        print(f"  ChromaDB path: {chroma_mgr.chroma_path}")
    except Exception as e:
        print(f"✗ Error: {e}")
        exit(1)
