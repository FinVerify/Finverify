"""
FinVerifyBench — Metrics
All metrics from the paper: exact match, relative error, bias detection,
underestimation/overestimation rate, per-category breakdown, calibration.
"""

import math
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

from implementation.taxonomy import ErrorCategory, Difficulty, ReasoningType


TOLERANCE = 0.05  # 5% relative — matches original FinQA eval protocol


# ─────────────────────────────────────────────────────────────────────────────
# Core numeric checks
# ─────────────────────────────────────────────────────────────────────────────

def is_correct(prediction: float, ground_truth: float, tol: float = TOLERANCE) -> bool:
    """Execution accuracy with relative tolerance (matches FinQA protocol)."""
    if ground_truth == 0:
        return abs(prediction) <= tol
    return abs(prediction - ground_truth) / abs(ground_truth) <= tol


def relative_error(prediction: float, ground_truth: float) -> Optional[float]:
    """Signed relative error: (pred - gt) / |gt|. None if gt == 0."""
    if ground_truth == 0:
        return None
    return (prediction - ground_truth) / abs(ground_truth)


def absolute_error(prediction: float, ground_truth: float) -> float:
    return abs(prediction - ground_truth)


def log_ratio(prediction: float, ground_truth: float) -> Optional[float]:
    """log10(|pred|/|gt|) — order-of-magnitude distance."""
    if ground_truth == 0 or prediction == 0:
        return None
    return math.log10(abs(prediction) / abs(ground_truth))


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_overall_accuracy(pairs: List[Dict], tol: float = TOLERANCE) -> float:
    if not pairs:
        return 0.0
    correct = sum(1 for p in pairs if is_correct(p["prediction"], p["sample"]["ground_truth"], tol))
    return correct / len(pairs)


def compute_mean_relative_error(pairs: List[Dict]) -> float:
    """Mean absolute relative error across samples where gt != 0."""
    errors = []
    for p in pairs:
        gt = p["sample"]["ground_truth"]
        re = relative_error(p["prediction"], gt)
        if re is not None:
            errors.append(abs(re))
    return statistics.mean(errors) if errors else float("nan")


def compute_median_relative_error(pairs: List[Dict]) -> float:
    errors = []
    for p in pairs:
        gt = p["sample"]["ground_truth"]
        re = relative_error(p["prediction"], gt)
        if re is not None:
            errors.append(abs(re))
    return statistics.median(errors) if errors else float("nan")


# ─────────────────────────────────────────────────────────────────────────────
# Bias detection — mirrors paper's binomial test setup
# ─────────────────────────────────────────────────────────────────────────────

def compute_bias_statistics(pairs: List[Dict]) -> Dict[str, Any]:
    """
    Replicates the paper's systematic underestimation analysis.
    Returns counts and rates for under/over estimation on *wrong* predictions.
    """
    wrong_pairs = [
        p for p in pairs
        if not is_correct(p["prediction"], p["sample"]["ground_truth"])
    ]

    n_under = 0  # prediction < ground_truth (underestimation)
    n_over  = 0  # prediction > ground_truth (overestimation)
    n_zero_gt = 0

    signed_errors = []
    for p in wrong_pairs:
        gt   = p["sample"]["ground_truth"]
        pred = p["prediction"]
        re   = relative_error(pred, gt)
        if re is None:
            n_zero_gt += 1
            continue
        signed_errors.append(re)
        if pred < gt:
            n_under += 1
        else:
            n_over += 1

    total_directional = n_under + n_over
    under_rate = n_under / total_directional if total_directional else 0.0
    over_rate  = n_over  / total_directional if total_directional else 0.0

    return {
        "n_wrong":            len(wrong_pairs),
        "n_underestimation":  n_under,
        "n_overestimation":   n_over,
        "n_zero_ground_truth": n_zero_gt,
        "underestimation_rate": round(under_rate, 4),
        "overestimation_rate":  round(over_rate, 4),
        "mean_signed_relative_error": round(statistics.mean(signed_errors), 4) if signed_errors else None,
        "note": (
            f"Paper benchmark: 60.9% underestimation on FinQA fine-tuned Mistral-7B. "
            f"This model: {under_rate*100:.1f}%"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Per-category breakdown
# ─────────────────────────────────────────────────────────────────────────────

def compute_category_accuracy(pairs: List[Dict], tol: float = TOLERANCE) -> Dict[str, Dict]:
    """Accuracy broken down by error_category of the *sample* (ground-truth label)."""
    buckets: Dict[str, List] = defaultdict(list)
    for p in pairs:
        for cat in p["sample"].get("error_category", ["none"]):
            buckets[cat].append(p)

    result = {}
    for cat, cat_pairs in sorted(buckets.items()):
        n = len(cat_pairs)
        n_correct = sum(1 for p in cat_pairs if is_correct(p["prediction"], p["sample"]["ground_truth"], tol))
        result[cat] = {
            "n":        n,
            "correct":  n_correct,
            "accuracy": round(n_correct / n, 4) if n else 0.0,
        }
    return result


def compute_difficulty_accuracy(pairs: List[Dict], tol: float = TOLERANCE) -> Dict[str, Dict]:
    buckets: Dict[str, List] = defaultdict(list)
    for p in pairs:
        diff = p["sample"].get("difficulty", "unknown")
        buckets[diff].append(p)

    result = {}
    for diff, diff_pairs in sorted(buckets.items()):
        n = len(diff_pairs)
        n_correct = sum(1 for p in diff_pairs if is_correct(p["prediction"], p["sample"]["ground_truth"], tol))
        result[diff] = {
            "n":        n,
            "correct":  n_correct,
            "accuracy": round(n_correct / n, 4) if n else 0.0,
        }
    return result


def compute_reasoning_type_accuracy(pairs: List[Dict], tol: float = TOLERANCE) -> Dict[str, Dict]:
    buckets: Dict[str, List] = defaultdict(list)
    for p in pairs:
        for rt in p["sample"].get("reasoning_type", ["unknown"]):
            buckets[rt].append(p)

    result = {}
    for rt, rt_pairs in sorted(buckets.items()):
        n = len(rt_pairs)
        n_correct = sum(1 for p in rt_pairs if is_correct(p["prediction"], p["sample"]["ground_truth"], tol))
        result[rt] = {
            "n":        n,
            "correct":  n_correct,
            "accuracy": round(n_correct / n, 4) if n else 0.0,
        }
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Order-of-magnitude error distribution
# ─────────────────────────────────────────────────────────────────────────────

def compute_magnitude_distribution(pairs: List[Dict]) -> Dict[str, int]:
    """
    Buckets wrong predictions by log10 distance — surfaces magnitude errors.
    """
    dist = defaultdict(int)
    for p in pairs:
        if is_correct(p["prediction"], p["sample"]["ground_truth"]):
            continue
        lr = log_ratio(p["prediction"], p["sample"]["ground_truth"])
        if lr is None:
            dist["zero_gt_or_pred"] += 1
        elif abs(lr) < 0.5:
            dist["< 0.5 orders (close)"] += 1
        elif abs(lr) < 1.5:
            dist["0.5–1.5 orders"] += 1
        elif abs(lr) < 2.5:
            dist["1.5–2.5 orders"] += 1
        else:
            dist["> 2.5 orders"] += 1
    return dict(dist)


# ─────────────────────────────────────────────────────────────────────────────
# Calibration
# ─────────────────────────────────────────────────────────────────────────────

def compute_calibration(pairs: List[Dict], n_bins: int = 5) -> Dict:
    """
    Bucket predictions by |relative error| magnitude.
    Useful for showing whether errors are distributed or concentrated.
    """
    bins = [(i / n_bins, (i + 1) / n_bins) for i in range(n_bins)]
    bin_counts = {f"{lo:.0%}–{hi:.0%}": 0 for lo, hi in bins}
    overflow = 0

    for p in pairs:
        gt   = p["sample"]["ground_truth"]
        pred = p["prediction"]
        re   = relative_error(pred, gt)
        if re is None:
            overflow += 1
            continue
        are = abs(re)
        placed = False
        for lo, hi in bins:
            if lo <= are < hi:
                bin_counts[f"{lo:.0%}–{hi:.0%}"] += 1
                placed = True
                break
        if not placed:
            overflow += 1

    return {"bins": bin_counts, "overflow (>100% or zero gt)": overflow}