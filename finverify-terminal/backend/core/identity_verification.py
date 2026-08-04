"""Canonical deterministic evidence identity and value matching.

This module is the reusable source of truth for the frozen verifier's
enforced dimensions: Value, Concept, and Period.  It deliberately does not
compare Phase 7F diagnostic fields (entity, scope, accounting basis, temporal
frame, or value role).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .financial.concepts import ConceptRegistry
from .financial.document import FinancialPeriod
from .financial.period import parse_period_string, periods_compatible
from .models import Evidence


@dataclass(frozen=True)
class EvidenceIdentityMatch:
    value: float
    locator: Optional[str]
    period: Optional[str]
    period_struct: Optional[FinancialPeriod]


@dataclass(frozen=True)
class EvidenceValueComparison:
    matched: bool
    evidence: Optional[EvidenceIdentityMatch]
    saw_period_match: bool
    mismatched_periods: tuple[str, ...]
    unresolved_periods: tuple[str, ...]


def canonical_concept(name: Optional[str], registry: ConceptRegistry) -> Optional[str]:
    """Resolve an explicit concept/alias; unknown identifiers stay unknown."""
    if not name:
        return None
    return registry.resolve_alias(name)


def primary_evidence_matches(
    evidence: list[Evidence],
    metric: str,
    *,
    registry: ConceptRegistry,
    statement_period_type: Optional[str] = None,
) -> list[EvidenceIdentityMatch]:
    """Return primary evidence matching the canonical concept identity."""
    canonical_metric = canonical_concept(metric, registry)
    if canonical_metric is None:
        return []

    matches: list[EvidenceIdentityMatch] = []
    for item in evidence:
        if item.source.kind != "primary_filing" or item.value is None:
            continue
        canonical_locator = canonical_concept(item.locator, registry)
        if canonical_locator == canonical_metric:
            matches.append(
                EvidenceIdentityMatch(
                    value=item.value,
                    locator=item.locator,
                    period=item.period,
                    period_struct=parse_period_string(
                        item.period,
                        statement_period_type=statement_period_type,
                    ),
                )
            )
    return matches


def compare_value_to_evidence(
    value: float,
    evidence_matches: list[EvidenceIdentityMatch],
    claim_period: Optional[FinancialPeriod],
    *,
    tolerance: float = 0.01,
) -> EvidenceValueComparison:
    """Apply the frozen period compatibility and relative-value tolerance."""
    saw_period_match = False
    mismatched_periods: list[str] = []
    unresolved_periods: list[str] = []

    for evidence_match in evidence_matches:
        compatibility = periods_compatible(claim_period, evidence_match.period_struct)
        evidence_period_label = evidence_match.period or "unknown"
        if compatibility == "MISMATCH":
            mismatched_periods.append(evidence_period_label)
            continue
        if compatibility == "UNKNOWN":
            unresolved_periods.append(evidence_period_label)
            continue

        saw_period_match = True
        evidence_value = evidence_match.value
        if evidence_value != 0 and abs(value - evidence_value) / abs(evidence_value) <= tolerance:
            return EvidenceValueComparison(
                True,
                evidence_match,
                saw_period_match,
                tuple(mismatched_periods),
                tuple(unresolved_periods),
            )

    return EvidenceValueComparison(
        False,
        None,
        saw_period_match,
        tuple(mismatched_periods),
        tuple(unresolved_periods),
    )
