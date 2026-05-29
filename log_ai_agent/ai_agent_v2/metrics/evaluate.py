#!/usr/bin/env python3
"""Evaluate detection quality by comparing pipeline results against ground truth.

Usage:
    # Default paths (inside Docker container):
    python -m ai_agent_v2.metrics.evaluate

    # Custom paths:
    python -m ai_agent_v2.metrics.evaluate \\
        --ground-truth /app/shared/external/attack_timeline.log \\
        --detections /app/log_ai_agent/ai_agent_v2/metrics/pipeline_metrics.log
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

DEFAULT_GROUND_TRUTH = Path("/app/shared/external/attack_timeline.log")
DEFAULT_DETECTIONS = Path(__file__).parent / "pipeline_metrics.log"


def parse_ground_truth(filepath: Path) -> set[str]:
    """Parse attack_timeline.log (format: start|end|technique) into a set of technique IDs."""
    techniques: set[str] = set()
    if not filepath.exists():
        logger.warning(f"Ground truth file not found: {filepath}")
        return techniques

    with filepath.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 3:
                tid = parts[2].strip()
                if tid:
                    techniques.add(tid)
    return techniques


def parse_pipeline_metrics(filepath: Path) -> set[str]:
    """Parse pipeline_metrics.log, extract RAG technique IDs from every incident block."""
    techniques: set[str] = set()
    if not filepath.exists():
        logger.warning(f"Pipeline metrics file not found: {filepath}")
        return techniques

    with filepath.open("r", encoding="utf-8") as f:
        content = f.read()

    # Each incident block: "RAG: T1110, T1496"
    for match in re.finditer(r"^RAG:\s*(.+)$", content, re.MULTILINE):
        raw = match.group(1).strip()
        if raw == "Нет":
            continue
        for tid in raw.split(","):
            tid = tid.strip()
            if tid:
                techniques.add(tid)

    return techniques


def compute_metrics(
    ground_truth: set[str],
    detected: set[str],
) -> dict[str, Any]:
    """Compute TP, FP, FN, precision, recall, F1."""
    tp = ground_truth & detected
    fp = detected - ground_truth
    fn = ground_truth - detected

    precision = len(tp) / (len(tp) + len(fp)) if (len(tp) + len(fp)) > 0 else 0.0
    recall = len(tp) / (len(tp) + len(fn)) if (len(tp) + len(fn)) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "true_positives": sorted(tp),
        "false_positives": sorted(fp),
        "false_negatives": sorted(fn),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
    }


def print_report(metrics: dict[str, Any]) -> None:
    print()
    print("=" * 50)
    print("  DETECTION QUALITY REPORT")
    print("=" * 50)
    print(f"  True Positives  ({len(metrics['true_positives'])}):  {', '.join(metrics['true_positives']) or '—'}")
    print(f"  False Positives ({len(metrics['false_positives'])}): {', '.join(metrics['false_positives']) or '—'}")
    print(f"  False Negatives ({len(metrics['false_negatives'])}): {', '.join(metrics['false_negatives']) or '—'}")
    print()
    print(f"  Precision: {metrics['precision']:.2%}")
    print(f"  Recall:    {metrics['recall']:.2%}")
    print(f"  F1-score:  {metrics['f1_score']:.2%}")
    print("=" * 50)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate detection quality against ground truth."
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=DEFAULT_GROUND_TRUTH,
        help=f"Path to attack_timeline.log (default: {DEFAULT_GROUND_TRUTH})",
    )
    parser.add_argument(
        "--detections",
        type=Path,
        default=DEFAULT_DETECTIONS,
        help=f"Path to pipeline_metrics.log (default: {DEFAULT_DETECTIONS})",
    )
    args = parser.parse_args()

    truth = parse_ground_truth(args.ground_truth)
    detected = parse_pipeline_metrics(args.detections)

    if not truth:
        logger.warning("No ground truth data found. Is the simulator running?")
    if not detected:
        logger.warning("No detection data found. Has the pipeline analyzed any logs?")

    logger.info(f"Ground truth techniques: {len(truth)}")
    logger.info(f"Pipeline-detected techniques: {len(detected)}")

    if truth and detected:
        metrics = compute_metrics(truth, detected)
        print_report(metrics)
    else:
        logger.info("Skipping metrics computation — missing data.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
