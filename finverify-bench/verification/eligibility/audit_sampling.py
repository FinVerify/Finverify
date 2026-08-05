"""Amendment 2 Section 8 / Implementation Spec Section 8A.4: audit sampling.

Deterministic seed derivation, SHA-256 within-stratum rank ordering, and the
floor + largest-remainder ("Hamilton") allocation rule with capacity
redistribution. No implementation-specific PRNG is used anywhere here —
selection order is entirely a function of two frozen input hashes and each
candidate ID.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence

STRATUM_ORDER = ("A", "B", "C")


def audit_seed_hex(raw_ledger_sha256_lower: str, annotation_config_sha256_lower: str) -> str:
    _require_lower_hex64(raw_ledger_sha256_lower, "raw_ledger_sha256_lower")
    _require_lower_hex64(annotation_config_sha256_lower, "annotation_config_sha256_lower")
    payload = "finverify-phase9c-audit-v1\n" + raw_ledger_sha256_lower + "\n" + annotation_config_sha256_lower
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def candidate_rank_hex(audit_seed_hex_value: str, candidate_id: str) -> str:
    payload = "finverify-phase9c-audit-rank-v1\n" + audit_seed_hex_value + "\n" + candidate_id
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _require_lower_hex64(value: str, name: str) -> None:
    if len(value) != 64 or value != value.lower() or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("%s must be a lowercase 64-hex-digit SHA-256 digest" % name)


def rank_order(candidate_ids: Sequence[str], audit_seed_hex_value: str) -> List[str]:
    """Ascending hex rank, breaking ties by ascending UTF-8 candidate ID."""
    return sorted(candidate_ids, key=lambda c: (candidate_rank_hex(audit_seed_hex_value, c), c))


def hamilton_allocate(n: int, populations: Mapping[str, int]) -> Dict[str, int]:
    """Floor + largest-remainder ("Hamilton") allocation with capacity redistribution.

    ``populations`` maps stratum name to N_h; a stratum absent or with N_h==0
    is treated as having zero capacity. Ties in the fractional remainder use
    the fixed lexical order A < B < C. No stratum receives more than its
    population.

    Note on why redistribution is a loop rather than dead code: for a single
    stratum, q_h = n * N_h / N_total satisfies q_h <= N_h whenever n <= the
    total across the strata passed in, so floor(q_h) + (at most one
    largest-remainder unit) can never exceed N_h in one pass — the
    "exhausted stratum" case in Amendment 2 Section 8 cannot arise from a
    single call with n <= sum(populations). It becomes reachable when this
    function is reused to allocate an *increased* n against a stratum whose
    capacity was fixed by an earlier, smaller allocation (e.g. a later
    volunteer-driven top-up reusing the same populations) — the loop below
    makes that reuse safe rather than relying on the impossibility argument
    holding for every caller forever.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    total_population = sum(v for v in populations.values() if v > 0)
    if n > total_population:
        raise ValueError("n (%d) exceeds total available population (%d)" % (n, total_population))

    remaining_capacity = {s: populations[s] for s in STRATUM_ORDER if populations.get(s, 0) > 0}
    allocation = {s: 0 for s in STRATUM_ORDER}
    remaining_n = n

    while remaining_n > 0 and remaining_capacity:
        total_capacity = sum(remaining_capacity.values())
        request = min(remaining_n, total_capacity)
        q = {s: request * remaining_capacity[s] / total_capacity for s in remaining_capacity}
        floors = {s: min(int(q[s]), remaining_capacity[s]) for s in remaining_capacity}
        leftover = request - sum(floors.values())
        remainders = sorted(
            remaining_capacity,
            key=lambda s: (-(q[s] - floors[s]), STRATUM_ORDER.index(s)),
        )
        extra = {s: 0 for s in remaining_capacity}
        given = 0
        idx = 0
        guard = 0
        while given < leftover:
            s = remainders[idx % len(remainders)]
            if floors[s] + extra[s] < remaining_capacity[s]:
                extra[s] += 1
                given += 1
            idx += 1
            guard += 1
            if guard > 10 * len(remainders) + 10:
                raise RuntimeError("largest-remainder redistribution failed to converge")
        round_alloc = {s: floors[s] + extra[s] for s in remaining_capacity}

        exhausted = []
        for s, given_s in round_alloc.items():
            allocation[s] += given_s
            remaining_capacity[s] -= given_s
            remaining_n -= given_s
            if remaining_capacity[s] == 0:
                exhausted.append(s)
        for s in exhausted:
            del remaining_capacity[s]

    return allocation


def inclusion_probabilities(allocation: Mapping[str, int], populations: Mapping[str, int]) -> Dict[str, float]:
    result = {}
    for s in STRATUM_ORDER:
        n_h = allocation.get(s, 0)
        n_pop = populations.get(s, 0)
        result[s] = (n_h / n_pop) if n_pop > 0 else 0.0
    return result


@dataclass(frozen=True)
class ManifestRow:
    candidate_id: str
    stratum: str
    inclusion_probability: float
    rank_hex: str
    rank_index: int
    selected: bool


def build_manifest(
    candidates_by_stratum: Mapping[str, Sequence[str]],
    populations: Mapping[str, int],
    *,
    n: int,
    audit_seed_hex_value: str,
) -> List[ManifestRow]:
    """Build the full, deterministic manifest for every occurrence.

    Every occurrence receives a row (Amendment 2 Section 8: "Every one of
    the 14,118 occurrences receives a documented selection probability"),
    with ``selected`` true only for the first ``n_h`` candidates in rank
    order within its stratum.
    """
    for s, ids in candidates_by_stratum.items():
        if len(ids) != populations.get(s, 0):
            raise ValueError("population count for stratum %s does not match candidate list length" % s)

    allocation = hamilton_allocate(n, populations)
    pi = inclusion_probabilities(allocation, populations)

    rows: List[ManifestRow] = []
    for s in STRATUM_ORDER:
        ids = list(candidates_by_stratum.get(s, ()))
        ordered = rank_order(ids, audit_seed_hex_value)
        n_h = allocation.get(s, 0)
        for index, candidate_id in enumerate(ordered):
            rows.append(
                ManifestRow(
                    candidate_id=candidate_id,
                    stratum=s,
                    inclusion_probability=pi[s],
                    rank_hex=candidate_rank_hex(audit_seed_hex_value, candidate_id),
                    rank_index=index,
                    selected=index < n_h,
                )
            )
    return rows


def manifest_csv_bytes(rows: Sequence[ManifestRow], *, generation_timestamp: str,
                        raw_ledger_sha256_lower: str, annotation_config_sha256_lower: str,
                        audit_seed_hex_value: str) -> bytes:
    """Deterministic CSV serialization: header, input hashes, then rows in a fixed order."""
    lines = [
        "# raw_ledger_sha256=%s" % raw_ledger_sha256_lower,
        "# annotation_config_sha256=%s" % annotation_config_sha256_lower,
        "# audit_seed_hex=%s" % audit_seed_hex_value,
        "# generation_timestamp=%s" % generation_timestamp,
        "candidate_id,stratum,inclusion_probability,rank_hex,rank_index,selected",
    ]
    ordered_rows = sorted(rows, key=lambda r: (r.stratum, r.rank_index, r.candidate_id))
    for row in ordered_rows:
        lines.append(
            "%s,%s,%.17g,%s,%d,%s" % (
                row.candidate_id, row.stratum, row.inclusion_probability,
                row.rank_hex, row.rank_index, "1" if row.selected else "0",
            )
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def selected_candidates(rows: Sequence[ManifestRow]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {s: [] for s in STRATUM_ORDER}
    for row in sorted(rows, key=lambda r: (r.stratum, r.rank_index)):
        if row.selected:
            result[row.stratum].append(row.candidate_id)
    return result
