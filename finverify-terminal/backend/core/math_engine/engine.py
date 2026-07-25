"""Rule-based math engine with a legacy tuple adapter."""

from app.dvl import compute_trust

from ..models import Claim, MathResult, RuleResult, RuleTrace, VerificationContext
from .rules.registry import RuleRegistry


class MathEngine:
    """Run formatting rules and expose both modern and legacy outputs."""

    def __init__(self, registry: RuleRegistry | None = None):
        self.registry = registry or RuleRegistry()

    def run(self, claim: Claim, context: VerificationContext) -> MathResult:
        if context.current_value is None:
            context.current_value = claim.raw_value

        if context.current_value is None:
            return MathResult(
                verified_value=None,
                corrections=[],
                rule_trace=RuleTrace(
                    results=[
                        RuleResult(
                            applied=False,
                            confidence=0.0,
                            reason="No numeric value available for math verification",
                            metadata={"stage": "input"},
                        ),
                    ],
                ),
                confidence=0.0,
            )

        corrections, trace = self.registry.apply(claim, context)

        # TODO: Replace the fixed confidence with a rule-aware calculation once
        # the confidence contract is defined across math, evidence, and trust.
        return MathResult(
            verified_value=context.current_value,
            corrections=corrections,
            rule_trace=trace,
            confidence=0.8,
        )

    def to_legacy_tuple(
        self,
        result: MathResult,
        claim: Claim,
        context: VerificationContext,
    ) -> tuple[float | None, list[dict], str, str]:
        if claim.raw_value is None:
            return None, [], "LOW", "#f87171"

        correction_log = [
            {"rule": correction.rule, "before": correction.before, "after": correction.after}
            for correction in result.corrections
        ]
        label, color = compute_trust(
            claim.raw_value,
            result.verified_value if result.verified_value is not None else claim.raw_value,
            correction_log,
            context.ambiguous_scale,
        )
        return result.verified_value, correction_log, label, color
