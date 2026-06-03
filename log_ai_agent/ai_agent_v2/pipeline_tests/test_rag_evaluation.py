#!/usr/bin/env python3
"""RAG Evaluation module with ground truth comparison.

This module provides metrics for evaluating RAG retrieval quality:
- Precision@k: fraction of retrieved results that are relevant
- Recall@k: fraction of relevant items that are retrieved
- MRR: Mean Reciprocal Rank of first relevant result
- Accuracy@1: whether top result is relevant
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseLanguageModel

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from log_ai_agent.ai_agent_v2.knowledge_base.manager import ChromaDBManager
from log_ai_agent.ai_agent_v2.chains.rag_chain import search_mitre_techniques

logger = logging.getLogger(__name__)

# Path to ground truth dataset
GROUND_TRUTH_PATH = Path(__file__).parent / "rag_ground_truth.json"


class RAGEvaluator:
    """Evaluator for RAG retrieval quality using ground truth."""

    def __init__(
        self,
        chroma_mgr: ChromaDBManager,
        llm: BaseLanguageModel | None = None,
        ground_truth_path: Path | None = None,
    ):
        """Initialize evaluator.

        Args:
            chroma_mgr: ChromaDB manager for vector search
            llm: Language model (optional, for query enhancement)
            ground_truth_path: Path to ground truth JSON file
        """
        self.chroma_mgr = chroma_mgr
        self.llm = llm
        self.ground_truth_path = ground_truth_path or GROUND_TRUTH_PATH
        self._ground_truth: list[dict] | None = None

    def load_ground_truth(self) -> list[dict]:
        """Load ground truth dataset.

        Returns:
            List of test cases with expected technique IDs
        """
        if self._ground_truth is not None:
            return self._ground_truth

        if not self.ground_truth_path.exists():
            raise FileNotFoundError(
                f"Ground truth file not found: {self.ground_truth_path}"
            )

        with open(self.ground_truth_path, encoding="utf-8") as f:
            self._ground_truth = json.load(f)

        logger.info(f"Loaded {len(self._ground_truth)} test cases from ground truth")
        return self._ground_truth

    def retrieve_for_description(
        self,
        description: str,
        k: int = 5,
        score_threshold: float = 0.7,
    ) -> list[dict]:
        """Retrieve MITRE techniques for a description.

        Args:
            description: Text description of the suspicious activity
            k: Number of results to retrieve
            score_threshold: Minimum similarity threshold

        Returns:
            List of retrieved technique dictionaries
        """
        results = search_mitre_techniques(
            chroma_mgr=self.chroma_mgr,
            query=description,
            k=k,
            score_threshold=score_threshold,
        )
        return results

    def normalize_technique_id(self, tech_id: str) -> str:
        """Normalize technique ID by removing sub-technique suffix.

        Args:
            tech_id: Technique ID (e.g., "T1021.001")

        Returns:
            Normalized ID (e.g., "T1021")
        """
        return tech_id.split(".")[0] if "." in tech_id else tech_id

    def extract_technique_ids(self, results: list[dict]) -> list[str]:
        """Extract technique IDs from retrieval results.

        Args:
            results: List of retrieval results from ChromaDB

        Returns:
            List of technique IDs (e.g., ["T1110", "T1190"])
        """
        ids = []
        for r in results:
            metadata = r.get("metadata", {})
            tech_id = metadata.get("technique_id", "")
            if tech_id and tech_id not in ids:
                ids.append(tech_id)
        return ids

    def match_technique(
        self, retrieved_id: str, expected_ids: list[str]
    ) -> bool:
        """Check if retrieved technique matches any expected (including sub-techniques).

        Args:
            retrieved_id: Retrieved technique ID (may include sub-technique like T1021.001)
            expected_ids: List of expected technique IDs

        Returns:
            True if there's a match
        """
        # Normalize both for comparison
        retrieved_base = self.normalize_technique_id(retrieved_id)
        expected_bases = {self.normalize_technique_id(eid) for eid in expected_ids}

        # Check direct match or sub-technique match
        if retrieved_id in expected_ids:
            return True
        if retrieved_base in expected_ids:
            return True
        if retrieved_id in expected_bases:
            return True
        return False

    def precision_at_k(
        self,
        retrieved_ids: list[str],
        expected_ids: list[str],
    ) -> float:
        """Calculate Precision@k.

        Precision@k = |relevant ∩ retrieved| / |retrieved|
        Supports sub-technique matching (T1021 matches T1021.001).

        Args:
            retrieved_ids: List of retrieved technique IDs
            expected_ids: List of expected (relevant) technique IDs

        Returns:
            Precision score between 0 and 1
        """
        if not retrieved_ids:
            return 0.0

        relevant_count = sum(
            1 for rid in retrieved_ids if self.match_technique(rid, expected_ids)
        )
        return relevant_count / len(retrieved_ids)

    def recall_at_k(
        self,
        retrieved_ids: list[str],
        expected_ids: list[str],
    ) -> float:
        """Calculate Recall@k.

        Recall@k = |relevant ∩ retrieved| / |relevant|
        Supports sub-technique matching.

        Args:
            retrieved_ids: List of retrieved technique IDs
            expected_ids: List of expected (relevant) technique IDs

        Returns:
            Recall score between 0 and 1
        """
        if not expected_ids:
            return 1.0  # No relevant items = perfect recall

        relevant_count = sum(
            1 for eid in expected_ids if self.match_technique(eid, retrieved_ids)
        )
        return relevant_count / len(expected_ids)

    def mrr(
        self,
        retrieved_ids: list[str],
        expected_ids: list[str],
    ) -> float:
        """Calculate Mean Reciprocal Rank.

        MRR = 1/rank of first relevant result.
        Supports sub-technique matching.

        Args:
            retrieved_ids: Ordered list of retrieved technique IDs
            expected_ids: List of expected technique IDs

        Returns:
            MRR score between 0 and 1
        """
        for i, tech_id in enumerate(retrieved_ids, start=1):
            if self.match_technique(tech_id, expected_ids):
                return 1.0 / i
        return 0.0

    def accuracy_at_1(
        self,
        retrieved_ids: list[str],
        expected_ids: list[str],
    ) -> bool:
        """Check if top-1 result is relevant.

        Args:
            retrieved_ids: List of retrieved technique IDs
            expected_ids: List of expected technique IDs

        Returns:
            True if top result is relevant
        """
        if not retrieved_ids or not expected_ids:
            return False
        return self.match_technique(retrieved_ids[0], expected_ids)

    def evaluate_single(
        self,
        description: str,
        expected_ids: list[str],
        k: int = 5,
        score_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Evaluate retrieval for a single test case.

        Args:
            description: Description of suspicious activity
            expected_ids: Expected technique IDs
            k: Number of results to retrieve
            score_threshold: Minimum similarity threshold

        Returns:
            Dictionary with evaluation results
        """
        results = self.retrieve_for_description(
            description=description,
            k=k,
            score_threshold=score_threshold,
        )
        retrieved_ids = self.extract_technique_ids(results)

        return {
            "retrieved_ids": retrieved_ids,
            "expected_ids": expected_ids,
            "precision_at_k": self.precision_at_k(retrieved_ids, expected_ids),
            "recall_at_k": self.recall_at_k(retrieved_ids, expected_ids),
            "mrr": self.mrr(retrieved_ids, expected_ids),
            "accuracy_at_1": self.accuracy_at_1(retrieved_ids, expected_ids),
            "num_retrieved": len(retrieved_ids),
            "num_expected": len(expected_ids),
        }

    def evaluate_all(
        self,
        k: int = 5,
        score_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Evaluate all test cases in ground truth.

        Args:
            k: Number of results to retrieve per query
            score_threshold: Minimum similarity threshold

        Returns:
            Dictionary with per-case and aggregate results
        """
        test_cases = self.load_ground_truth()

        case_results = []
        total_precision = 0.0
        total_recall = 0.0
        total_mrr = 0.0
        total_accuracy = 0
        valid_cases = 0

        for case in test_cases:
            case_id = case.get("id", "unknown")
            description = case.get("description", "")
            expected_ids = case.get("expected_technique_ids", [])

            if not description or not expected_ids:
                logger.warning(f"Skipping incomplete test case: {case_id}")
                continue

            eval_result = self.evaluate_single(
                description=description,
                expected_ids=expected_ids,
                k=k,
                score_threshold=score_threshold,
            )

            case_results.append(
                {
                    "id": case_id,
                    "category": case.get("category", "unknown"),
                    "description": description[:100],
                    **eval_result,
                }
            )

            total_precision += eval_result["precision_at_k"]
            total_recall += eval_result["recall_at_k"]
            total_mrr += eval_result["mrr"]
            if eval_result["accuracy_at_1"]:
                total_accuracy += 1
            valid_cases += 1

        # Calculate aggregate metrics
        if valid_cases > 0:
            aggregate = {
                "precision_at_k": total_precision / valid_cases,
                "recall_at_k": total_recall / valid_cases,
                "mrr": total_mrr / valid_cases,
                "accuracy_at_1": total_accuracy / valid_cases,
                "num_test_cases": valid_cases,
                "k": k,
                "score_threshold": score_threshold,
            }
        else:
            aggregate = {
                "precision_at_k": 0.0,
                "recall_at_k": 0.0,
                "mrr": 0.0,
                "accuracy_at_1": 0.0,
                "num_test_cases": 0,
                "k": k,
                "score_threshold": score_threshold,
            }

        return {
            "aggregate": aggregate,
            "cases": case_results,
        }
