#!/usr/bin/env python3
"""
FinVerify Smoke Benchmark – v1.0.2
Default behaviour ignores trust labels; use --check-labels to verify them.
"""
import json
import math
import sys
import time
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from core.engine import verify
from core.models import Claim


def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def get_environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": get_git_commit(),
        "benchmark_version": "1.0.2",
    }


def run_single_case(case: dict[str, Any], check_labels: bool = False) -> dict[str, Any]:
    claim = Claim(
        question=case["question"],
        raw_value=case["raw_value"],
    )
    start = time.perf_counter()
    result = verify(claim)
    elapsed = (time.perf_counter() - start) * 1000

    expected = case["expected_verified"]
    actual = result.verified_value
    value_ok = math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)

    expected_rules = set(case.get("expected_corrections", []))
    actual_rules = {c.get("rule", "") for c in result.correction_log}
    corrections_ok = expected_rules == actual_rules

    label_ok = True
    if check_labels and "expected_label" in case:
        label_ok = result.trust_score.label == case["expected_label"]

    passed = value_ok and corrections_ok and label_ok

    return {
        "id": case["id"],
        "category": case.get("category", "uncategorized"),
        "passed": passed,
        "value_ok": value_ok,
        "corrections_ok": corrections_ok,
        "label_ok": label_ok,
        "verified": actual,
        "expected": expected,
        "label": result.trust_score.label,
        "expected_label": case.get("expected_label"),
        "corrections": actual_rules,
        "expected_corrections": expected_rules,
        "runtime_ms": elapsed,
    }


def run_benchmark(dataset_path: Path, check_labels: bool = False) -> dict[str, Any]:
    with open(dataset_path) as f:
        data = json.load(f)

    cases = data["cases"]
    results = []
    passed_count = 0
    category_stats: dict[str, dict[str, int]] = {}
    total_runtime_ms = 0.0

    for case in cases:
        res = run_single_case(case, check_labels)
        results.append(res)
        total_runtime_ms += res["runtime_ms"]
        if res["passed"]:
            passed_count += 1

        cat = res["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0}
        category_stats[cat]["total"] += 1
        if res["passed"]:
            category_stats[cat]["passed"] += 1

    total = len(cases)
    return {
        "benchmark_version": data.get("version", "unknown"),
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "success": passed_count == total,
        "category_stats": category_stats,
        "results": results,
        "environment": get_environment(),
        "timestamp": datetime.utcnow().isoformat(),
        "total_runtime_ms": total_runtime_ms,
        "check_labels": check_labels,
    }


def print_summary(report: dict[str, Any]) -> None:
    print("=" * 50)
    print("FinVerify Smoke Benchmark")
    print("=" * 50)
    print(f"Version: {report['benchmark_version']}")
    print(f"Total cases: {report['total']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print(f"Success: {'✅ YES' if report['success'] else '❌ NO'}")
    print(f"Git commit: {report['environment']['git_commit']}")
    print(f"Runtime: {report.get('total_runtime_ms', 0):.2f} ms")
    print(f"Label checking: {'ON' if report.get('check_labels') else 'OFF'}")
    print("-" * 50)
    print("Category breakdown:")
    for cat, stats in report["category_stats"].items():
        print(f"  {cat:12} {stats['passed']}/{stats['total']}")
    print("=" * 50)

    if report["failed"] > 0:
        print("\n❌ Failed cases:")
        for res in report["results"]:
            if not res["passed"]:
                print(f"  - {res['id']} (category: {res['category']})")
                if not res["value_ok"]:
                    print(f"      Value mismatch: expected {res['expected']} got {res['verified']}")
                if not res["corrections_ok"]:
                    print(f"      Correction mismatch: expected {res['expected_corrections']} got {res['corrections']}")
                if not res["label_ok"]:
                    exp = res.get("expected_label", "N/A")
                    print(f"      Label mismatch: expected {exp} got {res['label']}")


def export_report(report: dict[str, Any], path: Path) -> None:
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Report exported to {path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", help="Export results to JSON file", type=Path)
    parser.add_argument("--check-labels", action="store_true", help="Also verify trust labels (for compatibility mode)")
    args = parser.parse_args()

    dataset = Path(__file__).parent / "smoke.json"
    report = run_benchmark(dataset, check_labels=args.check_labels)
    print_summary(report)

    if args.export:
        export_report(report, args.export)

    sys.exit(0 if report["success"] else 1)