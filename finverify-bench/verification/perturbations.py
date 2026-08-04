"""Deterministic controlled matched-pair construction."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any, Dict, Optional

from .schema import (
    ClaimEvidence,
    PairLabel,
    PairType,
    ShiftDimension,
    VerificationPair,
    validate_pair_shape,
)


def _stable_id(parent_id: str, dimension: ShiftDimension, mutation_side: str) -> str:
    digest = hashlib.sha256((parent_id + "|" + dimension.value + "|" + mutation_side).encode()).hexdigest()[:12]
    return "fvv_" + digest


def make_matched_control(pair: VerificationPair) -> VerificationPair:
    """Normalize a source pair into an explicit SUPPORT matched control."""
    if pair.claim.value != pair.evidence.value:
        raise ValueError("matched control requires equal claim/evidence values")
    control = replace(
        pair,
        label=PairLabel.SUPPORT,
        pair_type=PairType.MATCHED_CONTROL,
        shift_dimension=None,
        parent_pair_id=None,
        mutation_side=None,
        split=None,
        metadata=dict(pair.metadata, preserve_value=True, derivation="source_matched_control"),
    )
    errors = validate_pair_shape(control)
    if errors:
        raise ValueError("invalid matched control: " + "; ".join(errors))
    return control


def perturb_pair(
    control: VerificationPair,
    dimension: ShiftDimension,
    replacement: Any,
    *,
    mutation_side: str = "evidence",
    label: PairLabel = PairLabel.REJECT,
    text: Optional[str] = None,
) -> VerificationPair:
    """Create one deterministic single-dimension derivative from a control.

    Metadata are transformed independently from text. Callers may provide a
    text rendering, but this function never invents financial prose.
    """
    control = make_matched_control(control)
    if mutation_side not in {"claim", "evidence"}:
        raise ValueError("mutation_side must be claim or evidence")
    record = getattr(control, mutation_side)
    updates: Dict[str, Any] = {dimension.value: replacement}
    if text is not None:
        updates["text"] = text
    changed = replace(record, **updates)
    derivative = replace(
        control,
        id=_stable_id(control.id, dimension, mutation_side),
        pair_type=PairType.CONTROLLED_PERTURBATION,
        label=label,
        shift_dimension=dimension,
        parent_pair_id=control.id,
        mutation_side=mutation_side,
        claim=changed if mutation_side == "claim" else control.claim,
        evidence=changed if mutation_side == "evidence" else control.evidence,
        metadata=dict(control.metadata, preserve_value=True, derivation="deterministic_single_dimension"),
    )
    errors = validate_pair_shape(derivative)
    if errors:
        raise ValueError("invalid perturbation: " + "; ".join(errors))
    return derivative
