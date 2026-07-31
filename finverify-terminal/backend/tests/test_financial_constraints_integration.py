"""Integration tests for constraint verification in the shared pipeline."""

from __future__ import annotations

import logging

from core import engine as core_engine
from core.evidence import EvidenceRetriever
from core.engine import verify
from core.models import Claim, Metric


def _metric(name: str, unit: str = "USD") -> Metric:
    return Metric(name=name, canonical_name=name, unit=unit)


def test_single_claim_skips_constraint_check():
    result = verify(
        Claim(
            question="What is Revenue?",
            raw_value=100.0,
            metric=_metric("Revenue"),
        ),
        evidence_retriever=EvidenceRetriever(),
    )

    assert result.verified_value == 100.0
    assert result.constraint_result is None


def test_multiple_consistent_claims_pass():
    result = verify(
        Claim(
            question="What is GrossMargin?",
            raw_value=0.4,
            actual_value=0.4,
            metric=_metric("GrossMargin", unit="percentage"),
            metadata={
                "related_claims": [
                    {"metric": "Revenue", "value": 100.0, "unit": "USD"},
                    {"metric": "CostOfGoodsSold", "value": 60.0, "unit": "USD"},
                ]
            },
        ),
        evidence_retriever=EvidenceRetriever(),
    )

    assert result.constraint_result is not None
    assert result.constraint_result.consistent is True
    assert result.constraint_result.violations == []
    assert result.constraint_result.indeterminate == []


def test_multiple_inconsistent_claims_fail():
    result = verify(
        Claim(
            question="What is GrossMargin?",
            raw_value=0.5,
            actual_value=0.5,
            metric=_metric("GrossMargin", unit="percentage"),
            metadata={
                "related_claims": [
                    {"metric": "Revenue", "value": 100.0, "unit": "USD"},
                    {"metric": "CostOfGoodsSold", "value": 60.0, "unit": "USD"},
                ]
            },
        ),
        evidence_retriever=EvidenceRetriever(),
    )

    assert result.constraint_result is not None
    assert result.constraint_result.consistent is False
    assert len(result.constraint_result.violations) == 1
    violation = result.constraint_result.violations[0]
    assert violation.metric == "GrossMargin"
    assert violation.expected == 0.4
    assert violation.actual == 0.5


def test_constraint_check_does_not_crash_pipeline(monkeypatch, caplog):
    def _raise_registry_error():
        raise RuntimeError("constraint registry unavailable")

    monkeypatch.setattr(core_engine, "_load_constraint_registry", _raise_registry_error)

    with caplog.at_level(logging.WARNING):
        result = verify(
            Claim(
                question="What is GrossMargin?",
                raw_value=0.4,
                actual_value=0.4,
                metric=_metric("GrossMargin", unit="percentage"),
                metadata={
                    "related_claims": [
                        {"metric": "Revenue", "value": 100.0, "unit": "USD"},
                        {"metric": "CostOfGoodsSold", "value": 60.0, "unit": "USD"},
                    ]
                },
            ),
            evidence_retriever=EvidenceRetriever(),
        )

    assert result.verified_value == 0.4
    assert result.constraint_result is None
    assert "Constraint verification failed" in caplog.text
