#!/usr/bin/env python3
"""Create a read-only SHA-256 freeze manifest."""

import argparse
import json

from verification.freeze import build_freeze_manifest, write_freeze_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--command")
    args = parser.parse_args()
    manifest = build_freeze_manifest(args.input, seed=args.seed, creation_command=args.command)
    write_freeze_manifest(args.output, manifest)
    print("wrote freeze manifest: %s" % args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
