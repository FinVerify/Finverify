"""Magnitude correction extracted from the legacy DVL formatting pass."""

from app.dvl import RATIO_KEYWORDS, is_correct

from ...models import Claim, RuleResult, VerificationContext


class MagnitudeRule:
    """
    Preserve the original DVL denomination correction loop exactly.

    The legacy intent is to try a fixed list of magnitude factors in order and
    stop at the first candidate that validates.
    """

    name = "magnitude"
    category = "formatting"
    enabled = True

    _MAGNITUDE_FACTORS = [10, 100, 1000, 0.1, 0.01, 0.001]

    def evaluate(self, claim: Claim, context: VerificationContext) -> RuleResult:
        value = context.current_value
        if value is None:
            return RuleResult(applied=False, reason="No value available for magnitude evaluation")

        actual = claim.actual_value
        is_ratio = any(keyword in claim.question.lower() for keyword in RATIO_KEYWORDS)

        for factor in self._MAGNITUDE_FACTORS:
            corrected = value * factor
            if actual is not None:
                if is_correct(corrected, actual):
                    return RuleResult(
                        applied=True,
                        corrected_value=corrected,
                        reason=f"Applied magnitude_x{factor}",
                        metadata={
                            "correction": {
                                "rule": f"magnitude_x{factor}",
                                "before": value,
                                "after": corrected,
                            },
                        },
                    )
            elif is_ratio:
                if 0.001 < abs(corrected) < 1e9 and (abs(value) < 0.001 or abs(value) > 1e9):
                    return RuleResult(
                        applied=True,
                        corrected_value=corrected,
                        reason=f"Applied magnitude_x{factor}",
                        metadata={
                            "correction": {
                                "rule": f"magnitude_x{factor}",
                                "before": value,
                                "after": corrected,
                            },
                        },
                    )

        return RuleResult(applied=False, reason="No magnitude correction applied")
