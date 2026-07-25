"""Claim compilation: normalize external inputs into the shared Claim model."""

from typing import Any

from .models import Claim


def compile_claim(claim: Claim | dict[str, Any]) -> Claim:
    if isinstance(claim, Claim):
        return claim.copy(deep=True)
    return Claim.parse_obj(claim)
