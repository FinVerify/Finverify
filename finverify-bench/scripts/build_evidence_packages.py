#!/usr/bin/env python3
"""Freeze deterministic Section-7 evidence packages for the canonical Run-3 ledger."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verification.eligibility.evidence_package import build_evidence_packages
from verification.eligibility.run2_integrity import provenance_header_lines, validate_and_load_raw_ledger
from verification.eligibility.serialization import json_bytes, write_new


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-ledger", type=Path, required=True)
    parser.add_argument("--freeze-metadata", type=Path, required=True)
    parser.add_argument("--annotation-config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--allow-production", action="store_true")
    args = parser.parse_args()

    validated = validate_and_load_raw_ledger(
        args.raw_ledger,
        allow_production=args.allow_production,
        freeze_metadata_path=args.freeze_metadata,
        implementation_commit=args.implementation_commit,
    )
    config_sha = hashlib.sha256(args.annotation_config.read_bytes()).hexdigest()
    packages = build_evidence_packages(validated.records, args.repo_root)

    header = "\n".join(provenance_header_lines({
        "raw_ledger_sha256": validated.sha256,
        "annotation_config_sha256": config_sha,
        "candidate_count": str(len(packages)),
        "implementation_commit": args.implementation_commit,
        "evidence_schema": "section7-evidence-v1",
    })) + "\n"
    body = b"".join(json_bytes(item.to_dict()) for item in packages)
    digest = write_new(args.output, header.encode("utf-8") + body)
    print("froze evidence packages sha256=%s (%d records)" % (digest, len(packages)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
