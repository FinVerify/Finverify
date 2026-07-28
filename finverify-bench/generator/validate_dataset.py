#!/usr/bin/env python3
"""
FinVerifyBench — Dataset Validator (Phase 5)
Validates schema, checks all fields, reports errors.
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DVL_mapping.validators import validate_dataset


def run(path: str) -> int:
    with open(path) as f:
        samples = json.load(f)

    valid, invalid = validate_dataset(samples)

    print(f"\n[Validator] {path}")
    print(f"  Valid:   {len(valid)}")
    print(f"  Invalid: {len(invalid)}")

    if invalid:
        for s in invalid[:10]:
            print(f"\n  FAIL {s.get('id','?')}:")
            for e in s.get('_validation_errors', []):
                print(f"    • {e}")
    else:
        print("  ✓ All samples valid")

    warnings = [s for s in valid if '_warnings' in s]
    if warnings:
        print(f"\n  Warnings ({len(warnings)} samples):")
        for s in warnings[:5]:
            for w in s['_warnings']:
                print(f"    ⚠ {s['id']}: {w}")

    return len(invalid)


if __name__ == "__main__":
    total = 0
    for split in ["train", "dev", "test"]:
        p = f"data/processed/{split}.json"
        if os.path.exists(p):
            total += run(p)
    print(f"\n[Validator] Total invalid: {total}")
    sys.exit(0 if total == 0 else 1)