#!/usr/bin/env python3
"""
FinVerifyBench — Unit Test Suite
Run: python -m pytest tests/ -v
  or: python tests/test_benchmark.py
"""

import json
import math
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.evaluator import evaluate
from benchmark.metrics import (
    is_correct, relative_error, compute_overall_accuracy,
    compute_bias_statistics, compute_category_accuracy, TOLERANCE
)
from benchmark.validators import validate_sample, validate_dataset
from benchmark.taxonomy import (
    ErrorCategory, ReasoningType, Difficulty, Domain, Unit,
    classify_dvl_rules, DVLRuleTag
)


def test_is_correct():
    assert is_correct(100.0, 100.0)
    assert is_correct(104.9, 100.0)   # within 5%
    assert not is_correct(106.0, 100.0)  # outside 5%
    assert is_correct(-100.0, -100.0)
    assert is_correct(0.0, 0.0)
    print("  ✓ is_correct")


def test_relative_error():
    assert relative_error(110.0, 100.0) == pytest_approx(0.1) if False else True
    assert abs(relative_error(110.0, 100.0) - 0.1) < 1e-9
    assert relative_error(90.0, 100.0) == -0.1
    assert relative_error(0.0, 100.0) == -1.0
    assert relative_error(50.0, 0.0) is None
    print("  ✓ relative_error")


def test_validate_sample_valid():
    sample = {
        "id": "fvb_000001",
        "domain": "finance",
        "question": "What is the gross profit margin percentage?",
        "context": "Income Statement (in millions)\nRevenue: $45,230\nCost: $33,245",
        "ground_truth": 26.5,
        "unit": "percent",
        "error_category": ["scale_error"],
        "difficulty": "easy",
        "reasoning_type": ["margin_calculation"],
    }
    result = validate_sample(sample)
    assert result.valid, f"Expected valid, got errors: {result.errors}"
    print("  ✓ validate_sample (valid)")


def test_validate_sample_missing_field():
    sample = {
        "id": "fvb_000001",
        "domain": "finance",
        "question": "What is X?",
        # missing context, ground_truth, unit, etc.
    }
    result = validate_sample(sample)
    assert not result.valid
    assert any("Missing" in e for e in result.errors)
    print("  ✓ validate_sample (missing fields)")


def test_validate_sample_bad_id():
    sample = {
        "id": "bad-id-format",
        "domain": "finance",
        "question": "What is the gross margin percentage for fiscal year?",
        "context": "Income Statement\nRevenue: $1000\nCOGS: $600",
        "ground_truth": 40.0,
        "unit": "percent",
        "error_category": ["scale_error"],
        "difficulty": "easy",
        "reasoning_type": ["margin_calculation"],
    }
    result = validate_sample(sample)
    assert not result.valid
    assert any("id must match" in e for e in result.errors)
    print("  ✓ validate_sample (bad id)")


def test_validate_sample_unknown_category():
    sample = {
        "id": "fvb_000002",
        "domain": "finance",
        "question": "What is the gross margin percentage for the period?",
        "context": "Income Statement\nRevenue: $1000\nCOGS: $600",
        "ground_truth": 40.0,
        "unit": "percent",
        "error_category": ["invented_category_xyz"],
        "difficulty": "easy",
        "reasoning_type": ["margin_calculation"],
    }
    result = validate_sample(sample)
    assert not result.valid
    assert any("error_category" in e for e in result.errors)
    print("  ✓ validate_sample (unknown category)")


def test_evaluate_perfect():
    """All predictions match ground truth → 100% accuracy."""
    dataset = [
        {"id": "fvb_000001", "domain": "finance", "question": "Q",
         "context": "C", "ground_truth": 42.5, "unit": "percent",
         "error_category": ["scale_error"], "difficulty": "easy",
         "reasoning_type": ["margin_calculation"]},
        {"id": "fvb_000002", "domain": "finance", "question": "Q",
         "context": "C", "ground_truth": -100.0, "unit": "million_usd",
         "error_category": ["sign_error"], "difficulty": "easy",
         "reasoning_type": ["yoy_change"]},
    ]
    predictions = [
        {"id": "fvb_000001", "prediction": 42.5},
        {"id": "fvb_000002", "prediction": -100.0},
    ]
    report = evaluate(dataset, predictions)
    assert report["overall"]["accuracy"] == 1.0
    assert report["overall"]["mean_relative_error"] == 0.0
    print("  ✓ evaluate (perfect predictions)")


def test_evaluate_zero_accuracy():
    dataset = [
        {"id": "fvb_000001", "domain": "finance", "question": "Q",
         "context": "C", "ground_truth": 42.5, "unit": "percent",
         "error_category": ["scale_error"], "difficulty": "easy",
         "reasoning_type": ["margin_calculation"]},
    ]
    predictions = [{"id": "fvb_000001", "prediction": 999.0}]
    report = evaluate(dataset, predictions)
    assert report["overall"]["accuracy"] == 0.0
    print("  ✓ evaluate (zero accuracy)")


def test_evaluate_bias_detection():
    """Underestimation should be detected."""
    dataset = [
        {"id": f"fvb_{i:06d}", "domain": "finance", "question": "Q",
         "context": "C", "ground_truth": 100.0, "unit": "million_usd",
         "error_category": ["arithmetic_error"], "difficulty": "medium",
         "reasoning_type": ["yoy_change"]}
        for i in range(1, 11)
    ]
    # All predictions underestimate
    predictions = [{"id": f"fvb_{i:06d}", "prediction": 50.0} for i in range(1, 11)]
    report = evaluate(dataset, predictions)
    bias = report["bias_statistics"]
    assert bias["underestimation_rate"] == 1.0
    assert bias["overestimation_rate"] == 0.0
    print("  ✓ evaluate (bias detection — underestimation)")


def test_dvl_rules_scale():
    tag = classify_dvl_rules("What is the gross margin percentage?", 0.265, "percent")
    assert tag.scale_correction  # |0.265| < 1 and ratio question
    print("  ✓ DVL rule: scale (decimal margin)")


def test_dvl_rules_sign():
    tag = classify_dvl_rules("What was the loss from operations?", -234.0, "million_usd")
    assert tag.sign_correction
    print("  ✓ DVL rule: sign (loss keyword + negative gt)")


def test_dvl_rules_magnitude():
    tag = classify_dvl_rules("What is the total revenue?", 45.2, "billion_usd")
    assert tag.magnitude_correction
    print("  ✓ DVL rule: magnitude (billion unit)")


def test_enums_complete():
    """All taxonomy enums are populated."""
    assert len(list(ErrorCategory)) > 5
    assert len(list(ReasoningType)) >= 10
    assert len(list(Difficulty)) == 3
    assert len(list(Domain)) >= 4
    assert len(list(Unit)) >= 8
    print("  ✓ Taxonomy enums complete")


def test_real_dataset_loads():
    """Load actual processed dataset and run spot checks."""
    paths = ["data/processed/train.json", "data/processed/dev.json", "data/processed/test.json"]
    for path in paths:
        if not os.path.exists(path):
            print(f"  ⚠ {path} not found — run create_dataset.py first")
            continue
        with open(path) as f:
            samples = json.load(f)
        assert len(samples) > 0
        # Every sample must have required fields
        for s in samples[:5]:
            result = validate_sample(s)
            assert result.valid, f"{s['id']}: {result.errors}"
        print(f"  ✓ {path} loads and validates ({len(samples)} samples)")


def test_evaluate_category_breakdown():
    """Per-category accuracy should sum correctly."""
    dataset = [
        {"id": "fvb_000001", "domain": "finance", "question": "Q", "context": "C",
         "ground_truth": 50.0, "unit": "percent",
         "error_category": ["scale_error"], "difficulty": "easy",
         "reasoning_type": ["margin_calculation"]},
        {"id": "fvb_000002", "domain": "finance", "question": "Q", "context": "C",
         "ground_truth": -100.0, "unit": "million_usd",
         "error_category": ["sign_error"], "difficulty": "easy",
         "reasoning_type": ["yoy_change"]},
        {"id": "fvb_000003", "domain": "finance", "question": "Q", "context": "C",
         "ground_truth": 200.0, "unit": "million_usd",
         "error_category": ["scale_error"], "difficulty": "medium",
         "reasoning_type": ["yoy_change"]},
    ]
    predictions = [
        {"id": "fvb_000001", "prediction": 50.0},   # correct (scale_error)
        {"id": "fvb_000002", "prediction": 100.0},  # wrong sign
        {"id": "fvb_000003", "prediction": 999.0},  # wrong (scale_error)
    ]
    report = evaluate(dataset, predictions)
    cat = report["error_category_breakdown"]
    assert cat["scale_error"]["n"] == 2
    assert cat["scale_error"]["correct"] == 1
    assert abs(cat["scale_error"]["accuracy"] - 0.5) < 0.01
    print("  ✓ evaluate (category breakdown)")


if __name__ == "__main__":
    tests = [
        test_is_correct,
        test_relative_error,
        test_validate_sample_valid,
        test_validate_sample_missing_field,
        test_validate_sample_bad_id,
        test_validate_sample_unknown_category,
        test_evaluate_perfect,
        test_evaluate_zero_accuracy,
        test_evaluate_bias_detection,
        test_dvl_rules_scale,
        test_dvl_rules_sign,
        test_dvl_rules_magnitude,
        test_enums_complete,
        test_real_dataset_loads,
        test_evaluate_category_breakdown,
    ]

    passed = 0
    failed_tests = []
    print(f"\n{'='*50}")
    print("  FinVerifyBench Unit Tests")
    print(f"{'='*50}")

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            failed_tests.append((test_fn.__name__, str(e)))
            print(f"  ✗ {test_fn.__name__}: {e}")
        except Exception as e:
            failed_tests.append((test_fn.__name__, str(e)))
            print(f"  ✗ {test_fn.__name__} EXCEPTION: {e}")

    print(f"\n  {passed}/{len(tests)} tests passed")
    if failed_tests:
        print(f"  Failed: {[t[0] for t in failed_tests]}")
    print(f"{'='*50}")
    sys.exit(0 if not failed_tests else 1)
