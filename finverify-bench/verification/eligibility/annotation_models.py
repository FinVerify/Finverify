"""Amendment 2 Section 4 / Implementation Spec Section 8A.2: annotator votes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .models import REASON_CODES

VERDICTS = {"ELIGIBLE", "EXCLUDED", "CANNOT_RESOLVE"}
AGREEMENT_TIERS = {"unanimous", "majority", "split"}
LABEL_SOURCES = {"llm_only", "llm_audited_agree", "llm_human_consensus", "llm_human_adjudicated"}


@dataclass(frozen=True)
class AnnotatorVote:
    """A single annotator's structured output for one occurrence.

    ``failure`` covers refusal, timeout, and malformed/non-schema output —
    the three cases that must never be silently dropped and never default to
    a substantive label (Amendment 2 Section 3(6)).
    """

    candidate_id: str
    annotator_id: str
    verdict: Optional[str] = None  # None iff failure is set
    primary_exclusion_code: Optional[str] = None
    secondary_exclusion_codes: List[str] = field(default_factory=list)
    failure: Optional[str] = None  # "refusal" | "timeout" | "malformed" | None

    def __post_init__(self) -> None:
        if self.failure is not None:
            if self.failure not in {"refusal", "timeout", "malformed"}:
                raise ValueError("unknown failure kind: %r" % (self.failure,))
            if self.verdict is not None:
                raise ValueError("a failed vote must not also carry a verdict")
            return
        if self.verdict not in VERDICTS:
            raise ValueError("invalid verdict: %r" % (self.verdict,))
        if self.primary_exclusion_code and self.primary_exclusion_code not in REASON_CODES:
            raise ValueError("invalid primary_exclusion_code")
        if any(code not in REASON_CODES for code in self.secondary_exclusion_codes):
            raise ValueError("invalid secondary_exclusion_code")
        if self.verdict == "EXCLUDED" and not self.primary_exclusion_code:
            raise ValueError("an EXCLUDED vote requires a primary_exclusion_code")
        if self.verdict != "EXCLUDED" and self.primary_exclusion_code:
            raise ValueError("only an EXCLUDED vote may carry an exclusion code")


@dataclass(frozen=True)
class AnnotationRecord:
    """Corpus-wide row produced by the frozen ensemble for one occurrence.

    ``eligibility_status`` mirrors ``llm_annotation`` at this stage
    (``label_source == "llm_only"``); later audit/adjudication layers may
    additively update it without overwriting ``llm_annotation`` itself
    (Amendment 2 Section 13 / Spec Section 8A.7).
    """

    candidate_id: str
    llm_annotation: str  # ELIGIBLE | EXCLUDED | ADJUDICATION_REQUIRED
    agreement_tier: str  # unanimous | majority | split
    primary_exclusion_code: Optional[str]
    secondary_exclusion_codes: List[str]
    eligibility_status: str
    label_source: str = "llm_only"
    review_method: str = "LLM_ENSEMBLE_ANNOTATION"
    audit_status: str = "NOT_SELECTED"
    votes: List[AnnotatorVote] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.llm_annotation not in {"ELIGIBLE", "EXCLUDED", "ADJUDICATION_REQUIRED"}:
            raise ValueError("invalid llm_annotation")
        if self.agreement_tier not in AGREEMENT_TIERS:
            raise ValueError("invalid agreement_tier")
        if self.label_source not in LABEL_SOURCES:
            raise ValueError("invalid label_source")
        if self.eligibility_status != self.llm_annotation:
            raise ValueError("eligibility_status must mirror llm_annotation while label_source == llm_only")
