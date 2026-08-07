"""Independent blind DVL path; it has no reference-data dependency."""

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class BlindInterventionInput:
    example_id: str
    question: str
    context: str
    raw_generation: str
    parsed_prediction: Optional[float]


@dataclass(frozen=True)
class Correction:
    rule: str
    before: Optional[float]
    after: Optional[float]


@dataclass(frozen=True)
class BlindInterventionOutput:
    example_id: str
    verified_value: Optional[float]
    correction_log: tuple[Correction, ...]
    fired_rules: tuple[str, ...]
    trust_label: str
    trust_color: str


_RATIO_KEYWORDS = ("ratio", "margin", "return", "yield", "growth", "change", "increase", "decrease", "percent", "percentage", "rate", "loss")


def _ratio_question(question: str) -> bool:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", question).replace("_", " ").replace("-", " ").lower()
    return any(token.startswith(keyword) for token in normalized.split() for keyword in _RATIO_KEYWORDS)


def _trust(raw: float, verified: float, logs: list[Correction], ambiguous: bool) -> tuple[str, str]:
    if not logs:
        return "HIGH", "#00ff88"
    if ambiguous:
        return "LOW", "#f87171"
    delta = abs(verified - raw) / (abs(raw) + 1e-10)
    if delta < 0.05:
        return "HIGH", "#00ff88"
    if delta < 0.5:
        return "MEDIUM", "#fbbf24"
    return "LOW", "#f87171"


def blind_verify(input: BlindInterventionInput) -> BlindInterventionOutput:
    """Apply the frozen reference-free scale/magnitude behavior.

    The frozen sign rule requires a reference value, so it is structurally
    inactive in this study and is not invented here.
    """
    value = input.parsed_prediction
    logs: list[Correction] = []
    ambiguous = False
    if value is not None and _ratio_question(input.question):
        if abs(value) > 100:
            after = value / 100
            logs.append(Correction("scale_div100", value, after))
            value = after
        elif abs(value) < 1:
            after = value * 100
            logs.append(Correction("scale_mul100", value, after))
            value = after
        else:
            ambiguous = True

        # This is the existing blind magnitude branch. It is intentionally
        # conservative and only acts on clearly extreme ratio values.
        for factor in (10, 100, 1000, 0.1, 0.01, 0.001):
            if abs(value) < 0.001 or abs(value) > 1e9:
                after = value * factor
                if 0.001 < abs(after) < 1e9:
                    logs.append(Correction(f"magnitude_x{factor}", value, after))
                    value = after
                    break
    if input.parsed_prediction is None:
        label, color = "HIGH", "#00ff88"
    else:
        label, color = _trust(input.parsed_prediction, value, logs, ambiguous)
    fired = tuple(item.rule for item in logs if item.before != item.after)
    return BlindInterventionOutput(input.example_id, value, tuple(logs), fired, label, color)
