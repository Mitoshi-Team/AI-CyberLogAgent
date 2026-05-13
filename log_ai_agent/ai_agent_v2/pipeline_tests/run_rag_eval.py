#!/usr/bin/env python3
"""CLI script for running RAG evaluation against ground truth.

Usage:
    python run_rag_eval.py [--k K] [--threshold THRESH] [--output PATH]

Example:
    python run_rag_eval.py --k 5 --threshold 0.7
    python run_rag_eval.py --k 3 --output results.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from log_ai_agent.ai_agent_v2.knowledge_base.manager import ChromaDBManager
from log_ai_agent.ai_agent_v2.knowledge_base.mitre_loader import initialize_mitre_knowledge_base
from test_rag_evaluation import RAGEvaluator

# Default paths
DEFAULT_CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"


def print_results_table(results: dict, k: int, threshold: float, verbose: bool = False):
    """Print evaluation results in a formatted table.

    Args:
        results: Evaluation results from RAGEvaluator.evaluate_all()
        k: Value of k used for retrieval
        threshold: Score threshold used
        verbose: Whether to print detailed retrieval results
    """
    aggregate = results["aggregate"]
    cases = results["cases"]

    print("\n" + "=" * 80)
    print("  RAG Evaluation Results")
    print("=" * 80)

    # Per-case results
    print(f"\n{'Test Case':<30} | {'Expected':<20} | {'Top-1':<10} | {'MRR':<6} | {'Status':<8}")
    print("-" * 80)

    for case in cases:
        case_id = case["id"][:28]
        expected = ", ".join(case["expected_ids"])[:18]
        top_1 = case["retrieved_ids"][0] if case["retrieved_ids"] else "None"
        mrr = f"{case['mrr']:.2f}"
        status = "OK" if case["accuracy_at_1"] else "FAIL"

        print(f"{case_id:<30} | {expected:<20} | {top_1:<10} | {mrr:<6} | {status:<8}")

        if verbose and case.get("retrieved_ids"):
            print(f"  Retrieved: {case['retrieved_ids']}")

    # Aggregate metrics
    print("\n" + "-" * 80)
    print(f"Overall Metrics (k={k}, threshold={threshold}):")
    print(f"  Precision@{k}:  {aggregate['precision_at_k']:.3f}")
    print(f"  Recall@{k}:     {aggregate['recall_at_k']:.3f}")
    print(f"  MRR:            {aggregate['mrr']:.3f}")
    print(f"  Accuracy@1:     {aggregate['accuracy_at_1']:.3f}")
    print(f"  Test cases:      {aggregate['num_test_cases']}")
    print("=" * 80)


def save_report(results: dict, output_path: str | Path):
    """Save evaluation results to a JSON file.

    Args:
        results: Evaluation results dictionary
        output_path: Path to save the JSON report
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate RAG retrieval quality for MITRE ATT&CK techniques"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of results to retrieve per query (default: 5)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Minimum similarity threshold for retrieval (default: 0.7)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save JSON report (optional)",
    )
    parser.add_argument(
        "--chroma-path",
        type=str,
        default=None,
        help="Path to ChromaDB directory (default: chroma_db)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed retrieval results for each test case",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("  AI Agent v2 - RAG Evaluation")
    print("=" * 80)

    # Initialize ChromaDB
    chroma_path = Path(args.chroma_path) if args.chroma_path else DEFAULT_CHROMA_PATH
    print(f"\n[INFO] Initializing ChromaDB at: {chroma_path}")

    try:
        chroma_mgr = initialize_mitre_knowledge_base(
            persist_directory=str(chroma_path),
        )
        if not chroma_mgr or not chroma_mgr.is_initialized:
            print("[ERROR] ChromaDB not initialized. Please check the path.")
            sys.exit(1)
        print("[OK] ChromaDB initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize ChromaDB: {e}")
        sys.exit(1)

    # Create evaluator
    evaluator = RAGEvaluator(
        chroma_mgr=chroma_mgr,
        ground_truth_path=Path(__file__).parent / "rag_ground_truth.json",
    )

    # Run evaluation
    print(f"\n[INFO] Running evaluation with k={args.k}, threshold={args.threshold}")
    print("-" * 80)

    start_time = time.time()
    results = evaluator.evaluate_all(k=args.k, score_threshold=args.threshold)
    elapsed = time.time() - start_time

    # Print results
    print_results_table(results, k=args.k, threshold=args.threshold, verbose=args.verbose)
    print(f"\n[INFO] Evaluation completed in {elapsed:.1f}s")

    # Save report if requested
    if args.output:
        save_report(results, args.output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Evaluation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
