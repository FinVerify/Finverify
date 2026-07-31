"""
Number Parser
=============
Extracts numerical values from raw LLM text output.

Historically this module rolled its own ad hoc parsing
(`text.replace("$", "").replace(",", "")...` + a bare regex). That
implementation could not handle scale words ("2.4 billion", "$2.4B"),
scientific notation, or locale-ambiguous grouping -- it would silently
truncate "$2.4 billion" down to 2.4, discarding nine orders of magnitude.

Numeric parsing now has two stages, kept deliberately separate:

1. Candidate-token scanning (this module): find which substring(s) of a
   block of free text look like numbers. This is inherently fuzzy --
   LLMs restate the question before answering, mention other figures in
   passing, etc.
2. Canonicalization (numeric.canonicalizer): given ONE isolated
   token, deterministically resolve it to a value + unit + currency +
   scale, or reject it outright rather than guess. That module never
   makes a judgment call about which token is "the" answer; it only
   ever judges whether a single given token is unambiguous.

Keeping the fuzzy step and the strict step separate means the strict
step stays auditable: every rejection has a structured reason, and nothing
downstream of canonicalize() is ever a silent guess.
"""

import re
from typing import Optional

from .dvl import RATIO_KEYWORDS
from numeric.canonicalizer import (
    CanonicalizationError,
    CanonicalNumber,
    Unit,
    canonicalize,
)

# ---------------------------------------------------------------------------
# Candidate-token scanning
# ---------------------------------------------------------------------------

# Finds number-like substrings within free text, permissively enough to
# capture currency symbols, grouping commas, parenthesized negatives,
# trailing/leading signs, scale words, and percent signs -- WITHOUT trying
# to validate any of it. Validation is the canonicalizer's job. This regex
# only needs to answer "does this look roughly like a number," so it can
# afford to be generous; anything malformed that it captures will simply
# fail canonicalization and be skipped.
_CANDIDATE_TOKEN_RE = re.compile(
    r"\(?[-+]?(?:[$€£¥₹₩]\s?)?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?\)?[-+]?"
    r"(?:\s?(?:billion|bn|million|mn|thousand|trillion|tn|percent|pct|"
    r"basis\s*points?|bps|percentage\s*points?|pp|[BMKT]))?\s?%?",
    re.IGNORECASE,
)


def _find_candidates(text: str) -> list[str]:
    """Return number-like substrings of `text`, in order of appearance."""
    candidates = [m.group(0).strip() for m in _CANDIDATE_TOKEN_RE.finditer(text)]
    return [c for c in candidates if any(ch.isdigit() for ch in c)]


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract_canonical(text: str, locale: str = "en_US") -> Optional[CanonicalNumber]:
    """
    Extract the predicted number from free text as a structured
    CanonicalNumber (value, unit, currency, scale_applied, ...).

    LLMs often restate the question before giving the answer, so
    candidates are tried starting from the LAST one found in the text
    (matching the historical "take the last number" heuristic) and
    working backwards. A candidate is only skipped if the canonicalizer
    actively rejects it (e.g. it accidentally captured trailing
    punctuation) -- this is a fallback for scanning noise, not a way to
    reintroduce guessing at the canonicalization step itself.

    Returns None if no candidate in the text canonicalizes successfully.
    """
    if not text:
        return None

    candidates = _find_candidates(text)
    for token in reversed(candidates):
        try:
            return canonicalize(token, locale=locale)
        except CanonicalizationError:
            continue
    return None


def extract_number(text: str) -> Optional[float]:
    """
    Extract a number from text, handling financial formatting.

    Backward-compatible with the historical signature: returns a plain
    float (or None), and keeps unit semantics implicit exactly as the
    old implementation did (e.g. "42.5%" -> 42.5, not 0.425) -- callers
    that need the unit, currency, or scale explicitly should call
    extract_canonical() instead.

    Kept returning `float` rather than `Decimal` deliberately: every
    existing caller (clean_llm_output, format_number_display, main.py,
    evaluator.py, financial.py, evals/cross_model_eval.py) already does
    plain float arithmetic and formatting downstream, and the rest of
    the pipeline (formula evaluation, trust scoring) is float-based
    throughout. Converting only this one boundary to Decimal would add
    a conversion at every call site without eliminating float arithmetic
    anywhere else -- it would not buy real precision safety, just
    friction. The Decimal precision this module protects is preserved
    internally by the canonicalizer and exposed in full via
    extract_canonical() for the (currently: DVL) call sites that
    actually reason about representation, not just magnitude.

    NOTE ON BEHAVIOR CHANGE: previously, "(56.78) million" returned
    -56.78 -- the scale word was silently dropped because the old regex
    had no concept of scale words at all. It now correctly returns
    -56780000.0. This is a deliberate correctness fix, not a
    regression; see numeric/canonicalizer.py for the reasoning.
    """
    result = extract_canonical(text)
    if result is None:
        return None
    return float(result.value)


# ---------------------------------------------------------------------------
# LLM output cleaning
# ---------------------------------------------------------------------------

_LLM_ARTIFACTS = [
    "the answer is",
    "therefore",
    "thus",
    "hence",
    "so the answer is",
    "final answer:",
    "result:",
    "= ",
]


def clean_llm_output(raw_text: str) -> tuple[str, Optional[float]]:
    """
    Clean raw LLM text and extract the predicted number.

    Returns
    -------
    cleaned_text : str
        The cleaned text fragment.
    extracted_number : float | None
        The number extracted from it, or None.
    """
    if not raw_text:
        return "", None

    # Take the part after "Answer:" if present
    if "Answer:" in raw_text:
        cleaned = raw_text.split("Answer:")[-1]
    elif "answer:" in raw_text:
        cleaned = raw_text.split("answer:")[-1]
    else:
        cleaned = raw_text

    cleaned = cleaned.strip()

    # Strip common LLM preamble artifacts
    lower = cleaned.lower()
    for artifact in _LLM_ARTIFACTS:
        if lower.startswith(artifact):
            cleaned = cleaned[len(artifact):].strip()
            lower = cleaned.lower()

    number = extract_number(cleaned)
    return cleaned, number


def clean_llm_output_canonical(raw_text: str) -> tuple[str, Optional[CanonicalNumber]]:
    """
    Same preamble-stripping as clean_llm_output(), but returns the full
    structured CanonicalNumber instead of a bare float. Prefer this over
    clean_llm_output() in any new call site that needs to know unit,
    currency, or scale (e.g. DVL's canonical-aware verification path).
    """
    if not raw_text:
        return "", None

    if "Answer:" in raw_text:
        cleaned = raw_text.split("Answer:")[-1]
    elif "answer:" in raw_text:
        cleaned = raw_text.split("answer:")[-1]
    else:
        cleaned = raw_text

    cleaned = cleaned.strip()

    lower = cleaned.lower()
    for artifact in _LLM_ARTIFACTS:
        if lower.startswith(artifact):
            cleaned = cleaned[len(artifact):].strip()
            lower = cleaned.lower()

    return cleaned, extract_canonical(cleaned)


# ---------------------------------------------------------------------------
# Display formatting
# ---------------------------------------------------------------------------

def format_number_display(
    value: Optional[float],
    question: str,
    unit: Optional[Unit] = None,
) -> str:
    """
    Format a number for display in the terminal UI, adapting to context.

    `unit` is optional and backward-compatible: existing 2-argument call
    sites are unaffected. When a caller has already canonicalized the
    source token and knows its unit directly (PERCENT, BASIS_POINT,
    PERCENTAGE_POINT), pass it here to format correctly without
    re-guessing from question phrasing. When `unit` is None or
    Unit.NONE, falls back to the original RATIO_KEYWORDS heuristic.
    """
    if value is None:
        return "N/A"

    if unit is not None and unit != Unit.NONE:
        is_ratio = unit in (Unit.PERCENT, Unit.PERCENTAGE_POINT, Unit.BASIS_POINT)
    else:
        q_lower = question.lower()
        is_ratio = any(kw in q_lower for kw in RATIO_KEYWORDS)

    if is_ratio:
        return f"{value:.2f}%"
    if abs(value) > 1e6:
        return f"{value:,.0f}"
    return f"{value:.4f}"
