#!/usr/bin/env python3
"""RAG Evaluation Test - Tests RAG accuracy with ground truth cases.

Uses precision@1 metric: only checks if top-1 result matches expected technique.
"""

import pytest
import asyncio
import json
from pathlib import Path

from log_ai_agent.ai_agent_v2.chains.rag_chain import rag_search_single_event
from log_ai_agent.ai_agent_v2.chains.llm import create_llm
from log_ai_agent.ai_agent_v2.knowledge_base.mitre_loader import initialize_mitre_knowledge_base

DEFAULT_THRESHOLD = 0.40


def check_technique_match(got_id: str, expected_ids: list[str]) -> bool:
    """Check if any expected technique ID is present in the combined ID string.

    Example:
        got_id = "T1589 & T1590 & T1591 & T1592"
        expected_ids = ["T1590"] -> True
        expected_ids = ["T1110"] -> False
    """
    if not got_id or got_id == "NONE":
        return False
    return any(exp_id in got_id for exp_id in expected_ids)


def load_ground_truth() -> list[dict]:
    """Load ground truth test cases."""
    path = Path(__file__).parent / "rag_ground_truth.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def chroma_manager():
    """Initialize ChromaDB manager for tests."""
    chroma_path = Path(__file__).parent.parent / "chroma_db"
    manager = initialize_mitre_knowledge_base(str(chroma_path))
    if manager and manager.is_initialized:
        return manager
    pytest.skip("ChromaDB not initialized")


@pytest.fixture
def llm():
    """Create LLM for tests."""
    return create_llm()


@pytest.mark.asyncio
async def test_rag_accuracy_single(llm, chroma_manager):
    """Test RAG accuracy for single case (brute_force)."""
    cases = load_ground_truth()
    test_case = next(c for c in cases if c["id"] == "brute_force_1")

    result = await rag_search_single_event(
        llm=llm,
        chroma_mgr=chroma_manager,
        description=test_case["description"],
        k=3,
        score_threshold=DEFAULT_THRESHOLD,
    )

    print(f"\nTest: {test_case['id']}")
    print(f"Query: {test_case['description'][:80]}...")
    print(f"Expected: {test_case['expected_technique_ids']}")
    print(f"Got: {result.get('technique_id', 'NONE')}")
    print(f"Confidence: {result.get('confidence', 0):.3f}")

    assert check_technique_match(result.get("technique_id", ""), test_case["expected_technique_ids"]), \
        f"Expected {test_case['expected_technique_ids']}, got {result.get('technique_id')}"


@pytest.mark.asyncio
async def test_rag_precision_at_1(llm, chroma_manager):
    """Test RAG precision@1 for all ground truth cases.

    Precision@1: only top-1 result must be in expected_technique_ids.
    """
    cases = load_ground_truth()
    results = []
    passed = 0

    print("\n" + "="*70)
    print(f"RAG PRECISION@1 TEST (threshold={DEFAULT_THRESHOLD})")
    print("="*70)

    for case in cases:
        result = await rag_search_single_event(
            llm=llm,
            chroma_mgr=chroma_manager,
            description=case["description"],
            k=3,
            score_threshold=DEFAULT_THRESHOLD,
        )

        matched = check_technique_match(result.get("technique_id", ""), case["expected_technique_ids"])
        if matched:
            passed += 1

        results.append({
            "id": case["id"],
            "expected": case["expected_technique_ids"],
            "got": result.get("technique_id", "NONE"),
            "matched": matched,
            "confidence": result.get("confidence", 0),
            "category": case.get("category", "unknown"),
        })

    print("\nResults:")
    print("-"*70)
    for r in results:
        status = "PASS" if r["matched"] else "FAIL"
        conf_color = "OK" if r["confidence"] >= DEFAULT_THRESHOLD else "LOW"
        print(f"[{status}] {r['id']:30} | expected={r['expected']} | got={r['got']:6} | conf={r['confidence']:.3f} [{conf_color}]")

    print("-"*70)

    precision = passed / len(cases) * 100
    print(f"\nPrecision@1: {passed}/{len(cases)} ({precision:.0f}%)")
    print("="*70)

    assert precision >= 50, f"Precision {precision:.0f}% is too low (minimum 50%)"


@pytest.mark.asyncio
async def test_rag_threshold_analysis(llm, chroma_manager):
    """Analyze precision at different thresholds."""
    cases = load_ground_truth()
    thresholds = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]

    print("\n" + "="*70)
    print("RAG THRESHOLD ANALYSIS")
    print("="*70)
    print(f"{'Threshold':>10} | {'Passed':>8} | {'Failed':>8} | {'Precision':>10}")
    print("-"*70)

    for threshold in thresholds:
        passed = 0
        failed = 0
        no_match = 0

        for case in cases:
            result = await rag_search_single_event(
                llm=llm,
                chroma_mgr=chroma_manager,
                description=case["description"],
                k=3,
                score_threshold=threshold,
            )

            if not result.get("has_match"):
                no_match += 1
            elif check_technique_match(result.get("technique_id", ""), case["expected_technique_ids"]):
                passed += 1
            else:
                failed += 1

        total = passed + failed
        precision = (passed / total * 100) if total > 0 else 0
        print(f"{threshold:>10.2f} | {passed:>8} | {failed:>8} | {precision:>9.0f}%")

    print("-"*70)
    print(f"No match count (at any threshold): {no_match}")
    print("="*70)


@pytest.mark.asyncio
async def test_rag_categories_breakdown(llm, chroma_manager):
    """Test RAG accuracy by MITRE tactic category."""
    cases = load_ground_truth()
    categories = {}

    for case in cases:
        cat = case.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0}

        result = await rag_search_single_event(
            llm=llm,
            chroma_mgr=chroma_manager,
            description=case["description"],
            k=3,
            score_threshold=DEFAULT_THRESHOLD,
        )

        if check_technique_match(result.get("technique_id", ""), case["expected_technique_ids"]):
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1

    print("\n" + "="*70)
    print("RAG ACCURACY BY CATEGORY")
    print("="*70)

    for cat, stats in sorted(categories.items()):
        total = stats["passed"] + stats["failed"]
        acc = stats["passed"] / total * 100 if total > 0 else 0
        print(f"{cat:30} | {stats['passed']}/{total} ({acc:.0f}%)")

    print("="*70)


@pytest.mark.asyncio
async def test_rag_low_confidence_cases(llm, chroma_manager):
    """Check cases with low confidence scores."""
    cases = load_ground_truth()

    print("\n" + "="*70)
    print("LOW CONFIDENCE ANALYSIS")
    print("="*70)

    low_confidence = []
    for case in cases:
        result = await rag_search_single_event(
            llm=llm,
            chroma_mgr=chroma_manager,
            description=case["description"],
            k=3,
            score_threshold=DEFAULT_THRESHOLD,
        )

        if result.get("confidence", 0) < 0.30:
            low_confidence.append({
                "id": case["id"],
                "expected": case["expected_technique_ids"],
                "got": result.get("technique_id"),
                "confidence": result.get("confidence", 0),
            })

    if low_confidence:
        print(f"Found {len(low_confidence)} cases with confidence < 0.30:")
        for lc in low_confidence:
            print(f"  - {lc['id']}: expected={lc['expected']}, got={lc['got']}, conf={lc['confidence']:.3f}")
    else:
        print("All cases have confidence >= 0.30")

    print("="*70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])