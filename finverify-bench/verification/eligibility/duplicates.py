"""Conservative fact clustering and unchanged Section 40 canonical hierarchy."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Tuple

from .models import ReviewDecision
from .normalization import determinate, normalize_identity, normalized_value_key


def identity_key(raw: Dict[str, Any], review: ReviewDecision) -> Tuple[Any, ...] | None:
    normalized = normalize_identity(review.identity)
    if not all(determinate(normalized.get(name)) for name in normalized):
        return None
    value = normalized_value_key(raw["normalized_value"], raw["normalized_unit"], raw["scale"])
    return tuple(normalized[name] for name in ("entity", "concept", "period", "scope", "accounting_basis", "temporal_frame", "value_role")) + (value,)


def fact_cluster_id(key: Tuple[Any, ...]) -> str:
    payload = json.dumps(key, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return "fc1_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_sort_key(raw: Dict[str, Any], review: ReviewDecision) -> Tuple[Any, ...]:
    table_preference = 0 if (review.is_formal_statement_table and not review.is_repeated_narrative_restatement) else 1
    return (-review.directness_rank, table_preference, raw["source_id"], raw["source_locator"])

