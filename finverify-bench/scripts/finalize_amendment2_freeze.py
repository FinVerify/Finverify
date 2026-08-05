#!/usr/bin/env python3
"""Assemble and freeze the final Amendment 2 ELIGIBILITY_FREEZE.json record.

Phase 9C-I4-R1: this script no longer accepts a caller-supplied
raw_ledger_sha256 as proof of anything. The raw ledger artifact is
independently loaded and validated against the frozen Run-2 contract
(default-deny, hash/count/duplicate-checked) and its own freshly computed
digest is what goes into the freeze record. That computed digest is then
cross-checked, fail-closed, against the provenance headers already stamped
into the annotation ledger and audit manifest by the earlier pipeline
stages, so a caller cannot freeze a record whose upstream artifacts were
actually built from a different raw ledger.

Requires every upstream artifact to already exist and be hashed; this
script does not compute eligibility, annotation, or audit outcomes itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verification.eligibility.amendment2_freeze import ArtifactHashes, build_freeze_record
from verification.eligibility.run2_integrity import (
    parse_provenance_header, validate_and_load_raw_ledger, validate_provenance_hash,
)
from verification.eligibility.serialization import json_bytes, write_new


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_header(path: Path) -> dict[str, str]:
    return parse_provenance_header(path.read_text(encoding="utf-8").splitlines())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-ledger", type=Path, required=True, help="the actual raw Run-2 ledger artifact; its hash is independently derived here, never taken from --config")
    parser.add_argument("--config", type=Path, required=True, help="JSON with all non-hash freeze inputs (must NOT contain raw_ledger_sha256; it is rejected if present)")
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-production", action="store_true")
    parser.add_argument("--freeze-metadata", type=Path, default=None)
    parser.add_argument("--implementation-commit-for-ledger-load", default="UNRECORDED")
    args = parser.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    if "raw_ledger_sha256" in cfg:
        raise ValueError(
            "--config must not supply raw_ledger_sha256; it is independently derived from --raw-ledger "
            "(Phase 9C-I4-R1: a caller-supplied hash is never trusted as proof of artifact integrity)"
        )

    # Fail closed: independently load and validate the raw ledger; this is
    # the only source of the raw_ledger_sha256 used below.
    validated = validate_and_load_raw_ledger(
        args.raw_ledger,
        allow_production=args.allow_production,
        freeze_metadata_path=args.freeze_metadata,
        implementation_commit=args.implementation_commit_for_ledger_load,
    )

    d = args.artifacts_dir
    annotation_config_sha256 = _sha256(d / "annotation_config.lock.json")

    # Fail closed: cross-check the independently-derived raw-ledger digest
    # against what the upstream artifacts actually declare they were built
    # from, rather than assuming the artifacts-dir contents are consistent.
    annotation_header = _read_header(d / "llm_annotation_ledger.jsonl")
    validate_provenance_hash("raw_ledger_sha256", annotation_header.get("raw_ledger_sha256", ""), validated.sha256)
    validate_provenance_hash("annotation_config_sha256", annotation_header.get("annotation_config_sha256", ""), annotation_config_sha256)

    manifest_lines = (d / "audit_manifest_v1.csv").read_text(encoding="utf-8").splitlines()
    manifest_header = parse_provenance_header(manifest_lines)
    validate_provenance_hash("raw_ledger_sha256", manifest_header.get("raw_ledger_sha256", ""), validated.sha256)
    validate_provenance_hash("annotation_config_sha256", manifest_header.get("annotation_config_sha256", ""), annotation_config_sha256)

    hashes = ArtifactHashes(
        raw_ledger_sha256=validated.sha256,
        annotation_config_sha256=annotation_config_sha256,
        llm_annotation_ledger_sha256=_sha256(d / "llm_annotation_ledger.jsonl"),
        audit_manifest_sha256=_sha256(d / "audit_manifest_v1.csv"),
        human_audit_ledger_sha256=_sha256(d / "human_audit_ledger.jsonl"),
        eligibility_ledger_sha256=_sha256(d / "eligibility_ledger.jsonl"),
        source_group_manifest_sha256=_sha256(d / "source_group_manifest.json"),
        eligible_natural_pool_sha256=_sha256(d / "eligible_natural_pool.jsonl"),
        controlled_parent_pool_sha256=_sha256(d / "controlled_parent_pool.jsonl"),
        eligibility_summary_sha256=_sha256(d / "eligibility_summary.json"),
    )
    record = build_freeze_record(
        phase="9C-I4",
        artifact_hashes=hashes,
        audit_seed_hex_value=cfg["audit_seed_hex"],
        audit_size=cfg["audit_size"],
        double_coded_count=cfg["double_coded_count"],
        weighted_statistics=cfg["weighted_statistics"],
        kappa_report=cfg["kappa_report"],
        model_family_disjointness_attestation=cfg["model_family_disjointness_attestation"],
        annotation_gate_ts=cfg["annotation_gate_ts"],
        manifest_ts=cfg["manifest_ts"],
        audit_release_gate_ts=cfg["audit_release_gate_ts"],
        implementation_commit=cfg["implementation_commit"],
    )
    digest = write_new(args.output, json_bytes(record))
    print("froze ELIGIBILITY_FREEZE.json (Amendment 2) sha256=%s" % digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
