"""Shared contracts for rule-based math verification."""

from typing import Protocol

from ...models import Claim, RuleResult, VerificationContext


class Rule(Protocol):
    name: str
    category: str
    enabled: bool

    def evaluate(self, claim: Claim, context: VerificationContext) -> RuleResult:
        """Inspect the current value and optionally return a correction."""


class DisabledRule:
    """Placeholder for future rule families that are disabled by default."""

    def __init__(self, name: str, category: str, reason: str):
        self.name = name
        self.category = category
        self.enabled = False
        self._reason = reason

    def evaluate(self, claim: Claim, context: VerificationContext) -> RuleResult:
        return RuleResult(
            applied=False,
            confidence=0.0,
            reason=self._reason,
            metadata={
                "rule_name": self.name,
                "category": self.category,
                "enabled": self.enabled,
                "stub": True,
            },
        )
