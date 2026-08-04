"""Deterministic synthetic/audit statistics for eligibility review."""

from __future__ import annotations

import math
from typing import Mapping, Tuple


Z_95 = 1.959963984540054
AUDIT_MINIMUM_FOR_INFERENCE = 20
TOTAL_POPULATION = 14118


def stratified_fpc_normal_ci(
    strata: Mapping[str, Tuple[int, int, int]],
) -> dict[str, float | str | dict[str, float]]:
    """Return the Amendment 2 weighted agreement estimate and exact CI rule.

    Each value is ``(N_h, n_h, a_h)``: population, audited sample, and
    agreements. Empty strata are omitted from the estimator. A non-empty
    stratum with fewer than 20 audited cases is descriptive-only.
    """
    if not strata:
        raise ValueError("at least one stratum is required")
    if sum(value[0] for value in strata.values()) != TOTAL_POPULATION:
        raise ValueError("stratum populations must sum to 14118")

    per_stratum: dict[str, float] = {}
    weighted = 0.0
    inferential = True
    variance = 0.0
    for name in ("A", "B", "C"):
        if name not in strata:
            continue
        population, sample, agreements = strata[name]
        if population < 0 or sample < 0 or agreements < 0:
            raise ValueError("stratum counts must be non-negative")
        if population == 0:
            if sample != 0 or agreements != 0:
                raise ValueError("empty stratum cannot have sample counts")
            continue
        if sample > population or agreements > sample:
            raise ValueError("invalid stratum sample counts")
        if sample == 0:
            inferential = False
            continue
        p_h = agreements / sample
        per_stratum[name] = p_h
        weight = population / TOTAL_POPULATION
        weighted += weight * p_h
        if sample < AUDIT_MINIMUM_FOR_INFERENCE:
            inferential = False
        else:
            f_h = sample / population
            variance += weight * weight * (1.0 - f_h) * p_h * (1.0 - p_h) / (sample - 1)

    if not per_stratum:
        raise ValueError("at least one non-empty stratum is required")

    result: dict[str, float | str | dict[str, float]] = {
        "status": "ESTIMATED" if inferential else "NOT_ESTIMATED",
        "point_estimate": weighted if inferential or all(strata[name][1] > 0 for name in strata if strata[name][0] > 0) else None,
        "per_stratum": per_stratum,
        "critical_value": Z_95,
    }
    if not inferential:
        result.update({"variance": None, "standard_error": None, "ci_lower": None, "ci_upper": None})
        return result

    standard_error = math.sqrt(variance)
    result.update({
        "variance": variance,
        "standard_error": standard_error,
        "ci_lower": max(0.0, weighted - Z_95 * standard_error),
        "ci_upper": min(1.0, weighted + Z_95 * standard_error),
    })
    return result
