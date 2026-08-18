"""Phase 3D regression tests: universal numeric / unit verification.

These prove the verification engine does not conflate numeric quantities
that merely share a bare digit sequence but differ in scale, unit, or
metric identity -- monetary scale (billion vs million), percentage vs bare
number, basis points vs percentage, EPS vs revenue, shares vs currency, and
so on.

Two layers are exercised:
  1. numeric.canonicalizer / app.parser -- the token-level distinctions
     (a candidate token's own unit/scale can never be silently reinterpreted
     as a different one).
  2. core.engine.verify() end-to-end -- metric-identity matching
     (core.identity_verification.primary_evidence_matches) already ensures
     a claim can only be compared against evidence tagged with the SAME
     canonical concept, which is what actually prevents EPS-vs-revenue and
     shares-vs-currency conflation; these tests confirm that holds.
"""

from __future__ import annotations

import pytest

from app.parser import resolve_context_scale
from core.engine import verify
from core.financial.document import FinancialPeriod
from core.models import Claim, Entity, Evidence, Metric, Source, VerificationContext, VerificationStatus
from numeric.canonicalizer import CanonicalizationError, Unit, canonicalize


class _FakeRetriever:
    def __init__(self, items: list[Evidence]):
        self._items = items

    def retrieve(self, claim: Claim, context: VerificationContext | None = None) -> list[Evidence]:
        if context is not None:
            context.evidence_mode = "retrieved"
        return self._items


def _primary_evidence(value: float, *, locator: str, period: str = "FY2025") -> Evidence:
    return Evidence(
        source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0),
        claim="q",
        value=value,
        locator=locator,
        period=period,
    )


def _claim(raw_value: float, *, metric: str, fiscal_year: int = 2025) -> Claim:
    return Claim(
        question=f"What was {metric} for ACME?",
        raw_value=raw_value,
        metric=Metric(name=metric, canonical_name=metric),
        entity=Entity(name="ACME", ticker="ACME"),
        period_struct=FinancialPeriod(kind="annual", fiscal_year=fiscal_year),
    )


# ---------------------------------------------------------------------------
# 1. Monetary scale mismatch: $109.42B must never equal $109.42M
# ---------------------------------------------------------------------------

def test_billion_and_million_canonicalize_to_different_magnitudes():
    billions = canonicalize("$109.42 billion")
    millions = canonicalize("$109.42 million")
    assert billions.value != millions.value
    assert billions.value == millions.value * 1000


def test_billion_claim_does_not_verify_against_million_evidence(monkeypatch=None):
    result_b = verify(
        _claim(109.42e9, metric="Revenue"),
        evidence_retriever=_FakeRetriever([_primary_evidence(109.42e6, locator="Revenue")]),
    )
    assert result_b.trust_score.status is not VerificationStatus.VERIFIED


# ---------------------------------------------------------------------------
# 2. Percentage vs bare number: "12.5%" must never equal 12.5
# ---------------------------------------------------------------------------

def test_percent_token_carries_percent_unit_not_bare_number():
    percent = canonicalize("12.5%")
    bare = canonicalize("12.5")
    assert percent.unit is Unit.PERCENT
    assert bare.unit is Unit.NONE
    # Same numeric magnitude, but semantically distinct units -- callers
    # must consult .unit, never assume equality from .value alone.
    assert percent.value == bare.value
    assert percent.unit != bare.unit


# ---------------------------------------------------------------------------
# 3. Basis points vs percentage: "125 bps" must never equal "125%"
# ---------------------------------------------------------------------------

def test_bps_and_percent_are_distinct_units():
    bps = canonicalize("125 bps")
    percent = canonicalize("125%")
    assert bps.unit is Unit.BASIS_POINT
    assert percent.unit is Unit.PERCENT
    assert bps.unit != percent.unit


def test_bps_word_form_also_recognized():
    bps = canonicalize("125 basis points")
    assert bps.unit is Unit.BASIS_POINT
    assert bps.value == canonicalize("125 bps").value


# ---------------------------------------------------------------------------
# 4. EPS vs revenue/currency: metric-identity matching (not numeric parsing)
#    is what prevents these from ever being compared to each other.
# ---------------------------------------------------------------------------

def test_eps_claim_only_matches_eps_evidence_not_revenue():
    evidence = [
        _primary_evidence(6.12, locator="Revenue"),  # wrong concept entirely
    ]
    result = verify(
        _claim(6.12, metric="EarningsPerShareBasic"),
        evidence_retriever=_FakeRetriever(evidence),
    )
    # No compatible (EPS-tagged) evidence exists, so this must not become
    # VERIFIED purely because a numerically identical value exists under a
    # different metric.
    assert result.trust_score.status is not VerificationStatus.VERIFIED


def test_eps_claim_verifies_only_against_eps_tagged_evidence():
    evidence = [_primary_evidence(6.12, locator="EarningsPerShareBasic")]
    result = verify(
        _claim(6.12, metric="EarningsPerShareBasic"),
        evidence_retriever=_FakeRetriever(evidence),
    )
    assert result.trust_score.status is VerificationStatus.VERIFIED


# ---------------------------------------------------------------------------
# 5. Shares vs currency: metric-identity matching again, not numeric parsing.
# ---------------------------------------------------------------------------

def test_shares_claim_does_not_match_revenue_evidence_of_same_magnitude():
    evidence = [_primary_evidence(1_200_000_000, locator="Revenue")]
    result = verify(
        _claim(1_200_000_000, metric="SharesOutstanding"),
        evidence_retriever=_FakeRetriever(evidence),
    )
    assert result.trust_score.status is not VerificationStatus.VERIFIED


def test_shares_claim_verifies_against_shares_tagged_evidence():
    evidence = [_primary_evidence(1_200_000_000, locator="SharesOutstanding")]
    result = verify(
        _claim(1_200_000_000, metric="SharesOutstanding"),
        evidence_retriever=_FakeRetriever(evidence),
    )
    assert result.trust_score.status is VerificationStatus.VERIFIED


# ---------------------------------------------------------------------------
# 6 & 7. billion vs million, million vs thousand -- scale-word table itself.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "smaller_word,larger_word,ratio",
    [
        ("million", "billion", 1000),
        ("thousand", "million", 1000),
        ("thousand", "billion", 1_000_000),
    ],
)
def test_scale_word_ratios_are_exact(smaller_word, larger_word, ratio):
    smaller = canonicalize(f"2.5 {smaller_word}")
    larger = canonicalize(f"2.5 {larger_word}")
    assert larger.value == smaller.value * ratio


# ---------------------------------------------------------------------------
# 8. Correct equivalent representations
# ---------------------------------------------------------------------------

def test_equivalent_scale_representations_agree():
    assert canonicalize("$2.4 billion").value == canonicalize("$2,400 million").value
    assert canonicalize("2400 million").value == canonicalize("2.4 billion").value


def test_equivalent_currency_symbol_and_code_agree_in_value():
    assert canonicalize("$109.42").value == canonicalize("109.42 USD").value


# ---------------------------------------------------------------------------
# 9. Ambiguous units -> fail closed (CanonicalizationError / UNVERIFIED)
# ---------------------------------------------------------------------------

def test_ambiguous_scale_unit_combination_rejected():
    with pytest.raises(CanonicalizationError):
        canonicalize("12.4% billion")


def test_ambiguous_context_scale_leaves_claim_unresolved():
    assert resolve_context_scale(
        109.42, "Revenue was $109.42 billion; another estimate was $109.42 million."
    ) is None


# ---------------------------------------------------------------------------
# 10. Ambiguous scale (legacy ratio 1-100 window) -> UNVERIFIED, not guessed
# ---------------------------------------------------------------------------

def test_no_independent_evidence_with_ambiguous_ratio_stays_unverified_via_public_api():
    """core.engine.verify() called directly can still resolve a MODEL-tier,
    no-independent-evidence claim to VERIFIED when internal correction
    rules find self-consistency (see tests/test_trust_engine.py -- this is
    the offline-evaluation path and is intentionally left unchanged).
    The public /v1/verify API, however, must never expose that as VERIFIED
    when there is no independent evidence -- that is what the Phase 3E
    gate in app.main enforces."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/v1/verify",
        json={"question": "What was the margin change?", "raw_value": 42.0},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "unverified"
    assert payload["trust_score"] == "N/A"
    assert payload["confidence"] is None
