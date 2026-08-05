"""Amendment 2 Section 4 / Implementation Spec Section 8A.2: deterministic aggregation.

Pure function of one candidate's annotator votes. No randomness, no model
calls, no dependency on any other candidate's outcome. Applies uniformly,
in one non-interactive batch, to every occurrence — the caller
(``annotation_runner``) is responsible for iterating candidates in a fixed
order; this module only aggregates a single vote set.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .annotation_models import AnnotatorVote
from .models import REASON_PRIORITY


def aggregate_votes(votes: Sequence[AnnotatorVote]) -> Tuple[str, str, Optional[str], List[str]]:
    """Return ``(llm_annotation, agreement_tier, primary_code, secondary_codes)``.

    Failure votes (refusal/timeout/malformed) are treated as non-substantive:
    they can never contribute to a k-of-k or (k-1)-of-k count for a
    substantive label. If any failure is present the occurrence cannot reach
    unanimous/majority on a fresh, complete vote set, so it is routed to
    ``split`` / ``ADJUDICATION_REQUIRED`` — the fixed retry-then-fallback
    behavior belongs to the runner (which decides whether to retry before
    calling this function); this function never defaults a failure to a
    substantive label.
    """
    if not votes:
        raise ValueError("at least one vote is required")
    ids = {v.candidate_id for v in votes}
    if len(ids) != 1:
        raise ValueError("aggregate_votes requires a single candidate's votes")

    k = len(votes)
    failures = [v for v in votes if v.failure is not None]
    substantive = [v for v in votes if v.failure is None]

    def split() -> Tuple[str, str, Optional[str], List[str]]:
        return "ADJUDICATION_REQUIRED", "split", None, []

    if failures:
        return split()

    eligible_votes = [v for v in substantive if v.verdict == "ELIGIBLE"]
    excluded_votes = [v for v in substantive if v.verdict == "EXCLUDED"]
    unresolved_votes = [v for v in substantive if v.verdict == "CANNOT_RESOLVE"]
    if unresolved_votes:
        return split()

    n_eligible = len(eligible_votes)
    n_excluded = len(excluded_votes)

    if n_eligible == k:
        return "ELIGIBLE", "unanimous", None, []
    if n_excluded == k:
        return _excluded_result(excluded_votes, "unanimous")
    if n_eligible == k - 1:
        return "ELIGIBLE", "majority", None, []
    if n_excluded == k - 1:
        return _excluded_result(excluded_votes, "majority")
    return split()


def _excluded_result(excluded_votes: Sequence[AnnotatorVote], tier: str) -> Tuple[str, str, Optional[str], List[str]]:
    """Resolve primary/secondary exclusion codes among agreeing EXCLUDED annotators.

    A code disagreement among annotators who agree on the EXCLUDED verdict
    itself routes the occurrence to ADJUDICATION_REQUIRED rather than being
    silently resolved by vote count (Amendment 2 Section 4).
    """
    primary_codes = {v.primary_exclusion_code for v in excluded_votes}
    if len(primary_codes) != 1:
        return "ADJUDICATION_REQUIRED", "split", None, []
    primary = next(iter(primary_codes))
    all_secondary = set()
    for v in excluded_votes:
        all_secondary.update(v.secondary_exclusion_codes)
    all_secondary.discard(primary)
    ordered_secondary = [code for code in REASON_PRIORITY if code in all_secondary]
    return "EXCLUDED", tier, primary, ordered_secondary
