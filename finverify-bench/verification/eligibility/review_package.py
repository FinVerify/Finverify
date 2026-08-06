"""Amendment 2 Section 11 / Implementation Spec Section 7 & 8A.5: blinded export/import.

Human audit reviewers must be blind, at the time of initial judgment, to:
LLM model identity, individual votes, the aggregated llm_annotation value,
agreement_tier/stratum, any LLM rationale, and any FinVerify/DVL/Trust
Engine output. Case order is randomized independent of stratum. This module
builds the blinded package reviewers actually see, plus a private mapping
(kept out of the reviewer-facing artifact) used only to restore identity
when responses are imported.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence

# Section 7 evidence-package fields only — no LLM/aggregation fields, no
# FinVerify/model output fields are permitted here by construction.
EVIDENCE_ALLOWED_FIELDS = (
    "evidence_type", "evidence_text", "target_raw_text", "target_start", "target_end",
    "source_id", "source_sha256", "source_format", "source_locator", "parser_metadata",
    "applicable_heading", "issuer", "reporting_event", "structural_context", "dependency_log",
)


def _row_order_hex(shuffle_seed_hex: str, row_id: str) -> str:
    return hashlib.sha256(("finverify-phase9c-audit-order-v1\n" + shuffle_seed_hex + "\n" + row_id).encode("utf-8")).hexdigest()


def _row_id(candidate_id: str) -> str:
    # Reviewer-facing identifier is not the candidate_id itself, so a
    # reviewer cannot correlate row order/labels back to ledger position.
    return "audit_item_" + hashlib.sha256(("finverify-phase9c-audit-row-v1\n" + candidate_id).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class BlindedRow:
    row_id: str
    evidence: Dict[str, Any]


def export_blinded_audit(
    candidates: Sequence[Mapping[str, Any]],
    *,
    shuffle_seed_hex: str,
) -> tuple[List[BlindedRow], Dict[str, str]]:
    """Build the blinded reviewer package and the private candidate_id mapping.

    ``candidates`` items must already be restricted to raw ledger fields plus
    the Section 7 evidence object — callers are responsible for not passing
    any llm_annotation/agreement_tier/vote/model field in; this function
    additionally defensively strips any key outside ``EVIDENCE_ALLOWED_FIELDS``.
    """
    mapping: Dict[str, str] = {}
    rows: List[BlindedRow] = []
    for item in candidates:
        candidate_id = item["candidate_id"]
        row_id = _row_id(candidate_id)
        if row_id in mapping.values():
            raise ValueError("row_id collision for candidate_id %r" % candidate_id)
        mapping[row_id] = candidate_id
        evidence = {k: v for k, v in item.items() if k in EVIDENCE_ALLOWED_FIELDS}
        rows.append(BlindedRow(row_id=row_id, evidence=evidence))

    # Case presentation order randomized independent of stratum: order by a
    # deterministic hash of (shuffle seed, row_id), never by stratum/rank.
    rows = sorted(rows, key=lambda r: _row_order_hex(shuffle_seed_hex, r.row_id))
    return rows, mapping


def assert_no_leaked_fields(rows: Sequence[BlindedRow]) -> None:
    """Defense-in-depth check usable in tests: no disallowed field leaked through."""
    forbidden_markers = (
        "llm_annotation", "agreement_tier", "vote", "model_family", "model_version",
        "audit_stratum", "stratum", "rationale", "finverify", "dvl", "trust_engine",
    )
    for row in rows:
        for key in row.evidence:
            if key not in EVIDENCE_ALLOWED_FIELDS:
                raise AssertionError("blinded row leaked disallowed field: %r" % key)
        blob = str(row.evidence).lower()
        for marker in forbidden_markers:
            if marker in blob:
                raise AssertionError("blinded row evidence text contains forbidden marker: %r" % marker)


@dataclass(frozen=True)
class ReviewerResponse:
    row_id: str
    reviewer_id: str
    verdict: str  # ELIGIBLE | EXCLUDED | ADJUDICATION_REQUIRED
    primary_exclusion_code: str | None = None
    secondary_exclusion_codes: tuple[str, ...] = ()


def import_responses(
    responses: Sequence[ReviewerResponse],
    mapping: Mapping[str, str],
) -> Dict[str, ReviewerResponse]:
    """Restore candidate_id identity for reviewer responses; validates row IDs.

    Returns ``candidate_id -> ReviewerResponse``. Raises if a response
    references an unknown row_id or if the same row_id is answered twice by
    the same reviewer_id (duplicate submission), which would otherwise
    silently overwrite a prior judgment.
    """
    seen: set[tuple[str, str]] = set()
    result: Dict[str, ReviewerResponse] = {}
    for response in responses:
        if response.row_id not in mapping:
            raise ValueError("response references unknown row_id: %r" % response.row_id)
        key = (response.row_id, response.reviewer_id)
        if key in seen:
            raise ValueError("duplicate response for row_id/reviewer_id: %r" % (key,))
        seen.add(key)
        candidate_id = mapping[response.row_id]
        result[candidate_id] = response
    return result
