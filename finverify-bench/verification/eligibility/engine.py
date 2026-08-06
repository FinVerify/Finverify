"""Verifier-blind deterministic post-review eligibility construction."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .duplicates import canonical_sort_key, fact_cluster_id, identity_key
from .models import CHALLENGEABLE_DIMENSIONS, ReviewDecision, SourceDescriptor
from .normalization import determinate, normalize_identity, normalized_value_key
from .review import review_from_dict, validate_review_set

RUN2_SUFFIX = "data/verification/enumeration/raw_candidate_ledger_run2.jsonl"
RUN2_SHA256 = "ec9532fa60225be63d5446ca2137b260255d97a74354a25e82f1b3ecd62a0093"
RUN2_COMMIT = "252afe742cecae4f53a5f92d65fa35f25d2538bb"
RUN2_COUNT = 14118
RUN2_FREEZE_PATH = Path(__file__).resolve().parents[2] / "data" / "verification" / "enumeration" / "SECOND_RUN_FREEZE.json"
RUN2_FREEZE_SHA256 = "f69357c568ec256716da514999431667f3e3418ac510270035a82d28e219edce"
RUN2_LEDGER_BYTES = 64871267
RUN2_PARSE_ISSUE_RELATIVE_PATH = "data/verification/enumeration/parse_issues_run2.jsonl"
RUN2_PARSE_ISSUE_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

RUN3_SUFFIX = "data/verification/enumeration/raw_candidate_ledger_run3.jsonl"
RUN3_SHA256 = "1b126257e5a0e7c25a633d4b14d9eea5739378692ad1a777b48776231f32e37d"
RUN3_COMMIT = "e077014e3c74e691b362b25a4e58ddf3303e9006"
RUN3_SCHEMA_VERSION = "fvq2-raw-v1"
RUN3_COUNT = 14118
RUN3_FREEZE_PATH = Path(__file__).resolve().parents[2] / "data" / "verification" / "enumeration" / "THIRD_RUN_FREEZE.json"
RUN3_FREEZE_SHA256 = "f7fd2e4b79507a763a47eee496e58f2e0c0477d46b40cda3eec54420685e564b"
RUN3_LEDGER_BYTES = 64857149
RUN3_PARSE_ISSUE_RELATIVE_PATH = "data/verification/enumeration/parse_issues_run3.jsonl"
RUN3_PARSE_ISSUE_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
RUN3_CANDIDATE_ID_PREFIX = "fvq2_"


def expansion_required(unique_natural_eligible: int, controlled_parent_eligible: int) -> bool:
    return unique_natural_eligible < 60 or controlled_parent_eligible < 15


def _is_run2(path: Path) -> bool:
    return path.as_posix().lower().endswith(RUN2_SUFFIX)


def _is_run3(path: Path) -> bool:
    return path.as_posix().lower().endswith(RUN3_SUFFIX)


def _validate_raw(record: Mapping[str, Any]) -> Dict[str, Any]:
    required = {"candidate_id", "source_id", "source_sha256", "relative_path", "source_format", "source_locator", "raw_source_span", "target_raw_text", "target_start", "target_end", "numeric_kind", "normalized_value", "normalized_unit", "scale", "parser_metadata", "enumeration_status"}
    if set(record) < required:
        raise ValueError("raw candidate schema is incomplete")
    copied = dict(record)
    if not isinstance(copied["candidate_id"], str) or not isinstance(copied["target_start"], int) or not isinstance(copied["target_end"], int):
        raise ValueError("raw candidate types are invalid")
    if copied["target_start"] < 0 or copied["target_end"] < copied["target_start"]:
        raise ValueError("raw candidate offsets are invalid")
    if copied["raw_source_span"][copied["target_start"]:copied["target_end"]] != copied["target_raw_text"]:
        raise ValueError("raw target offset invariant failed")
    return copied


def load_raw_ledger(path: Path, *, allow_production: bool = False, expected_sha256: Optional[str] = None, freeze_metadata_path: Optional[Path] = None, implementation_commit: Optional[str] = None) -> List[Dict[str, Any]]:
    path = Path(path)
    if _is_run2(path):
        raise PermissionError("Run-2 is permanently retired for production/scientific use; Run-3 is the sole production ledger")
    if _is_run3(path) and not allow_production:
        raise PermissionError("production Run-3 eligibility is blocked by default")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("raw ledger SHA-256 mismatch")
    if _is_run3(path) and digest != RUN3_SHA256:
        raise ValueError("authorized path is not the frozen Run-3 ledger")
    if _is_run3(path) and allow_production:
        if implementation_commit is None or implementation_commit == "UNRECORDED" or not re.fullmatch(r"[0-9a-f]{40}", implementation_commit):
            raise PermissionError("authorized Run-3 eligibility requires a valid implementation commit")
        if freeze_metadata_path is None or Path(freeze_metadata_path).resolve() != RUN3_FREEZE_PATH.resolve():
            raise PermissionError("authorized Run-3 eligibility requires the canonical THIRD_RUN_FREEZE.json")
        freeze_bytes = Path(freeze_metadata_path).read_bytes()
        if hashlib.sha256(freeze_bytes).hexdigest() != RUN3_FREEZE_SHA256:
            raise ValueError("THIRD_RUN_FREEZE.json SHA-256 mismatch")
        freeze = json.loads(freeze_bytes.decode("utf-8"))
        raw_meta = freeze.get("raw_candidate_ledger", {}); parse_meta = freeze.get("parse_issue_ledger", {})
        provenance = freeze.get("source_corpus_provenance", {}); historical = freeze.get("historical_provenance_policy", {})
        repair = freeze.get("repair_scope", {})
        if (freeze.get("phase") != "9C-R3" or freeze.get("enumerator_commit") != RUN3_COMMIT
                or freeze.get("enumeration_schema_version") != RUN3_SCHEMA_VERSION
                or freeze.get("candidate_count") != RUN3_COUNT or freeze.get("unique_candidate_id_count") != RUN3_COUNT
                or raw_meta.get("relative_path") != RUN3_SUFFIX or raw_meta.get("byte_size") != RUN3_LEDGER_BYTES
                or raw_meta.get("sha256") != RUN3_SHA256 or parse_meta.get("relative_path") != RUN3_PARSE_ISSUE_RELATIVE_PATH
                or parse_meta.get("byte_size") != 0 or parse_meta.get("sha256") != RUN3_PARSE_ISSUE_SHA256
                or freeze.get("supersedes_for_scientific_use") != "SECOND_RUN_FREEZE.json"
                or historical.get("run2_remains_immutable_historical_provenance") is not True
                or historical.get("run2_is_never_a_scientific_fallback") is not True
                or provenance.get("source_corpus_unchanged_from_run2") is not True
                or repair.get("candidate_identity_changed") is not True or repair.get("segment_index_added_to_identity") is not True
                or repair.get("source_corpus_changed") is not False or repair.get("parsing_changed") is not False
                or repair.get("segmentation_changed") is not False or repair.get("eligibility_policy_changed") is not False
                or repair.get("production_annotation_had_started") is not False
                or repair.get("annotation_outcomes_created_before_repair") is not False):
            raise ValueError("Run-3 freeze metadata mismatch")
    records=[]; seen=set()
    for line in data.splitlines():
        record=_validate_raw(json.loads(line.decode("utf-8")))
        if record["candidate_id"] in seen: raise ValueError("duplicate candidate_id")
        seen.add(record["candidate_id"]); records.append(record)
    if _is_run3(path):
        if len(records) != RUN3_COUNT: raise ValueError("Run-3 candidate count mismatch")
        if not all(r["candidate_id"].startswith(RUN3_CANDIDATE_ID_PREFIX) for r in records):
            raise ValueError("Run-3 candidate IDs must use the fvq2_ identity scheme")
    return records


def _reviewed_record(raw: Dict[str, Any], review: ReviewDecision) -> Dict[str, Any]:
    identity = normalize_identity(review.identity)
    normalized = {key + "_normalized": value for key, value in identity.items()}
    normalized["normalized_value_key"] = normalized_value_key(raw["normalized_value"], raw["normalized_unit"], raw["scale"])
    output = dict(raw)
    output.update(normalized)
    output.update({
        "eligibility_status": review.eligibility_status,
        "primary_exclusion_code": review.primary_exclusion_code,
        "secondary_exclusion_codes": list(review.secondary_exclusion_codes),
        "ambiguity_status": review.ambiguity_status,
        "review_workflow_status": review.review_workflow_status,
        "review_method": review.review_method,
        "reviewer_id": review.reviewer_id,
        "review_timestamp": review.review_timestamp,
        "adjudication_id": review.adjudication_id,
        "entity": review.identity.get("entity"), "concept": review.identity.get("concept"),
        "period": review.identity.get("period"), "scope": review.identity.get("scope"),
        "accounting_basis": review.identity.get("accounting_basis"),
        "temporal_frame": review.identity.get("temporal_frame"), "value_role": review.identity.get("value_role"),
        "evidence": dict(review.evidence),
        "challengeable_dimensions": sorted(review.challengeable_dimensions),
        "natural_eligible": review.eligibility_status == "ELIGIBLE",
        "controlled_parent_eligible": False,
    })
    return output


def build_eligibility(raw_records: Iterable[Mapping[str, Any]], reviews: Iterable[Mapping[str, Any] | ReviewDecision], source_descriptors: Iterable[SourceDescriptor]) -> Dict[str, Any]:
    raw = [_validate_raw(record) for record in raw_records]
    ids = {record["candidate_id"] for record in raw}
    decisions = [item if isinstance(item, ReviewDecision) else review_from_dict(dict(item)) for item in reviews]
    review_map = validate_review_set(decisions, ids)
    descriptors = list(source_descriptors)
    group_map = __import__("verification.eligibility.source_groups", fromlist=["build_source_groups"]).build_source_groups(descriptors)
    records = [_reviewed_record(record, review_map[record["candidate_id"]]) for record in raw]
    eligible = [record for record in records if record["eligibility_status"] == "ELIGIBLE"]
    keyed: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
    for record in eligible:
        key = identity_key(record, review_map[record["candidate_id"]])
        if key is not None:
            keyed.setdefault(key, []).append(record)
        else:
            # Missing/unknown identity can never merge with another occurrence;
            # retain it as its own auditable singleton fact cluster.
            record["fact_cluster_id"] = fact_cluster_id(("singleton", record["candidate_id"]))
            record["canonical_occurrence"] = True
    for key, cluster in keyed.items():
        cluster_id = fact_cluster_id(key)
        ordered = sorted(cluster, key=lambda item: canonical_sort_key(item, review_map[item["candidate_id"]]))
        for index, record in enumerate(ordered):
            record["fact_cluster_id"] = cluster_id
            record["canonical_occurrence"] = index == 0
    for record in records:
        record.setdefault("fact_cluster_id", None)
        record.setdefault("canonical_occurrence", False)
        record["source_group_id"] = group_map.get(record["source_id"])
        if record["canonical_occurrence"] and record["natural_eligible"]:
            review = review_map[record["candidate_id"]]
            dimensions = set(review.challengeable_dimensions)
            if not dimensions.issubset(CHALLENGEABLE_DIMENSIONS):
                raise ValueError("unknown challengeable dimension")
            normalized_identity = normalize_identity(review.identity)
            recoverable = {name for name in CHALLENGEABLE_DIMENSIONS if determinate(normalized_identity.get(name))}
            if dimensions != recoverable:
                raise ValueError("challengeable_dimensions must equal explicitly recoverable dimensions")
            meaningful = set(review.meaningful_challenge_dimensions)
            if not meaningful.issubset(dimensions):
                raise ValueError("meaningful challenge dimension is not recoverable")
            required = all(determinate(normalized_identity.get(name)) for name in ("entity", "concept", "period"))
            record["controlled_parent_eligible"] = required and bool(meaningful)
    ordered_records = sorted(records, key=lambda item: (item["source_id"], item["source_locator"], item["target_start"], item["target_end"], item["target_raw_text"], item["candidate_id"]))
    natural_pool = [record for record in ordered_records if record["natural_eligible"] and record["canonical_occurrence"]]
    parent_pool = [record for record in natural_pool if record["controlled_parent_eligible"]]
    summary = {
        "raw_occurrences": len(records),
        "unique_natural_eligible": len(natural_pool),
        "controlled_parent_eligible": len(parent_pool),
        "corpus_expansion_required": expansion_required(len(natural_pool), len(parent_pool)),
    }
    return {"eligibility_ledger": ordered_records, "eligible_natural_pool": natural_pool, "controlled_parent_pool": parent_pool, "summary": summary, "source_group_map": group_map}
