#!/usr/bin/env python3
"""
FinVerifyBench — Dataset Statistics & Validation (Phase 5)
Checks: duplicates, template overlap, class balance, and generates report tables.
"""

import json
import math
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# Duplicate detection
# ──────────────────────────────────────────────────────────────────────────────

def fingerprint(sample: Dict) -> str:
    """Structural fingerprint: question + first 80 chars of context."""
    q = re.sub(r'\d+', 'N', sample['question'].lower().strip())
    c = re.sub(r'[\d,\.\$]+', 'N', sample['context'][:80].lower())
    return f"{q}|{c}"


def detect_duplicates(samples: List[Dict]) -> Tuple[List, List]:
    """Returns (exact_id_dups, template_overlap_groups)."""
    # Exact ID duplicates
    id_counts = Counter(s['id'] for s in samples)
    id_dups = [sid for sid, cnt in id_counts.items() if cnt > 1]

    # Template overlap
    fp_map = defaultdict(list)
    for s in samples:
        fp_map[fingerprint(s)].append(s['id'])
    overlaps = {fp: ids for fp, ids in fp_map.items() if len(ids) > 1}

    return id_dups, list(overlaps.values())


# ──────────────────────────────────────────────────────────────────────────────
# Class balance analysis
# ──────────────────────────────────────────────────────────────────────────────

def compute_class_stats(samples: List[Dict]) -> Dict:
    n = len(samples)
    cats   = Counter()
    diffs  = Counter()
    rts    = Counter()
    splits = Counter()
    units  = Counter()
    sources = Counter()

    for s in samples:
        for ec in s.get('error_category', []):
            cats[ec] += 1
        diffs[s.get('difficulty', 'unknown')] += 1
        for rt in s.get('reasoning_type', []):
            rts[rt] += 1
        splits[s.get('split', 'unknown')] += 1
        units[s.get('unit', 'unknown')] += 1
        sources[s.get('source_type', 'unknown')] += 1

    return {
        'n_total': n,
        'error_category': dict(cats),
        'difficulty': dict(diffs),
        'reasoning_type': dict(rts),
        'split': dict(splits),
        'unit': dict(units),
        'source_type': dict(sources),
    }


def chi_squared_balance(counts: Dict[str, int]) -> float:
    """Chi-squared statistic vs uniform null."""
    total = sum(counts.values())
    k = len(counts)
    if k < 2 or total == 0:
        return 0.0
    expected = total / k
    return sum((obs - expected) ** 2 / expected for obs in counts.values())


# ──────────────────────────────────────────────────────────────────────────────
# Ground-truth distribution analysis
# ──────────────────────────────────────────────────────────────────────────────

def gt_distribution(samples: List[Dict]) -> Dict:
    gts = [s['ground_truth'] for s in samples]
    pos = [x for x in gts if x > 0]
    neg = [x for x in gts if x < 0]
    zeros = sum(1 for x in gts if x == 0)
    log_vals = [math.log10(abs(x)) for x in gts if x != 0]

    return {
        'n_positive': len(pos),
        'n_negative': len(neg),
        'n_zero': zeros,
        'underestimation_baseline_rate': round(len(neg) / len(gts), 3),
        'log10_range': [round(min(log_vals), 2), round(max(log_vals), 2)] if log_vals else [],
        'mean_gt': round(sum(gts) / len(gts), 2) if gts else 0,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Report rendering
# ──────────────────────────────────────────────────────────────────────────────

def bar(count: int, total: int, width: int = 20) -> str:
    filled = int(count / total * width) if total else 0
    return '█' * filled + '░' * (width - filled)


def print_table(title: str, data: Dict[str, int], total: int):
    print(f"\n  {title}")
    print(f"  {'Category':<35} {'Count':>6}  {'%':>6}  {'Distribution'}")
    print(f"  {'─'*35} {'─'*6}  {'─'*6}  {'─'*22}")
    for k, v in sorted(data.items(), key=lambda x: -x[1]):
        pct = v / total * 100 if total else 0
        print(f"  {k:<35} {v:>6}  {pct:>5.1f}%  {bar(v, total)}")


def generate_report(all_samples: List[Dict], output_path: str = None) -> str:
    stats = compute_class_stats(all_samples)
    id_dups, template_overlaps = detect_duplicates(all_samples)
    gt_dist = gt_distribution(all_samples)
    n = stats['n_total']

    lines = []
    def p(s=""): lines.append(s)

    p("=" * 65)
    p("  FinVerifyBench — Dataset Statistics Report")
    p("=" * 65)
    p(f"  Total samples  : {n}")
    p(f"  Splits         : " + "  ".join(f"{k}={v}" for k, v in sorted(stats['split'].items())))
    p(f"  Duplicate IDs  : {len(id_dups)}")
    p(f"  Template overlaps: {len(template_overlaps)} groups")
    if id_dups:
        p(f"  ⚠  Duplicate IDs: {id_dups[:5]}")
    if template_overlaps:
        p(f"  ⚠  Overlap groups: {template_overlaps[:3]}")
    p()
    p("  Ground-Truth Distribution")
    p(f"    Positive GTs  : {gt_dist['n_positive']} ({gt_dist['n_positive']/n*100:.1f}%)")
    p(f"    Negative GTs  : {gt_dist['n_negative']} ({gt_dist['n_negative']/n*100:.1f}%)")
    p(f"    Zero GTs      : {gt_dist['n_zero']}")
    p(f"    Log10 range   : {gt_dist['log10_range']}")
    p(f"    Paper baseline underestimation : 60.9%")
    p()

    # Chi-squared for error categories
    cat_chi2 = chi_squared_balance(stats['error_category'])
    diff_chi2 = chi_squared_balance(stats['difficulty'])
    p(f"  Balance Statistics")
    p(f"    χ² error_category (vs uniform): {cat_chi2:.2f}  (lower = more balanced)")
    p(f"    χ² difficulty (vs uniform):     {diff_chi2:.2f}")
    p()

    report_text = '\n'.join(lines)
    print(report_text)

    # Tables
    print_table("Error Category Distribution", stats['error_category'], n)
    print_table("Difficulty Distribution",     stats['difficulty'],     n)
    print_table("Reasoning Type Distribution", stats['reasoning_type'], n)
    print_table("Source Type Distribution",    stats['source_type'],    n)
    print_table("Unit Distribution",           stats['unit'],           n)

    print("\n" + "=" * 65)

    # Also write markdown report
    if output_path:
        md_lines = [
            "# FinVerifyBench — Dataset Statistics\n",
            f"**Total samples:** {n}  \n",
            f"**Splits:** " + ", ".join(f"{k}={v}" for k, v in sorted(stats['split'].items())) + "  \n",
            f"\n## Error Category Distribution\n",
            "| Category | Count | % |",
            "|----------|-------|---|",
        ]
        for k, v in sorted(stats['error_category'].items(), key=lambda x: -x[1]):
            md_lines.append(f"| {k} | {v} | {v/n*100:.1f}% |")

        md_lines += [
            "\n## Difficulty Distribution\n",
            "| Difficulty | Count | % |",
            "|------------|-------|---|",
        ]
        for k, v in sorted(stats['difficulty'].items(), key=lambda x: -x[1]):
            md_lines.append(f"| {k} | {v} | {v/n*100:.1f}% |")

        md_lines += [
            "\n## Reasoning Type Distribution\n",
            "| Reasoning Type | Count | % |",
            "|----------------|-------|---|",
        ]
        for k, v in sorted(stats['reasoning_type'].items(), key=lambda x: -x[1]):
            md_lines.append(f"| {k} | {v} | {v/n*100:.1f}% |")

        md_lines += [
            "\n## Ground-Truth Analysis\n",
            f"- Positive: {gt_dist['n_positive']} ({gt_dist['n_positive']/n*100:.1f}%)",
            f"- Negative: {gt_dist['n_negative']} ({gt_dist['n_negative']/n*100:.1f}%)",
            f"- Log10 range: {gt_dist['log10_range']}",
            f"\n## Balance (χ²)\n",
            f"- Error category χ²: {cat_chi2:.2f}",
            f"- Difficulty χ²: {diff_chi2:.2f}",
        ]
        with open(output_path, 'w') as f:
            f.write('\n'.join(md_lines))
        print(f"\n  Markdown report saved: {output_path}")

    return report_text


if __name__ == "__main__":
    import os
    path = "data/processed/all.json"
    if not os.path.exists(path):
        print(f"Run create_dataset.py first. {path} not found.")
        sys.exit(1)

    with open(path) as f:
        samples = json.load(f)

    generate_report(samples, output_path="data/processed/statistics.md")