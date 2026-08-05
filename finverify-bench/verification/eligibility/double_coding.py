"""Amendment 2 Section 12 / Implementation Spec Section 8A.5: double coding.

Exactly 20 cases within the guaranteed n=100 audit floor, allocated across
the *already selected* audit strata (not the full stratum populations)
using the same floor + largest-remainder + A<B<C + capacity-redistribution
rule as the primary audit allocation. These are a subset of the audit
sample, never additional cases.
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Mapping, Sequence

from .audit_sampling import STRATUM_ORDER, hamilton_allocate

DOUBLE_CODE_COUNT = 20


def double_code_rank_hex(audit_seed_hex_value: str, candidate_id: str) -> str:
    payload = "finverify-phase9c-double-code-v1\n" + audit_seed_hex_value + "\n" + candidate_id
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_double_coded(
    selected_by_stratum: Mapping[str, Sequence[str]],
    *,
    audit_seed_hex_value: str,
    count: int = DOUBLE_CODE_COUNT,
) -> Dict[str, List[str]]:
    """Choose ``count`` double-coded cases from the already-selected audit sample.

    ``selected_by_stratum`` must be the manifest's selected candidates per
    stratum (its sizes are the "capacities" for this allocation — the
    already-selected audit counts, not the full population).
    """
    capacities = {s: len(selected_by_stratum.get(s, ())) for s in STRATUM_ORDER}
    total_selected = sum(capacities.values())
    if count > total_selected:
        raise ValueError("cannot double-code more cases than were selected for audit")
    allocation = hamilton_allocate(count, capacities)

    result: Dict[str, List[str]] = {s: [] for s in STRATUM_ORDER}
    for s in STRATUM_ORDER:
        ids = list(selected_by_stratum.get(s, ()))
        ordered = sorted(ids, key=lambda c: (double_code_rank_hex(audit_seed_hex_value, c), c))
        result[s] = ordered[: allocation.get(s, 0)]
    return result


def flatten(double_coded_by_stratum: Mapping[str, Sequence[str]]) -> List[str]:
    flat: List[str] = []
    for s in STRATUM_ORDER:
        flat.extend(double_coded_by_stratum.get(s, ()))
    return flat
