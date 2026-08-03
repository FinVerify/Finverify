"""Orchestrate document-level verification: extract, adapt, delegate.

`verify_document()` is intentionally a thin wiring layer only. It does not
verify anything itself, does not evaluate constraints, does not compute
trust, and does not normalize concept names -- all of that already happens
inside `verify_batch()` / `verify()`. Its only jobs are:

    FinancialDocument -> extract_claims() -> Claim -> BatchClaim -> verify_batch()

See `_claim_to_batch_claim()` for the one piece of real logic here: adapting
`Claim` (which has `entity: Entity`, `metric: Metric`, `metadata: dict`) into
`BatchClaim` (which has `entity: str`, optional `ticker` / `cik`, `metric: str`,
and no `metadata` field at all).
"""

from __future__ import annotations

import logging
from typing import Optional

from core.engine import verify_batch
from core.evidence import EvidenceRetriever
from core.models import BatchClaim, BatchVerifyRequest, BatchVerifyResponse, Claim

from .claim_extractor import extract_claims
from .document import FinancialDocument

logger = logging.getLogger(__name__)


def verify_document(
    document: FinancialDocument,
    *,
    include_constraints: bool = True,
    tolerance: Optional[float] = 1e-6,
    evidence_retriever: Optional[EvidenceRetriever] = None,
) -> BatchVerifyResponse:
    """Extract claims from `document` and verify them in one batch.

    Parameters mirror `BatchVerifyRequest` / `verify_batch()` directly rather
    than inventing new ones: `include_constraints` and `tolerance` are passed
    straight through to `BatchVerifyRequest`, and `evidence_retriever` is
    passed straight through to `verify_batch()` (e.g. for tests that want to
    stub evidence lookups, matching the existing pattern in
    `tests/test_batch_verify.py`).
    """
    claims = extract_claims(document)
    batch_claims, skipped = _adapt_claims(claims)

    if skipped:
        logger.warning(
            "verify_document: skipped %d/%d claim(s) with no raw_value for %s",
            skipped,
            len(claims),
            document.company_name,
        )

    request = BatchVerifyRequest(
        claims=batch_claims,
        include_constraints=include_constraints,
        tolerance=tolerance,
    )
    return verify_batch(request, evidence_retriever=evidence_retriever)


def _adapt_claims(claims: list[Claim]) -> tuple[list[BatchClaim], int]:
    batch_claims: list[BatchClaim] = []
    skipped = 0
    for claim in claims:
        batch_claim = _claim_to_batch_claim(claim)
        if batch_claim is None:
            skipped += 1
            continue
        batch_claims.append(batch_claim)
    return batch_claims, skipped


def _claim_to_batch_claim(claim: Claim) -> BatchClaim | None:
    """Adapt a single Claim into a BatchClaim.

    `BatchClaim.raw_value` is a required `float` (unlike `Claim.raw_value`,
    which is optional) -- claims with no raw_value cannot be represented as a
    BatchClaim and are dropped (see `verify_document`'s skipped-count log).

    `BatchClaim.metric` / `.entity` are plain strings, so `Claim.metric`
    (a `Metric` object) and `Claim.entity` (an `Entity` object) are flattened
    to their name. Entity provenance needed for SEC routing (`ticker` / `cik`)
    is preserved in the dedicated optional `BatchClaim` fields.

    `Claim.metadata` -- source, statement, filing_type, filing_date, xbrl_tag,
    source_url -- has nowhere to go on `BatchClaim` (it has no `metadata`
    field) and is intentionally dropped here, per the compatibility audit's
    finding. It is not recoverable from the `BatchVerifyResponse`; callers
    that need that context must keep a reference to the `Claim` objects
    returned by `extract_claims()` alongside this adapter's output.
    """
    if claim.raw_value is None:
        return None

    metric_name = None
    if claim.metric is not None:
        metric_name = claim.metric.canonical_name or claim.metric.name

    entity_name = claim.entity.name if claim.entity is not None else None

    return BatchClaim(
        question=claim.question,
        raw_value=claim.raw_value,
        metric=metric_name,
        entity=entity_name,
        ticker=claim.entity.ticker if claim.entity is not None else None,
        cik=claim.entity.cik if claim.entity is not None else None,
        period=claim.period,
        actual_value=claim.actual_value,
    )
