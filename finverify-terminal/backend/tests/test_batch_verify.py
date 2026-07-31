"""Tests for the batch verification engine and API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from core import engine as core_engine
from core.evidence import EvidenceRetriever
from core.engine import verify_batch
from core.financial.concepts import ConceptRegistry
from core.models import BatchClaim, BatchVerifyRequest


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def client():
    return TestClient(app)


def load_fixture(name: str) -> BatchVerifyRequest:
    payload = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    return BatchVerifyRequest(
        claims=[
            BatchClaim(
                question=claim.get("question", claim["metric"]),
                raw_value=claim.get("raw_value", claim["value"]),
                metric=claim.get("metric"),
                entity=claim.get("entity"),
                period=claim.get("period"),
                actual_value=claim.get("actual_value"),
            )
            for claim in payload["claims"]
        ],
        include_constraints=payload.get("include_constraints", True),
        tolerance=payload.get("tolerance", 1e-6),
    )


def test_batch_consistent_claims():
    request = BatchVerifyRequest(
        claims=[
            BatchClaim(question="Revenue", raw_value=100),
            BatchClaim(question="COGS", raw_value=60),
            BatchClaim(question="GrossMargin", raw_value=0.4, actual_value=0.4),
        ]
    )

    response = verify_batch(request, evidence_retriever=EvidenceRetriever())

    assert len(response.results) == 3
    assert all(result.constraint_result is None for result in response.results)
    assert response.constraint_result is not None
    assert response.constraint_result.consistent is True


def test_batch_inconsistent_claims():
    request = BatchVerifyRequest(
        claims=[
            BatchClaim(question="Revenue", raw_value=100),
            BatchClaim(question="COGS", raw_value=60),
            BatchClaim(question="GrossMargin", raw_value=0.5, actual_value=0.5),
        ]
    )

    response = verify_batch(request, evidence_retriever=EvidenceRetriever())

    assert response.constraint_result is not None
    assert response.constraint_result.consistent is False
    assert len(response.constraint_result.violations) > 0


def test_batch_single_claim_skips_constraints():
    request = BatchVerifyRequest(
        claims=[BatchClaim(question="Revenue", raw_value=100)]
    )

    response = verify_batch(request, evidence_retriever=EvidenceRetriever())

    assert len(response.results) == 1
    assert response.constraint_result is None


def test_batch_dimension_mismatch(monkeypatch, tmp_path, caplog):
    config_path = tmp_path / "concepts.json"
    config_path.write_text(
        json.dumps(
            {
                "concepts": {
                    "Revenue": {"dimension": "currency", "unit": "USD"},
                    "CostOfGoodsSold": {
                        "aliases": ["COGS"],
                        "dimension": "currency",
                        "unit": "USD",
                    },
                    "GrossMargin": {
                        "dimension": "currency",
                        "unit": "USD",
                        "formula": "(Revenue - CostOfGoodsSold) / Revenue",
                        "requires": ["Revenue", "CostOfGoodsSold"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(core_engine, "_load_constraint_registry", lambda: ConceptRegistry(config_path))

    request = BatchVerifyRequest(
        claims=[
            BatchClaim(question="Revenue", raw_value=100),
            BatchClaim(question="COGS", raw_value=60),
            BatchClaim(question="GrossMargin", raw_value=0.4),
        ]
    )

    with caplog.at_level("WARNING"):
        response = verify_batch(request, evidence_retriever=EvidenceRetriever())

    assert response.constraint_result is None
    assert "Batch constraint verification failed" in caplog.text


def test_batch_aapl_10k():
    request = load_fixture("aapl_2024_10k_claims.json")

    response = verify_batch(request, evidence_retriever=EvidenceRetriever())

    assert len(response.results) == 4
    assert response.constraint_result is not None
    assert response.constraint_result.consistent is True


def test_batch_verify_endpoint(client, monkeypatch):
    def verify_with_stubbed_evidence(request: BatchVerifyRequest):
        return verify_batch(request, evidence_retriever=EvidenceRetriever())

    monkeypatch.setattr("app.main.core_verify_batch", verify_with_stubbed_evidence)

    response = client.post(
        "/v1/verify/batch",
        json={
            "claims": [
                {"question": "Revenue", "raw_value": 100},
                {"question": "COGS", "raw_value": 60},
                {"question": "GrossMargin", "raw_value": 0.4, "actual_value": 0.4},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 3
    assert payload["constraint_result"]["consistent"] is True
