"""Data contracts for synthetic/reviewed eligibility construction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CHALLENGEABLE_DIMENSIONS = (
    "concept", "period", "entity", "scope", "accounting_basis", "temporal_frame", "value_role",
)
REASON_CODES = {
    "EXC_NON_FINANCIAL", "EXC_DERIVED_ONLY", "EXC_ENTITY_AMBIGUOUS", "EXC_CONCEPT_AMBIGUOUS",
    "EXC_PERIOD_AMBIGUOUS", "EXC_SCOPE_AMBIGUOUS", "EXC_BASIS_AMBIGUOUS",
    "EXC_TEMPORAL_AMBIGUOUS", "EXC_VALUE_ROLE_AMBIGUOUS", "EXC_EVIDENCE_INSUFFICIENT",
    "EXC_TABLE_CONTEXT_LOST", "EXC_PARSE_FAILURE", "EXC_OUT_OF_SCOPE",
}
REASON_PRIORITY = (
    "EXC_NON_FINANCIAL", "EXC_DERIVED_ONLY", "EXC_OUT_OF_SCOPE",
    "EXC_ENTITY_AMBIGUOUS", "EXC_CONCEPT_AMBIGUOUS", "EXC_PERIOD_AMBIGUOUS",
    "EXC_SCOPE_AMBIGUOUS", "EXC_BASIS_AMBIGUOUS", "EXC_TEMPORAL_AMBIGUOUS",
    "EXC_VALUE_ROLE_AMBIGUOUS", "EXC_EVIDENCE_INSUFFICIENT",
    "EXC_TABLE_CONTEXT_LOST", "EXC_PARSE_FAILURE",
)


@dataclass(frozen=True)
class ReviewDecision:
    candidate_id: str
    eligibility_status: str
    identity: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    primary_exclusion_code: Optional[str] = None
    secondary_exclusion_codes: List[str] = field(default_factory=list)
    challengeable_dimensions: List[str] = field(default_factory=list)
    meaningful_challenge_dimensions: List[str] = field(default_factory=list)
    directness_rank: int = 0
    is_formal_statement_table: bool = False
    is_repeated_narrative_restatement: bool = False
    reviewer_id: Optional[str] = None
    review_method: str = "independent_review"
    ambiguity_status: str = "NONE"
    review_workflow_status: str = "FINALIZED"
    review_timestamp: Optional[str] = None
    adjudication_id: Optional[str] = None


@dataclass(frozen=True)
class SourceDescriptor:
    source_id: str
    issuer_key: str
    reporting_event_key: str
    reporting_period_coverage: str = ""
    artifact_role: str = ""
    same_event_key: Optional[str] = None

