#!/usr/bin/env python3
"""Export a blinded annotation CSV and a private item mapping."""

import argparse
import json

from verification.annotations import export_annotation_rows, write_annotation_csv
from verification.io import read_pairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--seed", type=int, default=20260805)
    args = parser.parse_args()
    rows, mapping = export_annotation_rows(read_pairs(args.input), seed=args.seed)
    write_annotation_csv(args.output, rows)
    with open(args.mapping, "w", encoding="utf-8") as handle:
        json.dump(mapping, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("exported %d blinded annotation items" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
