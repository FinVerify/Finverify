"""10,000-resample percentile bootstrap helpers.

The frozen deterministic RNG seed is ``0`` and the resample count is fixed
at 10,000; neither is caller-overridable.
"""

import random
from typing import Callable, Sequence

RESAMPLES = 10_000
BOOTSTRAP_SEED = 0


def _percentile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def bootstrap_ci(values: Sequence, statistic: Callable[[list], float | None]) -> dict:
    rng, values, estimates = random.Random(BOOTSTRAP_SEED), list(values), []
    for _ in range(RESAMPLES):
        if not values:
            break
        estimate = statistic([values[rng.randrange(len(values))] for _ in values])
        if estimate is not None:
            estimates.append(float(estimate))
    return {"lower": _percentile(estimates, .025) if estimates else None,
            "upper": _percentile(estimates, .975) if estimates else None,
            "valid_replicates": len(estimates), "resamples": RESAMPLES}
