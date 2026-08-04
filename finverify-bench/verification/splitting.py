"""Source-group-safe deterministic DEV/TEST splitting."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Dict, List, Sequence, Tuple

from .schema import VerificationPair
from .validators import require_valid_dataset


def split_by_source_group(
    pairs: Sequence[VerificationPair],
    *,
    test_ratio: float = 0.65,
    seed: int = 20260804,
) -> Tuple[List[VerificationPair], Dict[str, object]]:
    if not 0 < test_ratio < 1:
        raise ValueError("test_ratio must be between 0 and 1")
    require_valid_dataset(pairs)
    groups = sorted({pair.source_group_id for pair in pairs})
    if len(groups) < 2:
        raise ValueError("at least two source groups are required")
    shuffled = list(groups)
    random.Random(seed).shuffle(shuffled)
    test_count = min(len(groups) - 1, max(1, round(len(groups) * test_ratio)))
    test_groups = set(shuffled[:test_count])
    dev_groups = set(groups) - test_groups
    split_pairs = [
        pair.__class__(**dict(pair.__dict__, split="test" if pair.source_group_id in test_groups else "dev"))
        for pair in pairs
    ]
    manifest = {
        "seed": seed,
        "test_ratio": test_ratio,
        "dev_source_groups": sorted(dev_groups),
        "test_source_groups": sorted(test_groups),
        "dev_pair_count": sum(pair.source_group_id in dev_groups for pair in split_pairs),
        "test_pair_count": sum(pair.source_group_id in test_groups for pair in split_pairs),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return split_pairs, manifest
