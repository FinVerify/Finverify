"""Amendment 2 Sections 3, 4, 6 / Implementation Spec Section 8A.2-8A.3.

Provider-independent: this module never calls a model, a network endpoint,
or FinVerify. It consumes an already-collected mapping of
``candidate_id -> [AnnotatorVote, ...]`` (produced by whatever ensemble
provider ran offline) and turns it into the frozen, deterministically
ordered ``llm_annotation`` ledger. Keeping model invocation entirely outside
this module is what makes it "provider-independent" and testable with pure
synthetic fixtures, matching the Section 14 "no FinVerify/model/network
dependency" test requirement.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Mapping, Sequence

from .aggregation import aggregate_votes
from .annotation_models import AnnotationRecord, AnnotatorVote

RetryProvider = Callable[[str, str], AnnotatorVote]  # (candidate_id, annotator_id) -> fresh vote


def resolve_votes_with_retry(
    candidate_id: str,
    votes: Sequence[AnnotatorVote],
    *,
    retry_count: int,
    retry_provider: RetryProvider | None = None,
) -> List[AnnotatorVote]:
    """Apply the fixed retry-then-fallback rule to one candidate's raw votes.

    Only failed (refusal/timeout/malformed) votes are retried, up to
    ``retry_count`` times each, via ``retry_provider``. If still failed after
    retries are exhausted, the failure vote is kept as-is (never silently
    dropped, never defaulted to a substantive label) — ``aggregate_votes``
    then routes any remaining failure to ``ADJUDICATION_REQUIRED``.
    """
    resolved: List[AnnotatorVote] = []
    for vote in votes:
        current = vote
        attempts = 0
        while current.failure is not None and retry_provider is not None and attempts < retry_count:
            current = retry_provider(candidate_id, current.annotator_id)
            attempts += 1
        resolved.append(current)
    return resolved


def run_annotation(
    candidate_ids: Sequence[str],
    votes_by_candidate: Mapping[str, Sequence[AnnotatorVote]],
    *,
    retry_count: int = 0,
    retry_provider: RetryProvider | None = None,
) -> List[AnnotationRecord]:
    """Run the frozen ensemble's aggregation, once, over every candidate.

    "One non-interactive batch" is enforced structurally: this function
    takes the complete candidate list up front and returns a single ledger;
    there is no partial/streaming/interactive mode and no per-candidate
    early return that could be influenced by results seen so far (each
    candidate's aggregation is independent of every other's).
    """
    ids = list(candidate_ids)
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate candidate_id in candidate_ids")
    missing = [c for c in ids if c not in votes_by_candidate]
    if missing:
        raise ValueError("missing votes for candidate(s): %s" % missing[:5])

    records: List[AnnotationRecord] = []
    for candidate_id in ids:  # caller-supplied order; ledger writer sorts for serialization
        raw_votes = votes_by_candidate[candidate_id]
        if not raw_votes:
            raise ValueError("candidate %r has no annotator votes" % candidate_id)
        for v in raw_votes:
            if v.candidate_id != candidate_id:
                raise ValueError("vote candidate_id mismatch for %r" % candidate_id)
        resolved = resolve_votes_with_retry(
            candidate_id, raw_votes, retry_count=retry_count, retry_provider=retry_provider
        )
        llm_annotation, agreement_tier, primary_code, secondary_codes = aggregate_votes(resolved)
        records.append(
            AnnotationRecord(
                candidate_id=candidate_id,
                llm_annotation=llm_annotation,
                agreement_tier=agreement_tier,
                primary_exclusion_code=primary_code,
                secondary_exclusion_codes=secondary_codes,
                eligibility_status=llm_annotation,
                votes=list(resolved),
            )
        )
    return records


def stratum_of(record: AnnotationRecord) -> str:
    """Amendment 2 Section 7 / Spec 8A.3: A/B/C strata from frozen annotation output only."""
    if record.agreement_tier == "split":
        return "C"
    if record.llm_annotation == "ELIGIBLE":
        return "A"
    if record.llm_annotation == "EXCLUDED":
        return "B"
    raise ValueError("unreachable: non-split record must be ELIGIBLE or EXCLUDED")


def stratum_populations(records: Sequence[AnnotationRecord]) -> Dict[str, int]:
    counts = {"A": 0, "B": 0, "C": 0}
    for record in records:
        counts[stratum_of(record)] += 1
    return counts
