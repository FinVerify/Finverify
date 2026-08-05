#!/usr/bin/env python3
"""Aggregate pre-collected annotator votes into llm_annotation_ledger.jsonl.

Phase 9C-I4-R1: the candidate-ID universe is no longer taken from an
independent file. It is derived directly from the validated raw ledger
(default-deny, hash/count/duplicate-checked via
``verification.eligibility.engine.load_raw_ledger``, wrapped by
``run2_integrity.validate_and_load_raw_ledger``), and the supplied votes
must cover that exact universe -- no missing, no extra, no duplicates.

This script never calls a model, network endpoint, or FinVerify -- it
consumes votes already collected offline (one JSONL file, one record per
AnnotatorVote) and applies only the frozen deterministic aggregation rule.
Running against the production Run-2 candidate set requires
--allow-annotation-production plus a valid --implementation-commit and, for
the real Run-2 path, --freeze-metadata pointing at the canonical
SECOND_RUN_FREEZE.json (Gate 1, default-deny; see
verification.eligibility.amendment2_freeze).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verification.eligibility.amendment2_freeze import authorize_annotation_run
from verification.eligibility.annotation_models import AnnotatorVote
from verification.eligibility.annotation_runner import run_annotation
from verification.eligibility.run2_integrity import (
    provenance_header_lines, validate_and_load_raw_ledger, validate_exact_candidate_universe,
)
from verification.eligibility.serialization import json_bytes, write_new


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-ledger", type=Path, required=True, help="the raw Run-2 candidate ledger; the candidate-ID universe is derived from this, not supplied independently")
    parser.add_argument("--annotation-config", type=Path, required=True, help="frozen annotation_config.lock.json, for provenance stamping")
    parser.add_argument("--votes", type=Path, required=True, help="JSONL of AnnotatorVote records")
    parser.add_argument("--output", type=Path, required=True, help="path for llm_annotation_ledger.jsonl")
    parser.add_argument("--retry-count", type=int, default=0)
    parser.add_argument("--allow-annotation-production", action="store_true")
    parser.add_argument("--freeze-metadata", type=Path, default=None, help="required for the real Run-2 path; canonical SECOND_RUN_FREEZE.json")
    parser.add_argument("--implementation-commit", default="UNRECORDED")
    args = parser.parse_args()

    authorize_annotation_run(
        allow_annotation_production=args.allow_annotation_production,
        implementation_commit=args.implementation_commit,
    )

    # Fail closed: default-deny + hash/count/duplicate validation against
    # the frozen Run-2 contract (a no-op check for non-Run-2/synthetic
    # paths, exactly as engine.load_raw_ledger already behaves).
    validated = validate_and_load_raw_ledger(
        args.raw_ledger,
        allow_production=args.allow_annotation_production,
        freeze_metadata_path=args.freeze_metadata,
        implementation_commit=args.implementation_commit,
    )
    canonical_ids = validated.candidate_ids
    annotation_config_sha256 = hashlib.sha256(args.annotation_config.read_bytes()).hexdigest()

    votes_by_candidate: dict[str, list[AnnotatorVote]] = defaultdict(list)
    for line in args.votes.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        vote = AnnotatorVote(**row)
        votes_by_candidate[vote.candidate_id].append(vote)

    # Fail closed: the votes file must cover exactly the canonical
    # candidate universe derived from the validated raw ledger -- no
    # missing, no extra, no duplicate candidate_id.
    validate_exact_candidate_universe(votes_by_candidate.keys(), canonical_ids, context="annotation votes")

    records = run_annotation(list(canonical_ids), votes_by_candidate, retry_count=args.retry_count)
    serializable = [asdict(r) for r in sorted(records, key=lambda rec: rec.candidate_id)]

    header = "\n".join(provenance_header_lines({
        "raw_ledger_sha256": validated.sha256,
        "annotation_config_sha256": annotation_config_sha256,
        "candidate_count": str(len(canonical_ids)),
    })) + "\n"
    body = b"".join(json_bytes(d) for d in serializable)
    data = header.encode("utf-8") + body
    digest = write_new(args.output, data)
    print("froze llm_annotation_ledger.jsonl sha256=%s (%d records)" % (digest, len(serializable)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
