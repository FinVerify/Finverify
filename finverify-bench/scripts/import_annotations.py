#!/usr/bin/env python3
"""Validate and preserve raw annotation responses."""

import argparse
import json

from verification.annotations import import_annotations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--raw-output", required=True)
    args = parser.parse_args()
    with open(args.mapping, encoding="utf-8") as handle:
        item_ids = json.load(handle).keys()
    annotations = import_annotations(args.input, item_ids=item_ids, raw_output=args.raw_output)
    print("preserved %d raw annotations" % len(annotations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
