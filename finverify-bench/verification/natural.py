"""Independent natural-pair ingestion and eligibility filtering."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterable, List, Optional, Sequence

from .schema import PairLabel, PairType, VerificationPair


def ingest_natural_pairs(
    pairs: Iterable[VerificationPair],
    *,
    eligibility: Optional[Callable[[VerificationPair], bool]] = None,
) -> List[VerificationPair]:
    """Keep source-backed natural pairs without consulting FinVerify output."""
    result = []
    for pair in pairs:
        if pair.pair_type != PairType.NATURAL:
            raise ValueError("natural ingestion received non-natural pair %s" % pair.id)
        if eligibility is None or eligibility(pair):
            result.append(pair)
    return result


def eligible_natural_pair(pair: VerificationPair) -> bool:
    """Default structural eligibility; content adjudication remains external."""
    return bool(
        pair.claim.text.strip()
        and pair.evidence.text.strip()
        and pair.source.document_id
        and pair.source.document_hash
        and pair.source.source_claim_id
    )
