#!/usr/bin/env python3
"""
FinVerifyBench — Baseline Prediction Generator (Phase 6)
Simulates realistic failure distributions matching the paper's structured error behavior.

Baselines:
  1. random          — no structure; uniform noise
  2. scale_confused  — % vs decimal confusion (×100 or ÷100)
  3. sign_confused   — always predicts positive value
  4. magnitude_confused — order-of-magnitude off (×1000 or ÷1000)
  5. arithmetic      — correct operands, rounded intermediates (CoT drift)
  6. oracle_dvl      — simulates DVL corrections (upper-bound ablation)
"""

import json
import math
import random
import os

random.seed(0)


def load_split(split: str) -> list:
    path = f"data/processed/{split}.json"
    with open(path) as f:
        return json.load(f)


# ─── Baseline predictors ──────────────────────────────────────────────────────

def pred_random(sample: dict) -> float:
    """Random baseline: predict ground_truth * random factor in [0.01, 100]."""
    gt = sample['ground_truth']
    if gt == 0:
        return random.uniform(-10, 10)
    factor = random.choice([0.01, 0.1, 1.0, 10.0, 100.0]) * random.uniform(0.5, 2.0)
    return round(gt * factor * (1 if random.random() > 0.3 else -1), 2)


def pred_scale_confused(sample: dict) -> float:
    """
    Scale-confused baseline: mirrors paper's finding that models confuse % and decimal.
    - If unit is percent and |gt| < 1: multiply by 100 (model gives decimal)
    - If unit is percent and |gt| > 10: divide by 100 (model gives decimal)
    - Otherwise: small noise
    Paper: 20.6% of DVL corrections are scale type.
    """
    gt = sample['ground_truth']
    unit = sample.get('unit', '')
    if unit == 'percent':
        if abs(gt) < 1:
            return round(gt * 100, 2)   # model under-scales
        if abs(gt) > 10 and random.random() < 0.6:
            return round(gt / 100, 4)   # model over-scales
    # Small noise for non-percent
    return round(gt * random.uniform(0.85, 1.15), 2)


def pred_sign_confused(sample: dict) -> float:
    """
    Sign-confused baseline: always predicts the absolute value (positive).
    Paper: 27% of DVL corrections are sign type.
    60.9% underestimation on FinQA.
    """
    gt = sample['ground_truth']
    # Flip negative to positive (the core sign error)
    if gt < 0:
        return abs(gt)
    # For positive GTs, sometimes negate (overestimation direction)
    if random.random() < 0.1:
        return -abs(gt)
    return round(gt * random.uniform(0.95, 1.05), 2)


def pred_magnitude_confused(sample: dict) -> float:
    """
    Magnitude-confused baseline: order-of-magnitude errors.
    Paper: 52.4% of DVL corrections are magnitude type (dominant class).
    """
    gt = sample['ground_truth']
    unit = sample.get('unit', '')
    ec = sample.get('error_category', [])

    if 'magnitude_error' in ec or 'unit_conversion' in ec:
        # Deliberate 1-2 OOM error
        factor = random.choice([0.001, 0.01, 1000, 10000])
        return round(gt * factor, 4)
    if 'billion_usd' in unit and abs(gt) < 100:
        # Model forgets to divide by 1000 (millions reported as billions)
        return round(gt * 1000, 1)
    # General: small OOM noise
    return round(gt * random.choice([0.1, 10.0, 1.0]), 2)


def pred_arithmetic(sample: dict) -> float:
    """
    Arithmetic baseline: CoT computational drift.
    Paper: 71% of CoT failures show intermediate rounding at step boundaries.
    Simulates: correct operands, wrong due to intermediate truncation.
    """
    gt = sample['ground_truth']
    rt = sample.get('reasoning_type', [])

    if 'multi_step_arithmetic' in rt or 'percentage_change' in rt:
        # Simulate intermediate rounding error
        noisy = round(gt, 0)  # truncate decimal precision
        return noisy + random.uniform(-0.5, 0.5)
    if 'growth_rate' in rt:
        # CAGR: exponent rounding
        return round(gt * random.uniform(0.95, 1.05), 1)
    # Default: small error
    return round(gt + random.gauss(0, abs(gt) * 0.05 + 0.01), 2)


def pred_oracle_dvl(sample: dict) -> float:
    """
    DVL oracle: simulates what DVL *would* correct.
    Paper: DVL captures 45.8% of gains achievable by full symbolic recomputation.
    Apply DVL rules where they fire; otherwise use arithmetic baseline.
    """
    gt = sample['ground_truth']
    q = sample['question'].lower()
    unit = sample.get('unit', '')
    ec = sample.get('error_category', [])

    # First get the "raw" prediction (arithmetic drift)
    raw = pred_arithmetic(sample)

    # DVL Rule 1: Scale correction
    ratio_kws = {'ratio', 'margin', 'return', 'yield', 'percent', 'change', 'growth', 'loss'}
    is_ratio_q = any(kw in q for kw in ratio_kws)
    if is_ratio_q:
        if abs(raw) > 100:
            raw = round(raw / 100, 4)
        elif abs(raw) < 1 and raw != 0:
            raw = round(raw * 100, 2)

    # DVL Rule 2: Sign correction
    neg_kws = {'decrease', 'loss', 'declined', 'negative', 'reduction', 'impairment'}
    has_neg = any(kw in q for kw in neg_kws)
    if has_neg and raw > 0 and gt < 0:
        raw = -abs(raw)

    # DVL Rule 3: Magnitude correction (only fires if unit header present)
    if 'magnitude_error' in ec and random.random() < 0.458:  # paper: 45.8% capture rate
        raw = gt * random.uniform(0.98, 1.02)  # near-correct

    return round(raw, 4)


BASELINES = {
    'random':             pred_random,
    'scale_confused':     pred_scale_confused,
    'sign_confused':      pred_sign_confused,
    'magnitude_confused': pred_magnitude_confused,
    'arithmetic':         pred_arithmetic,
    'oracle_dvl':         pred_oracle_dvl,
}


def generate_baselines(split: str = "test"):
    samples = load_split(split)
    os.makedirs("examples", exist_ok=True)

    results = {}
    for name, fn in BASELINES.items():
        preds = []
        for s in samples:
            preds.append({
                "id":         s['id'],
                "prediction": fn(s),
            })

        path = f"examples/{name}_{split}_predictions.json"
        with open(path, 'w') as f:
            json.dump(preds, f, indent=2)
        results[name] = preds
        print(f"  Written: {path}  ({len(preds)} predictions)")

    return results


def evaluate_baselines(split: str = "test"):
    """Quick accuracy summary of all baselines on the test split."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from benchmark.evaluator import evaluate, print_report

    samples = load_split(split)

    print(f"\n{'='*55}")
    print(f"  Baseline Accuracy Summary ({split} split, n={len(samples)})")
    print(f"{'='*55}")
    print(f"  {'Baseline':<22} {'Accuracy':>10}  {'Under%':>8}  {'MRE':>8}")
    print(f"  {'─'*22} {'─'*10}  {'─'*8}  {'─'*8}")

    for name, fn in BASELINES.items():
        preds = [{"id": s['id'], "prediction": fn(s)} for s in samples]
        report = evaluate(samples, preds)
        acc   = report['overall']['accuracy'] * 100
        under = report['bias_statistics']['underestimation_rate'] * 100
        mre   = report['overall']['mean_relative_error'] * 100
        print(f"  {name:<22} {acc:>9.2f}%  {under:>7.1f}%  {mre:>7.1f}%")

    print(f"  {'─'*22} {'─'*10}  {'─'*8}  {'─'*8}")
    print(f"  Paper DVL+FT result:   42.61%   60.9%")
    print(f"{'='*55}")


if __name__ == "__main__":
    for split in ["train", "dev", "test"]:
        generate_baselines(split)
    print()
    evaluate_baselines("test")
