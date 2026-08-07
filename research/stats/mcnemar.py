"""Exact-small / continuity-corrected McNemar test."""

import math


def mcnemar(i_to_c: int, c_to_i: int) -> dict:
    discordant = i_to_c + c_to_i
    if min(i_to_c, c_to_i) < 0:
        raise ValueError("discordant counts must be non-negative")
    if discordant == 0:
        return {"method": "exact_binomial", "statistic": 0.0, "p_value": 1.0, "i_to_c": i_to_c, "c_to_i": c_to_i, "discordant": 0}
    if discordant < 25:
        tail = sum(math.comb(discordant, k) for k in range(min(i_to_c, c_to_i) + 1)) / 2 ** discordant
        return {"method": "exact_binomial", "statistic": None, "p_value": min(1.0, 2 * tail), "i_to_c": i_to_c, "c_to_i": c_to_i, "discordant": discordant}
    statistic = (abs(i_to_c - c_to_i) - 1) ** 2 / discordant
    return {"method": "continuity_corrected", "statistic": statistic, "p_value": math.erfc(math.sqrt(statistic / 2)), "i_to_c": i_to_c, "c_to_i": c_to_i, "discordant": discordant}
