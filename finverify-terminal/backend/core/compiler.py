"""Claim compilation: normalize external inputs into the shared Claim model."""

import logging
from typing import Any

from .models import Claim

logger = logging.getLogger(__name__)


def compile_claim(claim: Claim | dict[str, Any]) -> Claim:
    if isinstance(claim, Claim):
        if hasattr(claim, "model_copy"):
            compiled = claim.model_copy(deep=True)
        else:
            compiled = claim.copy(deep=True)
    elif hasattr(Claim, "model_validate"):
        compiled = Claim.model_validate(claim)
    else:
        compiled = Claim.parse_obj(claim)

    return _apply_context_scale_bridge(compiled)


def _apply_context_scale_bridge(claim: Claim) -> Claim:
    """PHASE 3C.1: API numeric scale bridge.

    This is the single normalization boundary every verification entry
    point passes through (core.engine.verify() -> compile_claim()), so it
    is the correct place to fix the "raw_value=109.42 alongside
    context_text='...$109.42 billion...'" scale-loss bug at its root,
    rather than downstream in SEC evidence handling or Phase 3A's frozen
    comparison tolerances (both explicitly out of scope for this fix).

    Only ever *multiplies* claim.raw_value by a scale factor recovered
    from claim.context_text via app.parser.resolve_context_scale(); never
    replaces raw_value with a re-parsed number, and never applies a
    correction when the match is missing or ambiguous (see
    resolve_context_scale's docstring for the exact fail-closed rules).
    A resolution attempt is always recorded in claim.metadata["scale_bridge"]
    when context_text is present, whether or not a correction was applied,
    so the decision is auditable downstream.
    """
    if claim.raw_value is None or not claim.context_text:
        return claim

    # Local import: app.parser pulls in app.dvl, and eagerly importing that
    # at core/compiler.py module load time would widen core's import
    # surface unnecessarily for the (common) path where context_text is
    # absent. Deferring the import to this branch keeps compile_claim's
    # module-level import graph unchanged for every caller that doesn't use
    # context_text.
    from app.parser import resolve_context_scale

    try:
        match = resolve_context_scale(claim.raw_value, claim.context_text)
    except Exception as exc:  # never let scale-bridging itself break verification
        logger.warning("Context scale bridge failed for %r: %s", claim.question, exc)
        return claim

    if match is None:
        claim.metadata = {
            **claim.metadata,
            "scale_bridge": {
                "applied": False,
                "reason": "no_unambiguous_scale_match",
            },
        }
        return claim

    before = claim.raw_value
    after = before * float(match.multiplier)
    claim.raw_value = after
    claim.metadata = {
        **claim.metadata,
        "scale_bridge": {
            "applied": True,
            "scale_word": match.scale_word,
            "unit": match.unit.value,
            "currency": match.currency,
            "matched_token": match.matched_token,
            "before": before,
            "after": after,
        },
    }
    return claim
