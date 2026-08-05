#!/usr/bin/env python3
"""Import human-audit responses, restore identity, and resolve consensus/adjudication.

Consumes: the private candidate mapping, first-round responses, optional
second-round responses (required whenever a case diverges from the LLM
label or is in the fixed double-coded subset), and optional adjudication
records for human-human disagreements. Produces human_audit_ledger.jsonl
with the Amendment 2 Section 13 provenance fields.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verification.eligibility.double_coding import flatten, select_double_coded
from verification.eligibility.human_audit import AdjudicationRecord, PendingSecondReview, resolve_audit_outcome
from verification.eligibility.review_package import ReviewerResponse, import_responses
from verification.eligibility.run2_integrity import (
    IntegrityViolation, parse_provenance_header, validate_and_load_raw_ledger,
    validate_exact_candidate_universe, validate_provenance_hash,
)
from verification.eligibility.serialization import json_bytes, write_new


def _load_responses(path: Path) -> list[ReviewerResponse]:
    if not path.exists():
        return []
    return [ReviewerResponse(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--round1", type=Path, required=True)
    parser.add_argument("--round2", type=Path, required=False)
    parser.add_argument("--adjudications", type=Path, required=False, help="JSONL of AdjudicationRecord")
    parser.add_argument("--raw-ledger", type=Path, required=True)
    parser.add_argument("--annotation-config", type=Path, required=True)
    parser.add_argument("--annotation-ledger", type=Path, required=True, help="validated llm_annotation_ledger.jsonl")
    parser.add_argument("--audit-manifest", type=Path, required=True, help="validated audit_manifest_v1.csv")
    parser.add_argument("--allow-production", action="store_true")
    parser.add_argument("--freeze-metadata", type=Path, default=None)
    parser.add_argument("--implementation-commit", default="UNRECORDED")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    # R2: bind review routing to the canonical, integrity-checked machine
    # annotation ledger and deterministic audit manifest. No operator-supplied
    # label mapping or double-coded list is accepted.
    validated = validate_and_load_raw_ledger(
        args.raw_ledger, allow_production=args.allow_production,
        freeze_metadata_path=args.freeze_metadata, implementation_commit=args.implementation_commit,
    )
    config_sha256 = hashlib.sha256(args.annotation_config.read_bytes()).hexdigest()

    annotation_lines = args.annotation_ledger.read_text(encoding="utf-8").splitlines()
    annotation_header = parse_provenance_header(annotation_lines)
    validate_provenance_hash("raw_ledger_sha256", annotation_header.get("raw_ledger_sha256", ""), validated.sha256)
    validate_provenance_hash("annotation_config_sha256", annotation_header.get("annotation_config_sha256", ""), config_sha256)
    llm_by_candidate = {}
    annotation_ids = []
    for line in annotation_lines:
        if not line.strip() or line.startswith("# "):
            continue
        row = json.loads(line)
        cid = row["candidate_id"]
        annotation_ids.append(cid)
        llm_by_candidate[cid] = row["llm_annotation"]
    validate_exact_candidate_universe(annotation_ids, validated.candidate_ids, context="annotation ledger")

    manifest_lines = args.audit_manifest.read_text(encoding="utf-8").splitlines()
    manifest_header = parse_provenance_header(manifest_lines)
    validate_provenance_hash("raw_ledger_sha256", manifest_header.get("raw_ledger_sha256", ""), validated.sha256)
    validate_provenance_hash("annotation_config_sha256", manifest_header.get("annotation_config_sha256", ""), config_sha256)
    audit_seed = manifest_header.get("audit_seed_hex", "")
    if len(audit_seed) != 64 or any(c not in "0123456789abcdef" for c in audit_seed):
        raise IntegrityViolation("audit manifest has invalid or missing audit_seed_hex")

    csv_lines = [line for line in manifest_lines if line and not line.startswith("# ")]
    selected_by_stratum = {"A": [], "B": [], "C": []}
    manifest_ids = []
    for row in csv.DictReader(io.StringIO("\n".join(csv_lines))):
        cid = row["candidate_id"]
        manifest_ids.append(cid)
        if row["selected"] == "1":
            selected_by_stratum[row["stratum"]].append(cid)
    validate_exact_candidate_universe(manifest_ids, validated.candidate_ids, context="audit manifest")
    selected_ids = set().union(*map(set, selected_by_stratum.values()))
    double_coded = set(flatten(select_double_coded(selected_by_stratum, audit_seed_hex_value=audit_seed)))

    # R3: the private blinded row_id -> candidate_id mapping is itself a
    # scientific input. Bind every pair to the deterministic row-ID function
    # used by export_blinded_audit, not merely to the same candidate set. A
    # set-only check would miss a swap of two selected candidate IDs.
    expected_mapping = {
        "audit_item_" + hashlib.sha256(
            ("finverify-phase9c-audit-row-v1\n" + cid).encode("utf-8")
        ).hexdigest()[:16]: cid
        for cid in selected_ids
    }
    if mapping != expected_mapping:
        raise IntegrityViolation(
            "private audit mapping does not exactly match the deterministic selected-sample mapping"
        )

    # Restore reviewer identities only after every canonical input, including
    # the private mapping, has passed integrity validation.
    round1 = import_responses(_load_responses(args.round1), mapping)
    round2 = import_responses(_load_responses(args.round2), mapping) if args.round2 else {}

    reviewed_ids = set(round1) | set(round2)
    outside = sorted(reviewed_ids - selected_ids)
    if outside:
        raise IntegrityViolation("human review contains candidate_id(s) outside selected audit sample: %s" % outside[:5])

    adjudications: dict[str, AdjudicationRecord] = {}
    if args.adjudications and args.adjudications.exists():
        for line in args.adjudications.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            adjudications[row["candidate_id"]] = AdjudicationRecord(**row)

    outcomes = []
    pending = []
    for candidate_id, response in sorted(round1.items()):
        try:
            outcome = resolve_audit_outcome(
                candidate_id=candidate_id,
                llm_annotation=llm_by_candidate[candidate_id],
                human_audit_label=response.verdict,
                human_audit_label_2=(round2[candidate_id].verdict if candidate_id in round2 else None),
                is_double_coded=candidate_id in double_coded,
                adjudication=adjudications.get(candidate_id),
            )
            outcomes.append(outcome)
        except PendingSecondReview as exc:
            pending.append({"candidate_id": candidate_id, "reason": str(exc)})

    from dataclasses import asdict
    write_new(args.output, b"".join(json_bytes(asdict(o)) for o in outcomes))
    if pending:
        print("WARNING: %d cases still pending further review/adjudication:" % len(pending))
        for item in pending:
            print("  -", item["candidate_id"], ":", item["reason"])
    print("resolved %d audit outcomes" % len(outcomes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
