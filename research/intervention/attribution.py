"""Rule-level attribution without changing aggregate example scoring."""

from dataclasses import asdict
from typing import Iterable, Mapping

from .blind_dvl import Correction


def correction_dicts(corrections: Iterable[Correction]) -> list[dict]:
    return [asdict(item) for item in corrections]


def attribute_transition(output: Mapping, baseline_correct: bool, post_correct: bool) -> list[dict]:
    transition = ("C" if baseline_correct else "I") + "→" + ("C" if post_correct else "I")
    return [{"rule": rule, "transition": transition} for rule in output.get("fired_rules", ())]
