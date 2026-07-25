"""Sign correction extracted from the legacy DVL formatting pass."""

from app.dvl import _sign

from ...models import Claim, RuleResult, VerificationContext


class SignRule:
    """
    Preserve the original DVL sign-flip heuristic exactly.

    The legacy intent is to flip sign only when the absolute magnitude already
    matches the target within tolerance and the sign alone is wrong.
    """

    name = "sign"
    category = "formatting"
    enabled = True

    def evaluate(self, claim: Claim, context: VerificationContext) -> RuleResult:
        value = context.current_value
        actual = claim.actual_value
        if value is None or actual is None:
            return RuleResult(applied=False, reason="Missing value or actual for sign evaluation")
        if actual == 0:
            return RuleResult(applied=False, reason="Legacy DVL skips sign correction for zero actuals")

        if abs(abs(value) - abs(actual)) / abs(actual) <= 0.05 and _sign(value) != _sign(actual):
            corrected = -value
            return RuleResult(
                applied=True,
                corrected_value=corrected,
                reason="Applied sign_corrected",
                metadata={
                    "correction": {
                        "rule": "sign_corrected",
                        "before": value,
                        "after": corrected,
                    },
                },
            )
        return RuleResult(applied=False, reason="No sign correction applied")
