"""PHASE 3A regression tests.

These tests prove that the live verification entry point,
`core.engine.verify()`, can no longer reach VERIFIED from independent
(PRIMARY/SECONDARY tier) evidence purely on evidence tier -- it must now
prove the claimed value against the retrieved evidence using the EXISTING
identity/value comparison machinery in `core.identity_verification` (the
same machinery already relied on by the offline
`scripts/verify_transcript.py` path).

No live SEC/network calls: independent evidence is supplied via a fake
evidence_retriever, exactly like the existing `EvidenceRetriever()` pattern
used throughout tests/test_batch_verify.py and tests/test_document_verifier.py.
"""

from __future__ import annotations

import pytest

from core.engine import verify
from core.financial.document import FinancialPeriod
from core.models import (
    Claim,
    Entity,
    Evidence,
    Metric,
    Source,
    VerificationContext,
    VerificationStatus,
)
from core.trust_engine import compute_trust
from core.models import MathResult


class _FakePrimaryRetriever:
    """Minimal evidence_retriever stand-in: returns fixed primary-filing
    Evidence without touching the network or ingestion.db, mirroring how
    SECProvider.retrieve() shapes real evidence."""

    def __init__(self, items: list[Evidence]):
        self._items = items

    def retrieve(self, claim: Claim, context: VerificationContext | None = None) -> list[Evidence]:
        if context is not None:
            context.evidence_mode = "retrieved"
        return self._items


def _primary_evidence(value: float, *, locator: str = "Revenue", period: str = "FY2025") -> Evidence:
    return Evidence(
        source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0),
        claim="q",
        value=value,
        locator=locator,
        period=period,
    )


def _claim(
    raw_value: float,
    *,
    metric: str = "Revenue",
    fiscal_year: int = 2025,
) -> Claim:
    return Claim(
        question=f"What was {metric} for ACME?",
        raw_value=raw_value,
        metric=Metric(name=metric, canonical_name=metric),
        entity=Entity(name="ACME", ticker="ACME"),
        period_struct=FinancialPeriod(kind="annual", fiscal_year=fiscal_year),
    )


# ---------------------------------------------------------------------------
# The key regression test: same entity/metric/period/evidence source,
# two claims that differ only in value.
# ---------------------------------------------------------------------------


def test_matching_claim_value_is_verified():
    result = verify(_claim(100.0), evidence_retriever=_FakePrimaryRetriever([_primary_evidence(100.0)]))
    assert result.trust_score.status is VerificationStatus.VERIFIED
    assert result.trust_score.label == "HIGH"


def test_contradicting_claim_value_is_contradicted_not_verified():
    result = verify(_claim(75.0), evidence_retriever=_FakePrimaryRetriever([_primary_evidence(100.0)]))
    assert result.trust_score.status is VerificationStatus.CONTRADICTED
    assert result.trust_score.status is not VerificationStatus.VERIFIED


def test_same_evidence_diverging_claims_never_both_verified():
    """The most important Phase 3A regression test: Claim A (100) and Claim
    B (75), same entity/metric/period/evidence source, must NOT both come
    back VERIFIED."""
    evidence = [_primary_evidence(100.0)]
    result_a = verify(_claim(100.0), evidence_retriever=_FakePrimaryRetriever(evidence))
    result_b = verify(_claim(75.0), evidence_retriever=_FakePrimaryRetriever(evidence))

    assert result_a.trust_score.status is VerificationStatus.VERIFIED
    assert result_b.trust_score.status is VerificationStatus.CONTRADICTED
    assert not (
        result_a.trust_score.status is VerificationStatus.VERIFIED
        and result_b.trust_score.status is VerificationStatus.VERIFIED
    )


# ---------------------------------------------------------------------------
# Additional required cases
# ---------------------------------------------------------------------------


def test_no_evidence_is_unverified():
    result = verify(Claim(question="What was Revenue?", raw_value=100.0), evidence_retriever=_FakePrimaryRetriever([]))
    assert result.trust_score.status is VerificationStatus.UNVERIFIED
    assert result.trust_score.label == "N/A"


def test_wrong_period_evidence_does_not_verify():
    result = verify(
        _claim(100.0, fiscal_year=2024),
        evidence_retriever=_FakePrimaryRetriever([_primary_evidence(100.0, period="FY2025")]),
    )
    assert result.trust_score.status is not VerificationStatus.VERIFIED
    assert result.trust_score.status is VerificationStatus.UNVERIFIED


def test_wrong_metric_evidence_does_not_verify():
    result = verify(
        _claim(100.0, metric="NetIncome"),
        evidence_retriever=_FakePrimaryRetriever([_primary_evidence(100.0, locator="Revenue")]),
    )
    assert result.trust_score.status is not VerificationStatus.VERIFIED
    assert result.trust_score.status is VerificationStatus.UNVERIFIED


def test_primary_evidence_with_wrong_value_is_not_verified():
    """This is the exact vulnerability the audit identified: PRIMARY/HIGH
    quality evidence existing must not, by itself, be sufficient for
    VERIFIED when the numeric comparison fails."""
    result = verify(_claim(75.0), evidence_retriever=_FakePrimaryRetriever([_primary_evidence(100.0)]))
    assert result.trust_score.status is not VerificationStatus.VERIFIED


def test_primary_evidence_with_correct_value_is_verified():
    result = verify(_claim(100.0), evidence_retriever=_FakePrimaryRetriever([_primary_evidence(100.0)]))
    assert result.trust_score.status is VerificationStatus.VERIFIED


# ---------------------------------------------------------------------------
# Preserve Phase 0-2: no independent evidence remains UNVERIFIED / N/A / null
# ---------------------------------------------------------------------------


def test_generic_extension_claim_without_evidence_remains_unverified():
    result = verify(
        Claim(question="What was the financial value?", raw_value=101.0, model_source="chatgpt.com"),
        evidence_retriever=_FakePrimaryRetriever([]),
    )
    assert result.trust_score.status is VerificationStatus.UNVERIFIED
    assert result.trust_score.label == "N/A"
    assert result.trust_score.score is None


# ---------------------------------------------------------------------------
# Backward compatibility: callers that never pass `value_comparison` to
# compute_trust() directly (e.g. core.financial.reasoning.ReasoningEngine)
# keep their exact pre-Phase-3A behavior. This is what makes the Phase 3A
# gate additive rather than a change to trust_engine's default semantics.
# ---------------------------------------------------------------------------


def test_compute_trust_without_value_comparison_argument_is_unchanged():
    claim = Claim(question="What is Revenue for this filing?", raw_value=100.0)
    context = VerificationContext(
        claim=claim,
        provider="sec_edgar",
        provider_metadata={"tier": "primary"},
        evidence_mode="retrieved",
        current_value=100.0,
    )
    trust = compute_trust(context, MathResult(verified_value=100.0), [])
    assert trust.status is VerificationStatus.VERIFIED
    assert trust.label == "HIGH"
