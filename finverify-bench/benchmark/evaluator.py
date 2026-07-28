"""
FinVerifyBench — Evaluator
Given a dataset and model predictions, returns a full evaluation report.

Usage:
    from benchmark.evaluator import evaluate
    report = evaluate(dataset, predictions)
    print(json.dumps(report, indent=2))
"""

import json
import math
from typing import Any, Dict, List, Optional

from benchmark.validators import validate_predictions
from benchmark.metrics import (
    compute_overall_accuracy,
    compute_mean_relative_error,
    compute_median_relative_error,
    compute_bias_statistics,
    compute_category_accuracy,
    compute_difficulty_accuracy,
    compute_reasoning_type_accuracy,
    compute_magnitude_distribution,
    compute_calibration,
    TOLERANCE,
)


def evaluate(
    dataset: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
    tolerance: float = TOLERANCE,
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Main evaluation entry point.

    Args:
        dataset:     List of benchmark samples (validated).
        predictions: List of {"id": str, "prediction": float} dicts.
        tolerance:   Relative tolerance for exact match (default 5%).
        strict:      If True, raise on prediction validation errors.

    Returns:
        Full evaluation report as a dict.
    """
    # ── Align predictions with samples ───────────────────────────────────────
    aligned, pred_errors = validate_predictions(predictions, dataset)

    if pred_errors:
        if strict:
            raise ValueError(f"Prediction validation errors:\n" + "\n".join(pred_errors))
        print(f"[Evaluator] {len(pred_errors)} prediction issues (run with strict=True to raise):")
        for e in pred_errors[:10]:
            print(f"  • {e}")
        if len(pred_errors) > 10:
            print(f"  ... and {len(pred_errors) - 10} more")

    n_total     = len(dataset)
    n_evaluated = len(aligned)
    n_correct   = sum(
        1 for p in aligned
        if not math.isnan(p["prediction"]) and
           abs(p["prediction"] - p["sample"]["ground_truth"]) /
           max(abs(p["sample"]["ground_truth"]), 1e-9) <= tolerance
    )

    report: Dict[str, Any] = {
        "meta": {
            "n_dataset":     n_total,
            "n_evaluated":   n_evaluated,
            "n_skipped":     n_total - n_evaluated,
            "tolerance_pct": tolerance * 100,
            "benchmark":     "FinVerifyBench v1.0",
        },
        "overall": {
            "accuracy":              round(compute_overall_accuracy(aligned, tolerance), 4),
            "mean_relative_error":   round(compute_mean_relative_error(aligned), 4),
            "median_relative_error": round(compute_median_relative_error(aligned), 4),
        },
        "bias_statistics":           compute_bias_statistics(aligned),
        "error_category_breakdown":  compute_category_accuracy(aligned, tolerance),
        "difficulty_breakdown":      compute_difficulty_accuracy(aligned, tolerance),
        "reasoning_type_breakdown":  compute_reasoning_type_accuracy(aligned, tolerance),
        "magnitude_error_distribution": compute_magnitude_distribution(aligned),
        "calibration":               compute_calibration(aligned),
        "prediction_errors":         pred_errors,
    }

    # ── Paper comparison summary ──────────────────────────────────────────────
    paper_accuracy = 0.4261  # DVL + FT on FinQA dev, from paper
    model_acc = report["overall"]["accuracy"]
    report["paper_comparison"] = {
        "paper_dvl_ft_accuracy":  paper_accuracy,
        "this_model_accuracy":    model_acc,
        "gap_to_paper_pp":        round((model_acc - paper_accuracy) * 100, 2),
        "paper_underestimation_rate": 0.609,
        "this_model_underestimation_rate": report["bias_statistics"]["underestimation_rate"],
    }

    return report


def evaluate_from_files(
    dataset_path: str,
    predictions_path: str,
    output_path: Optional[str] = None,
    tolerance: float = TOLERANCE,
) -> Dict[str, Any]:
    """Convenience wrapper: load files, evaluate, optionally save report."""
    with open(dataset_path) as f:
        dataset = json.load(f)
    with open(predictions_path) as f:
        predictions = json.load(f)

    report = evaluate(dataset, predictions, tolerance=tolerance)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[Evaluator] Report saved to {output_path}")

    return report


def print_report(report: Dict[str, Any]) -> None:
    """Pretty-print a summary of the evaluation report to stdout."""
    meta = report["meta"]
    ov   = report["overall"]
    bias = report["bias_statistics"]
    cmp  = report["paper_comparison"]

    print("=" * 60)
    print(f"  FinVerifyBench Evaluation Report")
    print("=" * 60)
    print(f"  Samples evaluated : {meta['n_evaluated']} / {meta['n_dataset']}")
    print(f"  Tolerance         : {meta['tolerance_pct']:.0f}% relative")
    print()
    print(f"  Overall Accuracy  : {ov['accuracy']*100:.2f}%")
    print(f"  Mean Rel. Error   : {ov['mean_relative_error']*100:.1f}%")
    print(f"  Median Rel. Error : {ov['median_relative_error']*100:.1f}%")
    print()
    print(f"  Bias Analysis (wrong predictions only):")
    print(f"    Underestimation : {bias['underestimation_rate']*100:.1f}%  "
          f"(paper: 60.9%)")
    print(f"    Overestimation  : {bias['overestimation_rate']*100:.1f}%")
    print()
    print(f"  Gap to paper DVL+FT: {cmp['gap_to_paper_pp']:+.2f} pp")
    print()
    print("  Accuracy by Error Category:")
    for cat, stats in report["error_category_breakdown"].items():
        bar = "█" * int(stats["accuracy"] * 20)
        print(f"    {cat:<25} {stats['accuracy']*100:5.1f}%  [{bar:<20}]  n={stats['n']}")
    print()
    print("  Accuracy by Difficulty:")
    for diff, stats in report["difficulty_breakdown"].items():
        print(f"    {diff:<10} {stats['accuracy']*100:5.1f}%   n={stats['n']}")
    print("=" * 60)
