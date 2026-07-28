"""
FinVerifyBench — Error Taxonomy (Phase 2 Revised)
Grounded in DVL paper: ε(ŷ,y) = ε_scale + ε_sign + ε_magnitude + ε_residual

Phase 2 Audit changes vs v1:
  - Added: EXTRACTION_ERROR (pre-fine-tuning failure mode, 0% post-FT but present in raw models)
  - Added: ROUNDING_ERROR  (CoT computational drift — 71% of CoT failures)
  - Added: CONTEXT_CONFUSION (cross-step context loss — 29% of CoT failures)
  - Merged: percentage_error INTO scale_error (subtype) — kept separate for granularity
  - Hierarchy: MAGNITUDE_ERROR is parent of UNIT_CONVERSION (unit confusion is magnitude class)
  - Kept: all original 9 + 3 new = 12 leaf categories under 4 root groups
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


# ─── Root-level error groups (mirrors DVL decomposition) ─────────────────────

class ErrorGroup(str, Enum):
    """4 root groups from paper's decomposition formula."""
    SCALE     = "scale"      # ε_scale
    SIGN      = "sign"       # ε_sign
    MAGNITUDE = "magnitude"  # ε_magnitude
    RESIDUAL  = "residual"   # ε_residual (reasoning / drift)


# ─── Leaf error categories ────────────────────────────────────────────────────

class ErrorCategory(str, Enum):
    # SCALE group
    SCALE_ERROR       = "scale_error"       # 0.27 ↔ 27  (% vs decimal)
    PERCENTAGE_ERROR  = "percentage_error"  # wrong % calculation (CAGR, YoY)

    # SIGN group
    SIGN_ERROR        = "sign_error"        # +5% ↔ -5%

    # MAGNITUDE group
    MAGNITUDE_ERROR   = "magnitude_error"   # millions vs thousands vs billions
    UNIT_CONVERSION   = "unit_conversion"   # cross-unit arithmetic ($M → $B)
    AGGREGATION_ERROR = "aggregation_error" # wrong sum/avg/max over rows

    # RESIDUAL group
    ARITHMETIC_ERROR  = "arithmetic_error"  # wrong computation (correct operands)
    RATIO_ERROR       = "ratio_error"       # margin/ROE/ROA/P-E formula error
    REASONING_ERROR   = "reasoning_error"   # multi-step drift / context loss
    ROUNDING_ERROR    = "rounding_error"    # precision lost at step boundaries (CoT drift)
    CONTEXT_CONFUSION = "context_confusion" # wrong operand picked from context
    EXTRACTION_ERROR  = "extraction_error"  # pre-FT: fails to parse number from context

    NONE              = "none"              # correct / no error


ERROR_GROUP_MAP = {
    ErrorCategory.SCALE_ERROR:       ErrorGroup.SCALE,
    ErrorCategory.PERCENTAGE_ERROR:  ErrorGroup.SCALE,
    ErrorCategory.SIGN_ERROR:        ErrorGroup.SIGN,
    ErrorCategory.MAGNITUDE_ERROR:   ErrorGroup.MAGNITUDE,
    ErrorCategory.UNIT_CONVERSION:   ErrorGroup.MAGNITUDE,
    ErrorCategory.AGGREGATION_ERROR: ErrorGroup.MAGNITUDE,
    ErrorCategory.ARITHMETIC_ERROR:  ErrorGroup.RESIDUAL,
    ErrorCategory.RATIO_ERROR:       ErrorGroup.RESIDUAL,
    ErrorCategory.REASONING_ERROR:   ErrorGroup.RESIDUAL,
    ErrorCategory.ROUNDING_ERROR:    ErrorGroup.RESIDUAL,
    ErrorCategory.CONTEXT_CONFUSION: ErrorGroup.RESIDUAL,
    ErrorCategory.EXTRACTION_ERROR:  ErrorGroup.RESIDUAL,
    ErrorCategory.NONE:              ErrorGroup.RESIDUAL,
}


class ReasoningType(str, Enum):
    PERCENTAGE_CHANGE     = "percentage_change"
    MULTI_STEP_ARITHMETIC = "multi_step_arithmetic"
    RATIO_CALCULATION     = "ratio_calculation"
    AGGREGATION           = "aggregation"
    UNIT_CONVERSION       = "unit_conversion"
    SINGLE_LOOKUP         = "single_lookup"
    COMPARATIVE           = "comparative"
    YOY_CHANGE            = "yoy_change"
    MARGIN_CALCULATION    = "margin_calculation"
    GROWTH_RATE           = "growth_rate"


class Difficulty(str, Enum):
    EASY   = "easy"
    MEDIUM = "medium"
    HARD   = "hard"


class Domain(str, Enum):
    """Extensible for Paper 2 cross-domain expansion."""
    FINANCE    = "finance"
    MEDICAL    = "medical"
    SCIENTIFIC = "scientific"
    LEGAL      = "legal"


class Unit(str, Enum):
    MILLION_USD   = "million_usd"
    BILLION_USD   = "billion_usd"
    THOUSAND_USD  = "thousand_usd"
    USD           = "usd"
    PERCENT       = "percent"
    RATIO         = "ratio"
    SHARES        = "shares"
    BASIS_POINTS  = "basis_points"
    UNITLESS      = "unitless"
    OTHER         = "other"


class SourceType(str, Enum):
    """Phase 3: document source types."""
    SEC_10K        = "sec_10k"
    SEC_10Q        = "sec_10q"
    EARNINGS_RELEASE = "earnings_release"
    INVESTOR_PRES  = "investor_presentation"
    FINANCIAL_TABLE = "financial_table"
    CASH_FLOW      = "cash_flow_statement"
    BALANCE_SHEET  = "balance_sheet"
    INCOME_STMT    = "income_statement"
    SYNTHETIC      = "synthetic"


# ─── DVL rule mapping ─────────────────────────────────────────────────────────

RATIO_KEYWORDS = {
    "ratio", "margin", "return", "yield", "percent",
    "change", "growth", "loss", "rate", "percentage",
    "cagr", "roe", "roa", "eps", "pe", "p/e", "ebitda"
}

NEGATION_KEYWORDS = {
    "decrease", "loss", "declined", "negative",
    "reduction", "fell", "drop", "shrink", "below zero",
    "impairment", "write-down", "write-off", "deficit"
}

UNIT_PATTERNS = {
    "in millions":  1e6,
    "in thousands": 1e3,
    "in billions":  1e9,
    "in $000s":     1e3,
    "in $millions": 1e6,
    "in $billions": 1e9,
}


@dataclass
class DVLRuleTag:
    scale_correction:     bool = False
    sign_correction:      bool = False
    magnitude_correction: bool = False


def classify_dvl_rules(question: str, ground_truth: float, unit: str) -> DVLRuleTag:
    import math
    q_lower = question.lower()
    tag = DVLRuleTag()
    if math.isnan(ground_truth) or math.isinf(ground_truth):
        return tag
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


def infer_difficulty(reasoning_types: list, error_categories: list) -> str:
    hard_rt = {
        ReasoningType.MULTI_STEP_ARITHMETIC.value,
        ReasoningType.YOY_CHANGE.value,
        ReasoningType.GROWTH_RATE.value,
    }
    medium_rt = {
        ReasoningType.PERCENTAGE_CHANGE.value,
        ReasoningType.RATIO_CALCULATION.value,
        ReasoningType.MARGIN_CALCULATION.value,
        ReasoningType.COMPARATIVE.value,
    }
    hard_ec = {
        ErrorCategory.MAGNITUDE_ERROR.value,
        ErrorCategory.REASONING_ERROR.value,
        ErrorCategory.ARITHMETIC_ERROR.value,
        ErrorCategory.CONTEXT_CONFUSION.value,
        ErrorCategory.UNIT_CONVERSION.value,
    }
    rt_set = set(reasoning_types)
    ec_set = set(error_categories)
    if (rt_set & hard_rt) or (ec_set & hard_ec and len(ec_set) > 1):
        return Difficulty.HARD.value
    if rt_set & medium_rt:
        return Difficulty.MEDIUM.value
    return Difficulty.EASY.value
