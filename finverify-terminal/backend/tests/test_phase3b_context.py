"""Deterministic Phase 3B context -> resolution -> identity/value tests."""

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from core.engine import verify
from core.models import Claim, Evidence, Source


class StaticEvidence:
    def __init__(self, evidence):
        self.evidence = evidence

    def retrieve(self, claim, context=None):
        return self.evidence


def claim(**overrides):
    values = {
        "question": "What was revenue?",
        "raw_value": 94.04e9,
        "raw_text": "Apple reported revenue of $94.04 billion in Q3 FY2026.",
        "context_text": "Apple reported revenue of $94.04 billion in Q3 FY2026.",
        "entity_hint": "Apple",
        "metric_hint": "Revenue",
        "period_hint": "Q3 FY2026",
    }
    values.update(overrides)
    return Claim(**values)


def evidence(*, value=94.04e9, entity="AAPL", metric="Revenue", period="Q3 FY2026"):
    return [Evidence(
        source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0),
        claim="revenue",
        value=value,
        locator=metric,
        period=period,
        entity=entity,
    )]


def result_for(claim_value, evidence_value=94.04e9, **evidence_overrides):
    return verify(
        claim(raw_value=claim_value),
        evidence_retriever=StaticEvidence(evidence(value=evidence_value, **evidence_overrides)),
    )


def test_contextual_claim_matching_evidence_is_verified():
    result = result_for(94.04e9)
    assert result.claim.entity.ticker == "AAPL"
    assert result.claim.metric.canonical_name == "Revenue"
    assert result.claim.period_struct.fiscal_year == 2026
    assert result.claim.period_struct.fiscal_quarter == 3
    assert result.trust_score.status.value == "verified"


def test_contextual_claim_mismatching_value_is_contradicted():
    result = result_for(94.04e9, evidence_value=100e9)
    assert result.trust_score.status.value == "contradicted"


@pytest.mark.parametrize("overrides", [
    {"period": "Q3 FY2025"},
    {"metric": "NetIncome"},
    {"entity": "MSFT"},
])
def test_wrong_identity_dimension_never_verifies(overrides):
    result = result_for(94.04e9, **overrides)
    assert result.trust_score.status.value == "unverified"


def test_missing_period_does_not_guess_or_verify():
    result = verify(
        claim(period_hint=None, raw_text="Apple reported revenue of $94.04 billion.", context_text="Apple reported revenue of $94.04 billion."),
        evidence_retriever=StaticEvidence(evidence()),
    )
    assert result.claim.period_struct is None
    assert result.trust_score.status.value == "unverified"


def test_ambiguous_entity_does_not_guess():
    result = verify(
        claim(entity_hint="Apple and Microsoft", context_text="Apple and Microsoft reported revenue of $94.04 billion in Q3 FY2026."),
        evidence_retriever=StaticEvidence(evidence()),
    )
    assert result.claim.entity is None
    assert result.trust_score.status.value == "unverified"


def test_v1_request_is_backward_compatible_and_context_is_optional():
    client = TestClient(app)
    old = client.post("/v1/verify", json={"question": "What was the financial value?", "raw_value": 101.0})
    partial = client.post("/v1/verify", json={"question": "What was revenue?", "raw_value": 101.0, "metric_hint": "Revenue"})
    invalid = client.post("/v1/verify", json={"question": "What was revenue?", "raw_value": 101.0, "period_hint": 123})
    assert old.status_code == 200
    assert partial.status_code == 200
    assert invalid.status_code == 422
    assert old.json()["verification_status"] == "unverified"
    assert partial.json()["verification_status"] == "unverified"
