#!/usr/bin/env python3
"""Split verification pairs by source group."""

import argparse
import json

from verification.io import read_pairs, write_pairs
from verification.splitting import split_by_source_group


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--test-ratio", type=float, default=0.65)
    parser.add_argument("--seed", type=int, default=20260804)
    args = parser.parse_args()
    pairs, manifest = split_by_source_group(read_pairs(args.input), test_ratio=args.test_ratio, seed=args.seed)
    write_pairs(args.output, pairs)
    with open(args.manifest, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("split %d pairs: %d dev, %d test" % (len(pairs), manifest["dev_pair_count"], manifest["test_pair_count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
