"""Focused Phase 7H tests for the frozen Value + Concept + Period verifier."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from core.financial.concepts import ConceptRegistry
from core.financial.document import FinancialPeriod
from core.identity_verification import (
    EvidenceIdentityMatch,
    compare_value_to_evidence,
    primary_evidence_matches,
)
from core.models import Evidence, Source


def _period(year: int = 2025, quarter: int = 4) -> FinancialPeriod:
    return FinancialPeriod(kind="quarterly", fiscal_year=year, fiscal_quarter=quarter)


def _match(*, value: float = 100.0, period: FinancialPeriod | None = None) -> EvidenceIdentityMatch:
    return EvidenceIdentityMatch(value, "Revenue", "Q4 FY2025", period)


def test_identity_match_requires_valid_concept_period_and_value():
    result = compare_value_to_evidence(100.0, [_match(period=_period())], _period())
    assert result.matched is True


def test_concept_mismatch_is_not_an_evidence_match():
    registry = ConceptRegistry(BACKEND_ROOT / "config" / "concepts.yaml")
    evidence = [Evidence(
        source=Source(name="SEC", kind="primary_filing"),
        claim="net income",
        value=100.0,
        locator="net_income",
        period="Q4 FY2025",
    )]
    assert primary_evidence_matches(evidence, "Revenue", registry=registry, statement_period_type="duration") == []


def test_period_mismatch_is_not_a_value_match():
    result = compare_value_to_evidence(100.0, [_match(period=_period(2024))], _period())
    assert result.matched is False
    assert result.mismatched_periods == ("Q4 FY2025",)


def test_claim_unknown_period_is_not_a_match():
    result = compare_value_to_evidence(100.0, [_match(period=_period())], FinancialPeriod(kind="unknown"))
    assert result.matched is False
    assert result.unresolved_periods == ("Q4 FY2025",)


def test_evidence_unknown_period_is_not_a_match():
    result = compare_value_to_evidence(100.0, [EvidenceIdentityMatch(100.0, "Revenue", None, None)], _period())
    assert result.matched is False
    assert result.unresolved_periods == ("unknown",)


def test_both_unknown_periods_are_not_a_match():
    result = compare_value_to_evidence(
        100.0,
        [_match(period=FinancialPeriod(kind="unknown"))],
        FinancialPeriod(kind="unknown"),
    )
    assert result.matched is False


def test_numeric_mismatch_with_valid_identity_is_not_a_match():
    result = compare_value_to_evidence(101.1, [_match(period=_period())], _period())
    assert result.matched is False
    assert result.evidence is not None
    assert result.evidence.value == 100.0
