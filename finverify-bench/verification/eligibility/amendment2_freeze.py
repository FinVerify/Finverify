"""Amendment 2 Sections 6, 10, 14 / Implementation Spec Section 8A.3, 8A.7.

Two separate default-deny production gates, neither substituting for the
other:

  Gate 1 (``authorize_annotation_run``): authorizes the LLM-annotation
  production run against the frozen Run-2 ledger.
  Gate 2 (``authorize_audit_release``): authorizes release of the audit
  sampling manifest and the start of human-audit review.

Both default to denied. This module also enforces the required freeze
ordering (annotation-gate timestamp precedes manifest-generation timestamp
precedes audit-release-gate timestamp) and assembles the final freeze
record's Amendment-2 fields.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from .human_audit import cohens_kappa
from .statistics import stratified_fpc_normal_ci

_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


class ProductionGateDenied(PermissionError):
    pass


def _parse_ts(value: str) -> datetime:
    if not _TIMESTAMP_RE.match(value):
        raise ValueError("timestamp must be UTC ISO-8601 with trailing Z: %r" % value)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def authorize_annotation_run(*, allow_annotation_production: bool, implementation_commit: str) -> None:
    """Gate 1: default-deny authorization for running the ensemble against Run-2."""
    if not allow_annotation_production:
        raise ProductionGateDenied("LLM-annotation production run against the frozen Run-2 ledger is blocked by default")
    if not re.fullmatch(r"[0-9a-f]{40}", implementation_commit or ""):
        raise ProductionGateDenied("annotation production run requires a valid 40-hex-char implementation commit")


def authorize_audit_release(*, allow_audit_release: bool, annotation_ledger_frozen: bool, manifest_frozen: bool) -> None:
    """Gate 2: default-deny authorization to release the manifest and begin human audit.

    Independent of Gate 1 — passing Gate 1 never implies Gate 2.
    """
    if not allow_audit_release:
        raise ProductionGateDenied("audit-manifest release / human-audit start is blocked by default")
    if not annotation_ledger_frozen:
        raise ProductionGateDenied("audit release requires the full-corpus LLM annotation ledger to already be frozen")
    if not manifest_frozen:
        raise ProductionGateDenied("audit release requires the audit manifest to already be frozen")


def verify_gate_ordering(*, annotation_gate_ts: str, manifest_ts: str, audit_release_gate_ts: str) -> None:
    """Amendment 2 Section 6: annotation freeze precedes manifest precedes audit-release."""
    a = _parse_ts(annotation_gate_ts)
    m = _parse_ts(manifest_ts)
    r = _parse_ts(audit_release_gate_ts)
    if not (a <= m <= r):
        raise ValueError(
            "freeze timestamps must show annotation preceding manifest preceding audit release: "
            "got annotation=%s manifest=%s audit_release=%s" % (annotation_gate_ts, manifest_ts, audit_release_gate_ts)
        )


@dataclass(frozen=True)
class ArtifactHashes:
    raw_ledger_sha256: str
    annotation_config_sha256: str
    llm_annotation_ledger_sha256: str
    audit_manifest_sha256: str
    human_audit_ledger_sha256: str
    eligibility_ledger_sha256: str
    source_group_manifest_sha256: str
    eligible_natural_pool_sha256: str
    controlled_parent_pool_sha256: str
    eligibility_summary_sha256: str


def build_weighted_statistics(strata: Mapping[str, tuple[int, int, int]]) -> Dict[str, Any]:
    """Amendment 2 Section 14 / Spec 8A.6 weighted estimate, via the frozen CI estimator."""
    return stratified_fpc_normal_ci(strata)


def build_kappa_report(
    per_stratum_pairs: Mapping[str, list[tuple[str, str]]],
    double_coded_pairs: list[tuple[str, str]],
) -> Dict[str, Any]:
    overall_pairs: list[tuple[str, str]] = []
    per_stratum_kappa: Dict[str, Optional[float]] = {}
    for stratum, pairs in per_stratum_pairs.items():
        per_stratum_kappa[stratum] = cohens_kappa(pairs)
        overall_pairs.extend(pairs)
    return {
        "overall_kappa": cohens_kappa(overall_pairs),
        "per_stratum_kappa": per_stratum_kappa,
        "human_human_kappa_double_coded": cohens_kappa(double_coded_pairs),
        "double_coded_n": len(double_coded_pairs),
    }


def build_freeze_record(
    *,
    phase: str,
    artifact_hashes: ArtifactHashes,
    audit_seed_hex_value: str,
    audit_size: int,
    double_coded_count: int,
    weighted_statistics: Mapping[str, Any],
    kappa_report: Mapping[str, Any],
    model_family_disjointness_attestation: bool,
    annotation_gate_ts: str,
    manifest_ts: str,
    audit_release_gate_ts: str,
    implementation_commit: str,
) -> Dict[str, Any]:
    verify_gate_ordering(
        annotation_gate_ts=annotation_gate_ts, manifest_ts=manifest_ts, audit_release_gate_ts=audit_release_gate_ts,
    )
    if double_coded_count != 20:
        raise ValueError("Amendment 2 Section 12 fixes the double-coded subset at exactly 20 cases")
    if not model_family_disjointness_attestation:
        raise ValueError("final freeze requires an affirmative model-family disjointness attestation")
    return {
        "phase": phase,
        "protocol_version": "SOURCE_ELIGIBILITY_v1+AMENDMENT_1+AMENDMENT_2",
        "implementation_commit": implementation_commit,
        "corpus_characterization": (
            "LLM-annotated, with a blinded statistical human audit of a sampled subset; "
            "not a fully human-reviewed corpus"
        ),
        "artifact_hashes": {
            "raw_ledger": artifact_hashes.raw_ledger_sha256,
            "annotation_config": artifact_hashes.annotation_config_sha256,
            "llm_annotation_ledger": artifact_hashes.llm_annotation_ledger_sha256,
            "audit_manifest": artifact_hashes.audit_manifest_sha256,
            "human_audit_ledger": artifact_hashes.human_audit_ledger_sha256,
            "eligibility_ledger": artifact_hashes.eligibility_ledger_sha256,
            "source_group_manifest": artifact_hashes.source_group_manifest_sha256,
            "eligible_natural_pool": artifact_hashes.eligible_natural_pool_sha256,
            "controlled_parent_pool": artifact_hashes.controlled_parent_pool_sha256,
            "eligibility_summary": artifact_hashes.eligibility_summary_sha256,
        },
        "audit_seed_hex": audit_seed_hex_value,
        "audit_size": audit_size,
        "double_coded_count": double_coded_count,
        "weighted_statistics": weighted_statistics,
        "kappa_report": kappa_report,
        "model_family_disjointness_attestation": model_family_disjointness_attestation,
        "gate_timestamps": {
            "annotation_gate": annotation_gate_ts,
            "manifest_generated": manifest_ts,
            "audit_release_gate": audit_release_gate_ts,
        },
    }
