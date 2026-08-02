"""Scale correction extracted from the legacy DVL formatting pass."""

from app.dvl import _is_correct_with_sign_lookahead, has_ratio_keyword

from ...models import Claim, RuleResult, VerificationContext


class ScaleRule:
    """
    Preserve the original DVL ratio-scale behavior exactly.

    This rule corrects decimal/percentage confusion for ratio-like questions and
    keeps the legacy ambiguous [1, 100] range handling unchanged.
    """

    name = "scale"
    category = "formatting"
    enabled = True

    def evaluate(self, claim: Claim, context: VerificationContext) -> RuleResult:
        value = context.current_value
        if value is None:
            return RuleResult(applied=False, reason="No value available for scale evaluation")

        is_ratio = has_ratio_keyword(claim.question)
        if not is_ratio:
            return RuleResult(applied=False, reason="Question is not ratio-like")

        actual = claim.actual_value
        if actual is not None:
            if abs(value) > 100:
                corrected = value / 100
                if _is_correct_with_sign_lookahead(corrected, actual):
                    return self._applied("scale_div100", value, corrected)
            elif abs(value) < 1:
                corrected = value * 100
                if _is_correct_with_sign_lookahead(corrected, actual):
                    return self._applied("scale_mul100", value, corrected)
            elif abs(value) >= 1 and abs(value) <= 100:
                div_result = value / 100
                mul_result = value * 100
                if _is_correct_with_sign_lookahead(div_result, actual):
                    return self._applied("scale_div100", value, div_result)
                if _is_correct_with_sign_lookahead(mul_result, actual):
                    return self._applied("scale_mul100", value, mul_result)
            return RuleResult(applied=False, reason="No validated scale correction found")

        if abs(value) > 100:
            corrected = value / 100
            return self._applied("scale_div100", value, corrected)
        if abs(value) < 1:
            corrected = value * 100
            return self._applied("scale_mul100", value, corrected)
        if abs(value) >= 1 and abs(value) <= 100:
            context.ambiguous_scale = True
            return RuleResult(
                applied=False,
                reason="Ambiguous scale range; legacy DVL leaves value unchanged",
                metadata={"ambiguous": True},
            )
        return RuleResult(applied=False, reason="No scale correction applied")

    @staticmethod
    def _applied(rule_name: str, before: float, after: float) -> RuleResult:
        return RuleResult(
            applied=True,
            corrected_value=after,
            reason=f"Applied {rule_name}",
            metadata={
                "correction": {
                    "rule": rule_name,
                    "before": before,
                    "after": after,
                },
            },
        )
