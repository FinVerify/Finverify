"""Amendment 2 Sections 12-13 / Implementation Spec Sections 8A.5, 8A.7.

Binding rule:

1. A blind first reviewer records ``human_audit_label``.
2. If it diverges from ``llm_annotation`` (or the case is in the fixed
   20-case double-coded subset, which is always double-reviewed regardless
   of divergence), a second, independent blind reviewer records
   ``human_audit_label_2``.
3. If the two human judgments agree, that consensus is binding
   (``label_source = llm_human_consensus``) and is never overridden by an
   unblinded adjudicator, including in favor of the LLM.
4. If they disagree, an adjudicator sees the full record and issues
   ``adjudicated_label`` with a mandatory timestamped written justification
   (``label_source = llm_human_adjudicated``).

If only one human review exists and it agrees with ``llm_annotation``, that
is ``label_source = llm_audited_agree`` — the LLM value stands, now
corroborated. A single human review that diverges is *not* terminal by
itself; it requires the second review before any label_source beyond
"pending" can be assigned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

VALID_LABELS = {"ELIGIBLE", "EXCLUDED", "ADJUDICATION_REQUIRED"}


class PendingSecondReview(Exception):
    """Raised when a label_source is requested before a required second review exists."""


@dataclass(frozen=True)
class AdjudicationRecord:
    candidate_id: str
    adjudicated_label: str
    justification: str
    timestamp: str
    adjudicator_id: str
    conflict_of_interest: bool = False

    def __post_init__(self) -> None:
        if self.adjudicated_label not in VALID_LABELS:
            raise ValueError("invalid adjudicated_label")
        if not self.justification or not self.justification.strip():
            raise ValueError("adjudication requires a mandatory written justification")
        if not self.timestamp:
            raise ValueError("adjudication requires a timestamp")


@dataclass(frozen=True)
class AuditOutcome:
    candidate_id: str
    audit_status: str  # SELECTED | DOUBLE_CODED | ADJUDICATED
    human_audit_label: Optional[str]
    human_audit_label_2: Optional[str]
    adjudicated_label: Optional[str]
    eligibility_status: str
    label_source: str
    agrees_with_llm: Optional[bool]


def requires_second_review(*, human_audit_label: str, llm_annotation: str, is_double_coded: bool) -> bool:
    """Section 12(2): diverges from llm_annotation, OR is in the fixed double-coded subset."""
    return is_double_coded or human_audit_label != llm_annotation


def resolve_audit_outcome(
    *,
    candidate_id: str,
    llm_annotation: str,
    human_audit_label: str,
    human_audit_label_2: Optional[str] = None,
    is_double_coded: bool = False,
    adjudication: Optional[AdjudicationRecord] = None,
) -> AuditOutcome:
    if human_audit_label not in VALID_LABELS:
        raise ValueError("invalid human_audit_label")
    if human_audit_label_2 is not None and human_audit_label_2 not in VALID_LABELS:
        raise ValueError("invalid human_audit_label_2")

    needs_second = requires_second_review(
        human_audit_label=human_audit_label, llm_annotation=llm_annotation, is_double_coded=is_double_coded,
    )

    if not needs_second:
        # Single review, agrees with LLM: llm value stands, corroborated.
        return AuditOutcome(
            candidate_id=candidate_id, audit_status="SELECTED",
            human_audit_label=human_audit_label, human_audit_label_2=None, adjudicated_label=None,
            eligibility_status=llm_annotation, label_source="llm_audited_agree", agrees_with_llm=True,
        )

    if human_audit_label_2 is None:
        raise PendingSecondReview("second independent blind review required before an outcome can be resolved")

    if human_audit_label == human_audit_label_2:
        # Unanimous blind-human consensus is binding, even over the LLM,
        # and cannot be overridden by an unblinded adjudicator.
        return AuditOutcome(
            candidate_id=candidate_id,
            audit_status="DOUBLE_CODED" if is_double_coded else "SELECTED",
            human_audit_label=human_audit_label, human_audit_label_2=human_audit_label_2, adjudicated_label=None,
            eligibility_status=human_audit_label, label_source="llm_human_consensus",
            agrees_with_llm=(human_audit_label == llm_annotation),
        )

    # Two blind humans disagree: adjudication required.
    if adjudication is None:
        raise PendingSecondReview("human-human disagreement requires adjudication before an outcome can be resolved")
    if adjudication.candidate_id != candidate_id:
        raise ValueError("adjudication record candidate_id mismatch")
    return AuditOutcome(
        candidate_id=candidate_id, audit_status="ADJUDICATED",
        human_audit_label=human_audit_label, human_audit_label_2=human_audit_label_2,
        adjudicated_label=adjudication.adjudicated_label,
        eligibility_status=adjudication.adjudicated_label, label_source="llm_human_adjudicated",
        agrees_with_llm=(adjudication.adjudicated_label == llm_annotation),
    )


def cohens_kappa(pairs: list[tuple[str, str]]) -> Optional[float]:
    """Unweighted Cohen's kappa over (rater_a_label, rater_b_label) pairs.

    Returns ``None`` when undefined (no pairs, or zero expected-by-chance
    agreement variance i.e. every pair has the same label from both raters
    with no observed disagreement AND no label variation to estimate chance
    agreement from — kappa is mathematically 1.0 in the all-agree, single
    label case, which this function returns rather than None; None is
    reserved for the true 0/0 empty-input case).
    """
    n = len(pairs)
    if n == 0:
        return None
    labels = sorted({label for pair in pairs for label in pair})
    observed_agreement = sum(1 for a, b in pairs if a == b) / n
    a_counts: Dict[str, int] = {label: 0 for label in labels}
    b_counts: Dict[str, int] = {label: 0 for label in labels}
    for a, b in pairs:
        a_counts[a] += 1
        b_counts[b] += 1
    expected_agreement = sum((a_counts[label] / n) * (b_counts[label] / n) for label in labels)
    if expected_agreement >= 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1.0 - expected_agreement)
