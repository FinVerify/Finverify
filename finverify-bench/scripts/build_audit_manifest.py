#!/usr/bin/env python3
"""Build audit_manifest_v1.csv from the frozen llm_annotation_ledger.jsonl.

Phase 9C-I4-R1: this script no longer trusts a supplied raw-ledger path at
face value. The raw ledger is independently reloaded and validated against
the frozen Run-2 contract (default-deny, hash/count/duplicate-checked),
and the annotation ledger is checked for exact one-record-per-candidate
coverage of that same canonical universe, plus provenance-hash agreement
with the raw ledger and the supplied annotation config, before any
sampling math runs. All of this fails closed.

The manifest is generated exactly once; this script refuses to overwrite
an existing file (see verification.eligibility.serialization.write_new).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verification.eligibility.annotation_runner import stratum_of
from verification.eligibility.audit_sampling import audit_seed_hex, build_manifest, manifest_csv_bytes
from verification.eligibility.run2_integrity import (
    IntegrityViolation, parse_provenance_header, validate_and_load_raw_ledger,
    validate_exact_candidate_universe, validate_provenance_hash,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-ledger", type=Path, required=True, help="the same raw Run-2 candidate ledger used for annotation")
    parser.add_argument("--annotation-ledger", type=Path, required=True)
    parser.add_argument("--annotation-config", type=Path, required=True, help="the same annotation_config.lock.json used to produce --annotation-ledger")
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-production", action="store_true")
    parser.add_argument("--freeze-metadata", type=Path, default=None)
    parser.add_argument("--implementation-commit", default="UNRECORDED")
    args = parser.parse_args()

    # Fail closed: re-derive and re-validate the raw ledger independently --
    # never trust that the annotation ledger's own header is honest about
    # what it was built from.
    validated = validate_and_load_raw_ledger(
        args.raw_ledger,
        allow_production=args.allow_production,
        freeze_metadata_path=args.freeze_metadata,
        implementation_commit=args.implementation_commit,
    )
    canonical_ids = validated.candidate_ids
    annotation_config_sha256 = hashlib.sha256(args.annotation_config.read_bytes()).hexdigest()

    ledger_text = args.annotation_ledger.read_text(encoding="utf-8")
    lines = ledger_text.splitlines()
    header = parse_provenance_header(lines)
    if "raw_ledger_sha256" not in header or "annotation_config_sha256" not in header:
        raise IntegrityViolation("annotation ledger is missing its provenance header; cannot verify what it was built from")
    validate_provenance_hash("raw_ledger_sha256", header["raw_ledger_sha256"], validated.sha256)
    validate_provenance_hash("annotation_config_sha256", header["annotation_config_sha256"], annotation_config_sha256)

    candidates_by_stratum: dict[str, list[str]] = {"A": [], "B": [], "C": []}
    seen_ids: list[str] = []
    for line in lines:
        if line.startswith("# "):
            continue
        if not line.strip():
            continue
        row = json.loads(line)
        seen_ids.append(row["candidate_id"])
        stratum = "C" if row["agreement_tier"] == "split" else ("A" if row["llm_annotation"] == "ELIGIBLE" else "B")
        candidates_by_stratum[stratum].append(row["candidate_id"])

    # Fail closed: exactly one annotation record per canonical candidate_id
    # -- no missing, no extra, no duplicate.
    validate_exact_candidate_universe(seen_ids, canonical_ids, context="annotation ledger")

    populations = {s: len(v) for s, v in candidates_by_stratum.items()}
    seed = audit_seed_hex(validated.sha256, annotation_config_sha256)
    rows = build_manifest(candidates_by_stratum, populations, n=args.n, audit_seed_hex_value=seed)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = manifest_csv_bytes(
        rows, generation_timestamp=timestamp, raw_ledger_sha256_lower=validated.sha256,
        annotation_config_sha256_lower=annotation_config_sha256, audit_seed_hex_value=seed,
    )
    if args.output.exists():
        raise FileExistsError("audit manifest already exists and is generated exactly once: %s" % args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print("froze audit_manifest_v1.csv sha256=%s audit_seed_hex=%s" % (hashlib.sha256(data).hexdigest(), seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
