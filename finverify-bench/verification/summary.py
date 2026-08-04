"""Lightweight dataset QA summaries, not scientific performance metrics."""

from collections import Counter
from typing import Dict, Sequence

from .schema import VerificationPair


def summarize_pairs(pairs: Sequence[VerificationPair]) -> Dict[str, object]:
    return {
        "total_pairs": len(pairs),
        "pair_types": dict(Counter(pair.pair_type.value for pair in pairs)),
        "labels": dict(Counter(pair.label.value for pair in pairs)),
        "source_groups": len({pair.source_group_id for pair in pairs}),
        "shift_dimensions": dict(Counter(pair.shift_dimension.value for pair in pairs if pair.shift_dimension)),
        "splits": dict(Counter(pair.split for pair in pairs if pair.split)),
        "tickers": dict(Counter(pair.source.ticker for pair in pairs if pair.source.ticker)),
        "document_types": dict(Counter(pair.source.document_type for pair in pairs if pair.source.document_type)),
    }
