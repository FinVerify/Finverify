"""
FinVerifyBench — Schema Validators
Every sample must pass validation before entering the dataset.
"""

import re
import json
import math
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass

from implementation.taxonomy import (
    ErrorCategory, ReasoningType, Difficulty, Domain, Unit,
    RATIO_KEYWORDS, NEGATION_KEYWORDS
)


REQUIRED_FIELDS = {
    "id", "domain", "question", "context",
    "ground_truth", "unit", "error_category",
    "difficulty", "reasoning_type",
}

OPTIONAL_FIELDS = {
    "source", "split", "dvl_rules", "notes",
    "distractor_numbers", "expected_steps",
}

ID_PATTERN = re.compile(r"^fvb_\d{6}$")


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]

    def __bool__(self):
        return self.valid


def validate_sample(sample: Dict[str, Any]) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    # ── Required fields present ──────────────────────────────────────────────
    missing = REQUIRED_FIELDS - set(sample.keys())
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")

    if errors:
        return ValidationResult(False, errors, warnings)

    # ── ID format ────────────────────────────────────────────────────────────
    if not ID_PATTERN.match(sample.get("id", "")):
        errors.append(f"id must match fvb_XXXXXX pattern, got: {sample['id']!r}")

    # ── Domain ───────────────────────────────────────────────────────────────
    valid_domains = {d.value for d in Domain}
    if sample["domain"] not in valid_domains:
        errors.append(f"domain {sample['domain']!r} not in {valid_domains}")

    # ── Question non-empty ───────────────────────────────────────────────────
    if not isinstance(sample["question"], str) or len(sample["question"].strip()) < 10:
        errors.append("question must be a non-empty string (≥ 10 chars)")

    # ── Context non-empty ────────────────────────────────────────────────────
    if not isinstance(sample["context"], str) or len(sample["context"].strip()) < 20:
        errors.append("context must be a non-empty string (≥ 20 chars)")

    # ── Ground truth numeric ─────────────────────────────────────────────────
    gt = sample["ground_truth"]
    if not isinstance(gt, (int, float)) or math.isnan(gt) or math.isinf(gt):
        errors.append(f"ground_truth must be a finite number, got: {gt!r}")

    # ── Unit ─────────────────────────────────────────────────────────────────
    valid_units = {u.value for u in Unit}
    if sample["unit"] not in valid_units:
        warnings.append(f"unit {sample['unit']!r} not in canonical list; using 'other'")

    # ── Error categories ─────────────────────────────────────────────────────
    valid_cats = {c.value for c in ErrorCategory}
    ec = sample["error_category"]
    if not isinstance(ec, list) or len(ec) == 0:
        errors.append("error_category must be a non-empty list")
    else:
        bad = set(ec) - valid_cats
        if bad:
            errors.append(f"Unknown error_category values: {bad}")

    # ── Difficulty ───────────────────────────────────────────────────────────
    valid_diff = {d.value for d in Difficulty}
    if sample["difficulty"] not in valid_diff:
        errors.append(f"difficulty {sample['difficulty']!r} not in {valid_diff}")

    # ── Reasoning types ──────────────────────────────────────────────────────
    valid_rt = {r.value for r in ReasoningType}
    rt = sample["reasoning_type"]
    if not isinstance(rt, list) or len(rt) == 0:
        errors.append("reasoning_type must be a non-empty list")
    else:
        bad = set(rt) - valid_rt
        if bad:
            errors.append(f"Unknown reasoning_type values: {bad}")

    # ── Semantic consistency warnings ────────────────────────────────────────
    if isinstance(gt, (int, float)) and not math.isnan(gt):
        q_lower = sample["question"].lower()

        # Scale error: ratio Q with |gt| > 100 might be mislabelled
        is_ratio = any(kw in q_lower for kw in RATIO_KEYWORDS)
        ec_list = sample.get("error_category", [])
        if is_ratio and abs(gt) > 100 and "scale_error" not in ec_list:
            warnings.append(
                f"Ratio question with |ground_truth|={abs(gt):.2f} > 100; "
                "consider adding scale_error to error_category"
            )

        # Sign warning
        has_negation = any(kw in q_lower for kw in NEGATION_KEYWORDS)
        if has_negation and gt > 0 and "sign_error" not in ec_list:
            warnings.append(
                "Question contains negation keyword but ground_truth is positive; "
                "verify sign is correct"
            )

    return ValidationResult(len(errors) == 0, errors, warnings)


def validate_dataset(samples: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
    """
    Returns (valid_samples, invalid_samples).
    invalid_samples each carry a '_validation_errors' key.
    """
    valid, invalid = [], []
    seen_ids: set = set()

    for i, s in enumerate(samples):
        result = validate_sample(s)

        sid = s.get("id", f"<index {i}>")
        if sid in seen_ids:
            result.errors.append(f"Duplicate id: {sid}")
            result.valid = False
        seen_ids.add(sid)

        if result.valid:
            if result.warnings:
                s["_warnings"] = result.warnings
            valid.append(s)
        else:
            s["_validation_errors"] = result.errors
            s["_warnings"] = result.warnings
            invalid.append(s)

    return valid, invalid


def validate_predictions(
    predictions: List[Dict[str, Any]],
    dataset: List[Dict[str, Any]],
) -> Tuple[List[Dict], List[str]]:
    """
    Validate prediction format and align with dataset samples.
    Returns (aligned_pairs, errors).
    Each aligned pair: {"sample": ..., "prediction": float_value}
    """
    errors: List[str] = []
    dataset_map = {s["id"]: s for s in dataset}
    aligned = []

    for pred in predictions:
        if "id" not in pred:
            errors.append(f"Prediction missing 'id': {pred}")
            continue
        if "prediction" not in pred:
            errors.append(f"Prediction {pred['id']} missing 'prediction' field")
            continue
        if pred["id"] not in dataset_map:
            errors.append(f"Prediction id {pred['id']} not found in dataset")
            continue

        val = pred["prediction"]
        if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            errors.append(
                f"Prediction {pred['id']}: prediction must be finite number, got {val!r}"
            )
            continue

        aligned.append({
            "sample": dataset_map[pred["id"]],
            "prediction": float(val),
        })

    return aligned, errors