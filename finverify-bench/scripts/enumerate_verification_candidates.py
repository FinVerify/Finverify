#!/usr/bin/env python3
"""Enumerate raw quantitative candidates from a non-production manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from verification.enumeration.ledger import EnumerationError, enumerate_manifest, write_candidate_ledger, write_issue_ledger
from verification.enumeration.manifest import ManifestError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--issues", required=True, type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--source-id", action="append", dest="source_ids")
    args = parser.parse_args()
    try:
        candidates, issues = enumerate_manifest(args.manifest, source_root=args.source_root, source_ids=args.source_ids)
        write_candidate_ledger(args.output, candidates)
        write_issue_ledger(args.issues, issues)
    except (EnumerationError, ManifestError, OSError) as exc:
        print("enumeration failed: %s" % exc, file=sys.stderr)
        return 1
    print("enumerated %d raw candidates" % len(candidates))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
