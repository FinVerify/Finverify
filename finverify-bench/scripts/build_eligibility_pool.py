"""Build eligibility construction artifacts from a reviewed ledger.

Production Run-2 execution is intentionally default-deny in engine.load_raw_ledger.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import sys
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verification.eligibility.engine import load_raw_ledger, build_eligibility
from verification.eligibility.models import SourceDescriptor
from verification.eligibility.serialization import json_bytes, jsonl_bytes, write_new


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--source-groups", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-production", action="store_true")
    parser.add_argument("--freeze-metadata", type=Path)
    parser.add_argument("--implementation-commit")
    args = parser.parse_args()
    raw = load_raw_ledger(args.ledger, allow_production=args.allow_production, freeze_metadata_path=args.freeze_metadata, implementation_commit=args.implementation_commit)
    reviews = [json.loads(line) for line in args.reviews.read_text(encoding="utf-8").splitlines() if line.strip()]
    descriptors = [SourceDescriptor(**json.loads(line)) for line in args.source_groups.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = build_eligibility(raw, reviews, descriptors)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for name, value in (
        ("eligibility_ledger.jsonl", jsonl_bytes(result["eligibility_ledger"])),
        ("eligible_natural_pool.jsonl", jsonl_bytes(result["eligible_natural_pool"])),
        ("controlled_parent_pool.jsonl", jsonl_bytes(result["controlled_parent_pool"])),
        ("eligibility_summary.json", json_bytes(result["summary"])),
    ):
        artifacts[name] = write_new(args.output_dir / name, value)
    descriptors_json = [asdict(item) for item in descriptors]
    group_manifest = {"protocol_version": "SOURCE_ELIGIBILITY_v1+AMENDMENT_1", "groups": [
        dict(item, source_group_id=result["source_group_map"].get(item["source_id"]))
        for item in sorted(descriptors_json, key=lambda value: value["source_id"])
    ]}
    artifacts["source_group_manifest.json"] = write_new(args.output_dir / "source_group_manifest.json", json_bytes(group_manifest))
    input_hash = hashlib.sha256(args.ledger.read_bytes()).hexdigest()
    freeze = {
        "phase": "9C-G", "protocol_version": "SOURCE_ELIGIBILITY_v1+AMENDMENT_1",
        "implementation_commit": args.implementation_commit or "UNRECORDED",
        "input_ledger": {"path": str(args.ledger), "sha256": input_hash},
        "artifacts": artifacts,
    }
    write_new(args.output_dir / "ELIGIBILITY_FREEZE.json", json_bytes(freeze))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
