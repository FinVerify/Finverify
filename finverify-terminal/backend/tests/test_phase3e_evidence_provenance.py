"""Phase 3E regression tests: evidence quality + provenance hardening.

Covers:
  - primary evidence with valid provenance can VERIFY
  - missing independent evidence cannot VERIFY
  - MODEL-tier evidence cannot become VERIFIED through the public API
    (/v1/verify and /v1/verify/batch), even though core.trust_engine
    itself can still resolve MODEL-tier + actual_value to VERIFIED for the
    offline-evaluation harness (tests/test_trust_engine.py) -- the fix is
    an API-boundary gate (app.main._gate_independent_evidence /
    _gate_verification_result), not a change to trust_engine.compute_trust().
  - /v1/verify and /v1/verify/batch have identical no-independent-evidence
    semantics.
  - evidence provenance (source, url, retrieved_at, authority, locator,
    period, entity) survives into the verification result.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app, _gate_independent_evidence, _gate_verification_result
from core.engine import verify, verify_batch
from core.evidence import EvidenceRetriever
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

client = TestClient(app)


class _FakeRetriever:
    def __init__(self, items: list[Evidence]):
        self._items = items

    def retrieve(self, claim: Claim, context: VerificationContext | None = None) -> list[Evidence]:
        if context is not None:
            context.evidence_mode = "retrieved"
        return self._items


def _primary_evidence(
    value: float,
    *,
    locator: str = "Revenue",
    period: str = "FY2025",
    url: str | None = "https://www.sec.gov/example",
    entity: str | None = "ACME",
) -> Evidence:
    return Evidence(
        source=Source(
            name="SEC EDGAR",
            kind="primary_filing",
            authority=1.0,
            url=url,
            retrieved_at="2026-08-16T00:00:00+00:00",
        ),
        claim="What was Revenue for ACME?",
        value=value,
        locator=locator,
        period=period,
        entity=entity,
    )


def _claim(raw_value: float, *, metric: str = "Revenue", fiscal_year: int = 2025) -> Claim:
    return Claim(
        question=f"What was {metric} for ACME?",
        raw_value=raw_value,
        metric=Metric(name=metric, canonical_name=metric),
        entity=Entity(name="ACME", ticker="ACME"),
        period_struct=FinancialPeriod(kind="annual", fiscal_year=fiscal_year),
    )


# ---------------------------------------------------------------------------
# Primary evidence with valid provenance can VERIFY
# ---------------------------------------------------------------------------

def test_primary_evidence_with_valid_provenance_verifies():
    result = verify(
        _claim(100.0),
        evidence_retriever=_FakeRetriever([_primary_evidence(100.0)]),
    )
    assert result.trust_score.status is VerificationStatus.VERIFIED
    assert result.trust_score.label == "HIGH"


# ---------------------------------------------------------------------------
# Missing independent evidence cannot VERIFY through the public API.
#
# core.engine.verify() called directly does not by itself guarantee this --
# see test_gate_downgrades_model_tier_verified_to_unverified below for why
# that is intentional (the offline-eval harness relies on it). The
# API-boundary gate (exercised here via the real /v1/verify endpoint) is
# what enforces the invariant for public callers.
# ---------------------------------------------------------------------------

def test_missing_independent_evidence_cannot_verify():
    response = client.post(
        "/v1/verify",
        json={"question": "What was Revenue for ACME?", "raw_value": 100.0},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "unverified"
    assert payload["trust_score"] == "N/A"
    assert payload["confidence"] is None
    assert payload["evidence_value"] is None
    assert "No independent evidence available" in payload["reasons"]


# ---------------------------------------------------------------------------
# The API-boundary gate itself
# ---------------------------------------------------------------------------

def test_gate_passes_through_primary_evidence_untouched():
    result = verify(
        _claim(100.0),
        evidence_retriever=_FakeRetriever([_primary_evidence(100.0)]),
    )
    gated = _gate_verification_result(result)
    assert gated.trust_score.status is VerificationStatus.VERIFIED
    assert gated is result  # untouched: no copy needed when already gate-compliant


def test_gate_downgrades_model_tier_verified_to_unverified():
    """Directly exercises the exact scenario the gate exists for: a
    MODEL-tier evidence result that core.trust_engine resolved to VERIFIED
    via internal correction-rule self-consistency (actual_value supplied,
    simulating the offline evaluation harness), gated at the API boundary
    down to UNVERIFIED / N/A / no confidence."""
    claim = Claim(
        question="What was the percentage decrease in HTM securities?",
        raw_value=-34.11,
        actual_value=0.34146,
    )
    result = verify(claim)
    # Confirm the precondition: trust_engine itself reports VERIFIED here
    # (this is the documented, intentional offline-eval behavior).
    assert result.trust_score.status is VerificationStatus.VERIFIED

    seeded = result.model_copy(update={"evidence_value": 109.42}) if hasattr(result, "model_copy") else result.copy(update={"evidence_value": 109.42})
    gated = _gate_verification_result(seeded)
    assert gated.trust_score.status is VerificationStatus.UNVERIFIED
    assert gated.trust_score.label == "N/A"
    assert gated.trust_score.score is None
    assert gated.trust_score.reasons == ["No independent evidence available"]
    assert gated.evidence_value is None


def test_gate_helper_treats_user_tier_the_same_as_model_tier():
    from core.models import (
        Ambiguity,
        Consistency,
        CorrectionSeverity,
        EvidenceTier,
        RuleEvidence,
        TrustFindings,
        TrustScore,
    )

    findings = TrustFindings(
        evidence_tier=EvidenceTier.USER,
        correction_severity=CorrectionSeverity.NONE,
        ambiguity=Ambiguity.LOW,
        consistency=Consistency.PASS,
        rule_evidence=RuleEvidence.NONE,
    )
    trust = TrustScore(
        label="HIGH", score=0.9, color="#00ff88",
        status=VerificationStatus.VERIFIED, findings=findings,
    )
    gated = _gate_independent_evidence(trust, [])
    assert gated.status is VerificationStatus.UNVERIFIED
    assert gated.label == "N/A"
    assert gated.score is None


# ---------------------------------------------------------------------------
# MODEL-tier evidence cannot become VERIFIED through the public API
# ---------------------------------------------------------------------------

def test_v1_verify_never_returns_verified_for_model_tier(monkeypatch):
    monkeypatch.setattr(main_module, "verify", lambda claim: verify(claim))
    response = client.post(
        "/v1/verify",
        json={
            "question": "What was the percentage decrease in HTM securities?",
            "raw_value": -34.11,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "unverified"
    assert payload["trust_score"] == "N/A"
    assert payload["confidence"] is None
    assert payload["evidence_value"] is None
    assert payload["reasons"] == ["No independent evidence available"]


def test_v1_verify_contradiction_surfaces_primary_evidence_value(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "verify",
        lambda claim: verify(
            claim.model_copy(
                update={
                    "metric": Metric(name="Revenue", canonical_name="Revenue"),
                    "entity": Entity(name="ACME", ticker="ACME"),
                    "period_struct": FinancialPeriod(kind="annual", fiscal_year=2025),
                }
            ) if hasattr(claim, "model_copy") else claim.copy(
                update={
                    "metric": Metric(name="Revenue", canonical_name="Revenue"),
                    "entity": Entity(name="ACME", ticker="ACME"),
                    "period_struct": FinancialPeriod(kind="annual", fiscal_year=2025),
                }
            ),
            evidence_retriever=_FakeRetriever([_primary_evidence(109.42)]),
        ),
    )
    response = client.post(
        "/v1/verify",
        json={"question": "What was Revenue for ACME?", "raw_value": 94.04},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "contradicted"
    assert payload["verified_value"] == 94.04
    assert payload["evidence_value"] == 109.42


def test_v1_verify_batch_never_returns_verified_for_model_tier():
    def stubbed_verify_batch(req):
        return verify_batch(req, evidence_retriever=EvidenceRetriever())

    import app.main as m
    m.core_verify_batch = stubbed_verify_batch
    try:
        response = client.post(
            "/v1/verify/batch",
            json={
                "claims": [{"question": "What was Revenue for ACME?", "raw_value": 109.42}],
                "include_constraints": False,
            },
        )
    finally:
        from core.engine import verify_batch as _original_verify_batch
        m.core_verify_batch = _original_verify_batch

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 1
    trust = payload["results"][0]["trust_score"]
    assert trust["status"] == "unverified"
    assert trust["label"] == "N/A"
    assert trust["score"] is None
    assert "No independent evidence available" in trust["reasons"]


# ---------------------------------------------------------------------------
# /v1/verify and /v1/verify/batch have identical no-independent-evidence
# semantics.
# ---------------------------------------------------------------------------

def test_single_and_batch_endpoints_agree_on_no_evidence_semantics():
    single_response = client.post(
        "/v1/verify",
        json={"question": "What was Revenue for ACME?", "raw_value": 109.42},
    )
    batch_response = client.post(
        "/v1/verify/batch",
        json={
            "claims": [{"question": "What was Revenue for ACME?", "raw_value": 109.42}],
            "include_constraints": False,
        },
    )

    single_payload = single_response.json()
    batch_trust = batch_response.json()["results"][0]["trust_score"]

    assert single_payload["verification_status"] == batch_trust["status"]
    assert single_payload["trust_score"] == batch_trust["label"]
    assert single_payload["confidence"] == batch_trust["score"]
    assert single_payload["reasons"] == batch_trust["reasons"]


# ---------------------------------------------------------------------------
# Evidence provenance survives into the verification result.
# ---------------------------------------------------------------------------

def test_evidence_provenance_survives_into_verification_result():
    evidence_item = _primary_evidence(
        100.0,
        locator="Revenue",
        period="FY2025",
        url="https://www.sec.gov/cgi-bin/browse-edgar?example",
        entity="ACME",
    )
    result = verify(_claim(100.0), evidence_retriever=_FakeRetriever([evidence_item]))

    assert len(result.evidence) == 1
    surfaced = result.evidence[0]
    assert surfaced.source.name == "SEC EDGAR"
    assert surfaced.source.kind == "primary_filing"
    assert surfaced.source.authority == 1.0
    assert surfaced.source.url == "https://www.sec.gov/cgi-bin/browse-edgar?example"
    assert surfaced.source.retrieved_at == "2026-08-16T00:00:00+00:00"
    assert surfaced.locator == "Revenue"
    assert surfaced.period == "FY2025"
    assert surfaced.entity == "ACME"
    assert surfaced.value == 100.0


def test_verified_result_is_explainable_from_findings_reasons():
    """A VERIFIED result's trust reasons must name the evidence tier and
    correction/ambiguity/consistency state that produced it -- this is
    the minimum needed to explain *why* a result was VERIFIED without
    inventing provenance that was never retrieved."""
    result = verify(
        _claim(100.0),
        evidence_retriever=_FakeRetriever([_primary_evidence(100.0)]),
    )
    reasons_text = " | ".join(result.trust_score.reasons)
    assert "Evidence tier: primary" in reasons_text
    assert "Corrections:" in reasons_text
    assert "Ambiguity:" in reasons_text
    assert "Consistency:" in reasons_text
