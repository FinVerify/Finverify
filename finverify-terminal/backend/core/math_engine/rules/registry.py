"""Rule registry for the modular math engine."""

from ...models import Claim, Correction, RuleTrace, VerificationContext
from .base import DisabledRule, Rule
from .magnitude import MagnitudeRule
from .scale import ScaleRule
from .sign import SignRule


class RuleRegistry:
    """Apply rules in the same sequence as the legacy DVL pipeline."""

    CATEGORY_ORDER = ("formatting", "normalisation", "consistency")

    def __init__(self, categories: dict[str, list[Rule]] | None = None):
        self.categories = categories or {
            "formatting": [ScaleRule(), SignRule(), MagnitudeRule()],
            "normalisation": [
                DisabledRule(
                    name="percentage_normalisation",
                    category="normalisation",
                    reason="TODO: normalisation rules are placeholders in this refactor",
                ),
            ],
            "consistency": [
                DisabledRule(
                    name="consistency_check",
                    category="consistency",
                    reason="TODO: consistency rules are placeholders in this refactor",
                ),
            ],
        }

    def apply(self, claim: Claim, context: VerificationContext) -> tuple[list[Correction], RuleTrace]:
        corrections: list[Correction] = []
        trace = RuleTrace()

        for category in self.CATEGORY_ORDER:
            for rule in self.categories.get(category, []):
                result = rule.evaluate(claim, context)
                metadata = dict(result.metadata)
                metadata.setdefault("rule_name", getattr(rule, "name", rule.__class__.__name__))
                metadata.setdefault("category", getattr(rule, "category", category))
                result.metadata = metadata
                trace.results.append(result)

                if result.applied and result.corrected_value is not None:
                    correction = metadata.get("correction") or {
                        "rule": metadata["rule_name"],
                        "before": context.current_value,
                        "after": result.corrected_value,
                    }
                    corrections.append(Correction(**correction))
                    context.current_value = result.corrected_value

        return corrections, trace
