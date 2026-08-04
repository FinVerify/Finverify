#!/usr/bin/env python3
"""Validate a FinVerifyBench-Verify JSONL dataset."""

import argparse
import json
import sys

from verification.io import read_pairs
from verification.summary import summarize_pairs
from verification.validators import validate_dataset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    pairs = read_pairs(args.input)
    errors = validate_dataset(pairs)
    result = {"valid": not errors, "pair_count": len(pairs), "summary": summarize_pairs(pairs), "errors": errors}
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("valid: %d pairs" % len(pairs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
