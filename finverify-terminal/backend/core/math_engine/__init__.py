"""Rule-based math engine with a legacy DVL adapter."""

from ..models import Claim, VerificationContext

from .engine import MathEngine


def validate(
    claim: Claim,
    context: VerificationContext | None = None,
) -> tuple[float | None, list[dict], str, str]:
    """Backward-compatible tuple adapter for legacy callers."""
    math_engine = MathEngine()
    verification_context = context or VerificationContext(
        claim=claim,
        entity=claim.entity,
        metric=claim.metric,
        period=claim.period,
        metadata=dict(claim.metadata),
        current_value=claim.raw_value,
    )
    result = math_engine.run(claim, verification_context)
    return math_engine.to_legacy_tuple(result, claim, verification_context)


__all__ = ["MathEngine", "validate"]
