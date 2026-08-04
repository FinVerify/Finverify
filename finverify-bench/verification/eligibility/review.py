"""Validation of human-review records; no semantic decisions are inferred."""

from __future__ import annotations

from typing import Dict, Iterable

from .models import REASON_CODES, REASON_PRIORITY, ReviewDecision


def review_from_dict(value: Dict[str, object]) -> ReviewDecision:
    decision = ReviewDecision(**value)
    if decision.eligibility_status not in {"ELIGIBLE", "EXCLUDED", "ADJUDICATION_REQUIRED"}:
        raise ValueError("invalid eligibility_status")
    if decision.primary_exclusion_code and decision.primary_exclusion_code not in REASON_CODES:
        raise ValueError("invalid primary exclusion code")
    if any(code not in REASON_CODES for code in decision.secondary_exclusion_codes):
        raise ValueError("invalid secondary exclusion code")
    if decision.eligibility_status == "EXCLUDED" and not decision.primary_exclusion_code:
        raise ValueError("excluded review requires a primary exclusion code")
    if decision.eligibility_status == "ELIGIBLE" and decision.primary_exclusion_code:
        raise ValueError("eligible review cannot have an exclusion code")
    if decision.primary_exclusion_code and decision.secondary_exclusion_codes:
        expected = min((REASON_PRIORITY.index(code), code) for code in [decision.primary_exclusion_code, *decision.secondary_exclusion_codes])[1]
        if decision.primary_exclusion_code != expected:
            raise ValueError("reason-code precedence violation")
    return decision


def validate_review_set(reviews: Iterable[ReviewDecision], candidate_ids: set[str]) -> Dict[str, ReviewDecision]:
    result = {}
    for review in reviews:
        if review.candidate_id in result:
            raise ValueError("duplicate review decision")
        if review.candidate_id not in candidate_ids:
            raise ValueError("review references unknown candidate")
        result[review.candidate_id] = review
    if set(result) != candidate_ids:
        raise ValueError("every raw candidate requires exactly one review decision")
    return result
