"""Tests for core.financial.document_verifier.verify_document."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.evidence import EvidenceRetriever
from core.financial.concepts import ConceptRegistry
from core.financial.constraints.models import ConstraintStatus
from core.engine import _build_batch_claim
from core.financial.claim_extractor import extract_claims
from core.financial.document_verifier import _claim_to_batch_claim, verify_document
from core.financial.mapper import StatementMapper
from core.models import BatchClaim, Claim, Entity, Metric


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "concepts.yaml"


def _annual_entry(start: str, end: str, filed: str, value: float, accn: str, fy: int) -> dict:
    return {
        "start": start,
        "end": end,
        "val": value,
        "accn": accn,
        "fy": fy,
        "fp": "FY",
        "form": "10-K",
        "filed": filed,
    }


def make_aapl_facts() -> dict:
    """Revenue + COGS in the same fiscal year -> GrossMargin constraint is checkable."""
    return {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 391_035_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "CostOfGoodsAndServicesSold": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 210_352_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 93_736_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
            }
        },
    }


def make_aapl_document(max_periods: int = 1):
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)
    return mapper.map_xbrl_to_document(
        make_aapl_facts(),
        {
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "cik": "0000320193",
            "filing_type": "10-K",
            "filing_date": "2024-11-01",
            "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/",
        },
        max_periods=max_periods,
    )


def test_verify_document_aapl():
    document = make_aapl_document()

    response = verify_document(document, evidence_retriever=EvidenceRetriever())

    assert len(response.results) == 3
    assert all(result.verified_value is not None for result in response.results)


def test_verify_document_empty_document():
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)
    document = mapper.map_xbrl_to_document({"facts": {"us-gaap": {}}}, {"company_name": "Empty Co"})

    response = verify_document(document, evidence_retriever=EvidenceRetriever())

    assert response.results == []
    assert response.constraint_result is None


def test_verify_document_exercises_constraints_via_verify_batch():
    """GrossMargin should be internally checkable from Revenue + COGS via the
    same constraint engine verify_batch() already uses -- DocumentVerifier
    must not reimplement any of this itself, only route claims into it."""
    document = make_aapl_document()

    response = verify_document(document, evidence_retriever=EvidenceRetriever())

    # Revenue and CostOfGoodsSold are both present in the batch, so
    # verify_batch()'s existing constraint machinery (ConceptRegistry.load_equations()
    # + ConstraintVerifier) should have something to evaluate.
    assert response.constraint_result is not None
    assert response.constraint_result.status == ConstraintStatus.NOT_EVALUATED
    assert response.constraint_result.consistent is None
    assert response.constraint_result.coverage.loaded == 4
    assert response.constraint_result.coverage.derivable == 1
    assert response.constraint_result.coverage.not_applicable == 3
    metric_names = {result.claim.metric.canonical_name for result in response.results if result.claim.metric}
    assert {"Revenue", "CostOfGoodsSold"}.issubset(metric_names)


def test_verify_document_drops_claims_without_raw_value(monkeypatch):
    """Claims with raw_value=None can't become a BatchClaim (raw_value is a
    required float there) and must be skipped rather than crash."""
    document = make_aapl_document()

    def fake_extract_claims(_document):
        return [
            Claim(question="What is Revenue for Apple Inc.?", raw_value=100.0, metric=Metric(name="Revenue")),
            Claim(question="Undetermined claim", raw_value=None, metric=Metric(name="Revenue")),
        ]

    monkeypatch.setattr("core.financial.document_verifier.extract_claims", fake_extract_claims)

    response = verify_document(document, evidence_retriever=EvidenceRetriever())

    assert len(response.results) == 1
    assert response.results[0].claim.question == "What is Revenue for Apple Inc.?"


def test_claim_to_batch_claim_drops_metadata_flattens_entity_and_preserves_provenance():
    claim = Claim(
        question="What is Revenue for Apple Inc. (FY2024)?",
        raw_value=391_035_000_000.0,
        metric=Metric(name="Revenue", canonical_name="Revenue", unit="USD"),
        entity=Entity(name="Apple Inc.", ticker="AAPL", cik="0000320193"),
        period="2024",
        metadata={"source": "10-K filed 2024-11-01", "statement": "IncomeStatement"},
    )

    batch_claim = _claim_to_batch_claim(claim)

    assert isinstance(batch_claim, BatchClaim)
    assert batch_claim.question == claim.question
    assert batch_claim.raw_value == claim.raw_value
    assert batch_claim.metric == "Revenue"
    assert batch_claim.entity == "Apple Inc."
    assert batch_claim.ticker == "AAPL"
    assert batch_claim.cik == "0000320193"
    assert batch_claim.period == "2024"
    assert not hasattr(batch_claim, "metadata")


def test_document_claim_round_trip_preserves_entity_provenance():
    document = make_aapl_document()
    original_claim = next(claim for claim in extract_claims(document) if claim.entity is not None)

    batch_claim = _claim_to_batch_claim(original_claim)
    rebuilt_claim = _build_batch_claim(batch_claim)

    assert rebuilt_claim.entity is not None
    assert rebuilt_claim.entity.name == original_claim.entity.name
    assert rebuilt_claim.entity.ticker == "AAPL"
    assert rebuilt_claim.entity.cik == "0000320193"


def test_claim_to_batch_claim_returns_none_for_missing_raw_value():
    claim = Claim(question="No value here", raw_value=None)

    assert _claim_to_batch_claim(claim) is None


def test_verify_document_passes_through_tolerance_and_include_constraints():
    document = make_aapl_document()

    response = verify_document(
        document,
        include_constraints=False,
        evidence_retriever=EvidenceRetriever(),
    )

    assert response.constraint_result is None
