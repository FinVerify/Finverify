"""
FinVerifyBench — Error Taxonomy
Grounded in the DVL paper's structured error decomposition:
ε(ŷ, y) = ε_scale + ε_sign + ε_magnitude + ε_residual
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class ErrorCategory(str, Enum):
    """Primary error taxonomy from structured numerical hallucination analysis."""
    SCALE_ERROR       = "scale_error"        # % vs decimal  (0.27 ↔ 27)
    SIGN_ERROR        = "sign_error"          # +5% vs -5%
    MAGNITUDE_ERROR   = "magnitude_error"     # millions vs thousands vs billions
    ARITHMETIC_ERROR  = "arithmetic_error"    # wrong computation
    RATIO_ERROR       = "ratio_error"         # margin/return/yield calculation
    PERCENTAGE_ERROR  = "percentage_error"    # percentage-change calculation
    AGGREGATION_ERROR = "aggregation_error"   # sum/avg/max/min over rows
    UNIT_CONVERSION   = "unit_conversion"     # e.g. $000s vs plain $
    REASONING_ERROR   = "reasoning_error"     # multi-step drift / context loss
    ROUNDING_ERROR    = "rounding_error"
    CONTEXT_CONFUSION = "context_confusion"
    NONE              = "none"                # correct / no error


class ReasoningType(str, Enum):
    PERCENTAGE_CHANGE    = "percentage_change"
    MULTI_STEP_ARITHMETIC = "multi_step_arithmetic"
    RATIO_CALCULATION    = "ratio_calculation"
    AGGREGATION          = "aggregation"
    UNIT_CONVERSION      = "unit_conversion"
    SINGLE_LOOKUP        = "single_lookup"
    COMPARATIVE          = "comparative"
    YOY_CHANGE           = "yoy_change"
    MARGIN_CALCULATION   = "margin_calculation"
    GROWTH_RATE          = "growth_rate"


class Difficulty(str, Enum):
    EASY   = "easy"    # single-step, no unit ambiguity
    MEDIUM = "medium"  # two-step, possible scale ambiguity
    HARD   = "hard"    # multi-step, cross-table, high error risk


class Domain(str, Enum):
    """Extensible — designed for Paper 2 cross-domain expansion."""
    FINANCE   = "finance"
    MEDICAL   = "medical"
    SCIENTIFIC = "scientific"
    LEGAL     = "legal"


class Unit(str, Enum):
    MILLION_USD    = "million_usd"
    BILLION_USD    = "billion_usd"
    THOUSAND_USD   = "thousand_usd"
    USD            = "usd"
    PERCENT        = "percent"
    RATIO          = "ratio"
    SHARES         = "shares"
    BASIS_POINTS   = "basis_points"
    UNITLESS       = "unitless"
    OTHER          = "other"


@dataclass
class DVLRuleTag:
    """Maps a sample to the DVL correction rules that *should* fire on it."""
    scale_correction:     bool = False   # |ŷ| > 100 or < 1 on ratio Q
    sign_correction:      bool = False   # negation keyword + positive prediction
    magnitude_correction: bool = False   # doc unit header mismatch


# Keyword sets mirroring Algorithm 1 in the paper
RATIO_KEYWORDS = {
    "ratio", "margin", "return", "yield", "percent",
    "change", "growth", "loss", "rate", "percentage"
}

NEGATION_KEYWORDS = {
    "decrease", "loss", "declined", "negative",
    "reduction", "fell", "drop", "shrink", "below zero"
}

UNIT_PATTERNS = {
    "in millions":  1e6,
    "in thousands": 1e3,
    "in billions":  1e9,
}


def classify_dvl_rules(question: str, ground_truth: float, unit: str) -> DVLRuleTag:
    """
    Predict which DVL rules *should* fire for a given sample.
    Used during dataset construction to auto-label DVL relevance.
    """
    q_lower = question.lower()
    tag = DVLRuleTag()

    is_ratio_q = any(kw in q_lower for kw in RATIO_KEYWORDS)
    if is_ratio_q:
        if abs(ground_truth) > 100 or (abs(ground_truth) < 1 and ground_truth != 0):
            tag.scale_correction = True

    has_negation = any(kw in q_lower for kw in NEGATION_KEYWORDS)
    if has_negation and ground_truth < 0:
        tag.sign_correction = True

    unit_lower = unit.lower()
    if any(u in unit_lower for u in ["million", "billion", "thousand"]):
        tag.magnitude_correction = True

    return tag


def infer_difficulty(reasoning_types: List[str], error_categories: List[str]) -> str:
    """Heuristic difficulty assignment."""
    hard_signals = {
        ReasoningType.MULTI_STEP_ARITHMETIC.value,
        ReasoningType.YOY_CHANGE.value,
        ReasoningType.MARGIN_CALCULATION.value,
    }
    medium_signals = {
        ReasoningType.PERCENTAGE_CHANGE.value,
        ReasoningType.RATIO_CALCULATION.value,
        ReasoningType.COMPARATIVE.value,
    }
    hard_errors = {
        ErrorCategory.MAGNITUDE_ERROR.value,
        ErrorCategory.REASONING_ERROR.value,
        ErrorCategory.ARITHMETIC_ERROR.value,
    }

    rt_set = set(reasoning_types)
    ec_set = set(error_categories)

    if rt_set & hard_signals or ec_set & hard_errors:
        return Difficulty.HARD.value
    if rt_set & medium_signals:
        return Difficulty.MEDIUM.value
    return Difficulty.EASY.value