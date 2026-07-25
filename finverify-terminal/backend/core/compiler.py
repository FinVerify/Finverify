"""Claim compilation: normalize external inputs into the shared Claim model."""

from typing import Any

from .models import Claim


def compile_claim(claim: Claim | dict[str, Any]) -> Claim:
    if isinstance(claim, Claim):
        if hasattr(claim, "model_copy"):
            return claim.model_copy(deep=True)
        return claim.copy(deep=True)
    if hasattr(Claim, "model_validate"):
        return Claim.model_validate(claim)
    return Claim.parse_obj(claim)
