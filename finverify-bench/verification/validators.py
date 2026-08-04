"""Dataset-level integrity and leakage validators."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict
from typing import Dict, Iterable, List, Sequence

from .schema import IDENTITY_FIELDS, PairType, VerificationPair, validate_pair_shape


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _identity_snapshot(pair: VerificationPair) -> Dict[str, object]:
    return {
        side + "." + field: getattr(getattr(pair, side), field)
        for side in ("claim", "evidence")
        for field in IDENTITY_FIELDS
    }


def validate_dataset(pairs: Sequence[VerificationPair]) -> List[str]:
    errors: List[str] = []
    ids: Dict[str, VerificationPair] = {}
    groups: Dict[str, set] = {}
    pair_signatures: Dict[str, str] = {}
    by_id = {pair.id: pair for pair in pairs}

    for pair in pairs:
        for error in validate_pair_shape(pair):
            errors.append("%s: %s" % (pair.id, error))
        if pair.id in ids:
            errors.append("duplicate pair id: %s" % pair.id)
        ids[pair.id] = pair
        groups.setdefault(pair.source_group_id, set()).add(pair.split)
        signature = "|".join(
            [_normalized_text(pair.claim.text), _normalized_text(pair.evidence.text),
             repr(pair.claim.value), repr(pair.evidence.value)]
        )
        digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()
        if digest in pair_signatures and pair_signatures[digest] != pair.id:
            other = by_id[pair_signatures[digest]]
            if other.split != pair.split:
                errors.append("exact duplicate pair across splits: %s and %s" % (other.id, pair.id))
        pair_signatures[digest] = pair.id

    for group, splits in groups.items():
        actual = {split for split in splits if split is not None}
        if len(actual) > 1:
            errors.append("source group crosses splits: %s" % group)

    for pair in pairs:
        if pair.pair_type != PairType.CONTROLLED_PERTURBATION:
            continue
        parent = by_id.get(pair.parent_pair_id)
        if parent is None:
            errors.append("%s: missing parent control %s" % (pair.id, pair.parent_pair_id))
            continue
        if parent.source_group_id != pair.source_group_id:
            errors.append("%s: derivative and parent source groups differ" % pair.id)
        if parent.split != pair.split:
            errors.append("%s: control and derivative splits differ" % pair.id)
        if pair.claim.value != parent.claim.value or pair.evidence.value != parent.evidence.value:
            errors.append("%s: controlled value changed from parent" % pair.id)
        changed = [key for key, value in _identity_snapshot(pair).items() if value != _identity_snapshot(parent)[key]]
        dimensions = {key.split(".", 1)[1] for key in changed}
        if dimensions != {pair.shift_dimension.value}:
            errors.append("%s: expected only %s to change, found %s" % (pair.id, pair.shift_dimension.value, sorted(dimensions)))

    return errors


def validate_split_isolation(pairs: Sequence[VerificationPair]) -> List[str]:
    errors: List[str] = []
    groups: Dict[str, set] = {}
    for pair in pairs:
        groups.setdefault(pair.source_group_id, set()).add(pair.split)
    for group, splits in groups.items():
        actual = {split for split in splits if split is not None}
        if len(actual) > 1:
            errors.append("source group %s appears in multiple splits: %s" % (group, sorted(actual)))
    return errors


def require_valid_dataset(pairs: Sequence[VerificationPair]) -> None:
    errors = validate_dataset(pairs)
    if errors:
        raise ValueError("dataset validation failed:\n- " + "\n- ".join(errors))
