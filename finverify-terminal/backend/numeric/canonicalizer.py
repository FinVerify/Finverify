"""
numeric.canonicalizer
============================
Deterministic numeric canonicalization module.

Converts a single numeric TOKEN (already isolated from surrounding prose)
into a structured, unambiguous representation. This is the shared,
single source of truth for numeric parsing across the FinVerify Terminal
backend (app.parser, app.dvl). It replaces the ad hoc `float(text.replace(...))`
patterns that previously existed independently in app/parser.py and were
never able to handle scale words ("2.4 billion"), scientific notation, or
locale-ambiguous grouping.

NOTE ON PACKAGE PLACEMENT: this lives in a standalone top-level `numeric`
package rather than under `core.numeric`, deliberately. `app.dvl` needs to
import this module, and `core/__init__.py` eagerly imports the whole
verification engine graph (core.engine -> core.math_engine ->
core.math_engine.engine -> `from app.dvl import compute_trust`). If this
module were nested under `core`, importing it from app/dvl.py would
trigger `core/__init__.py`, which would in turn try to import app.dvl
while it's still mid-import -- a circular import. Living outside `core`
avoids that entirely, since neither `app` nor `core` needs to already be
initialized to import this module.

Design principles
-----------------
1. Never guess. Any input that admits more than one reasonable reading is
   REJECTED with a structured reason code, not silently resolved by
   precedence or heuristic.
2. Never conflate representation with semantics. "12%" canonicalizes to
   value=Decimal(12), unit=PERCENT -- NOT value=Decimal("0.12"). Whether a
   caller needs to divide by 100 is a semantic decision that belongs
   downstream, with context this module does not have. This is the same
   distinction DVL's scale-correction step exists to resolve; keeping it
   literal here means DVL consults `unit` instead of re-guessing from
   question keywords.
3. Decimal, never float. Financial values must not pick up binary
   floating-point rounding error anywhere in the pipeline.
4. This module parses ONE token. Extracting "the" number out of a paragraph
   of free text is a different, fuzzier problem (see app.parser's
   candidate-token scanning) and is out of scope here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Public data model
# ---------------------------------------------------------------------------

class Unit(Enum):
    NONE = "none"
    PERCENT = "percent"
    PERCENTAGE_POINT = "percentage_point"
    BASIS_POINT = "basis_point"


class RejectReason(Enum):
    EMPTY_INPUT = "empty_input"
    NO_DIGITS = "no_digits"
    MULTIPLE_DECIMAL_POINTS = "multiple_decimal_points"
    MALFORMED_GROUPING = "malformed_grouping"
    CONTRADICTORY_SIGN = "contradictory_sign"
    MULTIPLE_SCALE_WORDS = "multiple_scale_words"
    MULTIPLE_UNIT_MARKERS = "multiple_unit_markers"
    SCALE_UNIT_CONFLICT = "scale_unit_conflict"
    CONFLICTING_CURRENCY = "conflicting_currency"
    UNRECOGNIZED_CHARACTERS = "unrecognized_characters"
    MALFORMED_SCIENTIFIC_NOTATION = "malformed_scientific_notation"
    UNSUPPORTED_LOCALE = "unsupported_locale"


class CanonicalizationError(Exception):
    """Raised when a token cannot be canonicalized deterministically."""

    def __init__(self, reason: RejectReason, detail: str, raw_input: str):
        self.reason = reason
        self.detail = detail
        self.raw_input = raw_input
        super().__init__(f"[{reason.value}] {detail} (input={raw_input!r})")


@dataclass
class CanonicalNumber:
    raw_input: str
    value: Decimal
    unit: Unit = Unit.NONE
    currency: Optional[str] = None
    scale_applied: Optional[str] = None
    is_negative: bool = False
    precision_digits: int = 0
    warnings: list[str] = field(default_factory=list)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"CanonicalNumber(value={self.value}, unit={self.unit.value}, "
            f"currency={self.currency}, scale={self.scale_applied}, "
            f"warnings={self.warnings})"
        )


# ---------------------------------------------------------------------------
# Static tables
# ---------------------------------------------------------------------------

_CURRENCY_SYMBOLS = {
    "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY",
    "₹": "INR", "₩": "KRW", "₽": "RUB", "₺": "TRY",
}
_CURRENCY_CODES = {"USD", "EUR", "GBP", "JPY", "INR", "KRW", "RUB", "TRY",
                   "CNY", "CHF", "AUD", "CAD"}

# order matters only for regex alternation length (longest first per group)
_SCALE_WORDS = {
    "trillion": Decimal("1e12"), "tn": Decimal("1e12"), "t": Decimal("1e12"),
    "billion": Decimal("1e9"), "bn": Decimal("1e9"), "b": Decimal("1e9"),
    "million": Decimal("1e6"), "mn": Decimal("1e6"), "m": Decimal("1e6"),
    "thousand": Decimal("1e3"), "k": Decimal("1e3"),
}
# single-letter tokens require immediate attachment or a single preceding
# space to avoid colliding with ordinary word characters
_SINGLE_LETTER_SCALE = {"t", "b", "m", "k"}

# PHASE 3C.1: public, read-only view of the scale-word -> multiplier table.
# Exists so that callers outside this module (currently app.parser's
# context-driven scale-bridge resolver) can look up "what multiplier does
# CanonicalNumber.scale_applied correspond to" without re-declaring their
# own copy of this table. This is the "smallest reusable abstraction"
# referenced in the Phase 3C.1/3D/3E engineering notes: it adds a lookup,
# not a second implementation of scale parsing.
SCALE_WORD_MULTIPLIERS: dict[str, Decimal] = dict(_SCALE_WORDS)

_PERCENT_WORDS = {"%", "percent", "pct"}
_BPS_WORDS = {"bps", "basis point", "basis points"}
_PP_WORDS = {"pp", "percentage point", "percentage points"}

_UNICODE_MINUS = "\u2212"  # −
_NBSP = "\u00a0"

_CORE_NUMBER_RE = re.compile(r"^\d+(\.\d+)?$")
_SCI_NOTATION_RE = re.compile(r"^(\d+(?:\.\d+)?)[eE]([+-]?\d+)$")


# ---------------------------------------------------------------------------
# Core entry point
# ---------------------------------------------------------------------------

def canonicalize(raw_input: str, locale: str = "en_US") -> CanonicalNumber:
    """
    Canonicalize a single numeric token.

    Parameters
    ----------
    raw_input : str
        The token to parse, e.g. "$2.4B", "(1,234.56)", "12.5%".
    locale : str
        "en_US" (comma=thousands, period=decimal) or
        "eu_EU" (period=thousands, comma=decimal). Must be explicit;
        this function never auto-detects locale.

    Returns
    -------
    CanonicalNumber

    Raises
    ------
    CanonicalizationError
        If the input is empty, malformed, or ambiguous in a way that
        cannot be resolved without guessing.
    """
    if locale not in ("en_US", "eu_EU"):
        raise CanonicalizationError(
            RejectReason.UNSUPPORTED_LOCALE,
            f"locale must be 'en_US' or 'eu_EU', got {locale!r}",
            raw_input,
        )

    if raw_input is None or raw_input.strip() == "":
        raise CanonicalizationError(
            RejectReason.EMPTY_INPUT, "input is empty or whitespace-only", raw_input
        )

    warnings: list[str] = []
    text = _normalize_unicode(raw_input, warnings)

    # Sign must be resolved before parens: "-(1234)" needs to see the
    # leading '-' before the parens are stripped, so the contradiction
    # (double negation) can be detected.
    text, sign_char = _extract_sign(text, raw_input, warnings)

    text, paren_negative = _strip_parentheses(text)

    if paren_negative and sign_char is not None:
        raise CanonicalizationError(
            RejectReason.CONTRADICTORY_SIGN,
            "an explicit sign was combined with a parenthesized (already-signed) "
            "value",
            raw_input,
        )
    sign_negative = sign_char == "-"

    # Currency is extracted on the now sign/paren-free magnitude text, so
    # it is found correctly regardless of whether it was wrapped or signed.
    text, currency = _extract_currency(text, raw_input)

    # Scale word is resolved before the unit marker so that a scale word
    # trailing a unit marker (e.g. "12.4% billion") is still caught as a
    # conflict rather than silently ignored because it wasn't anchored
    # at the string's end.
    text, scale_word, scale_multiplier = _extract_scale(text, raw_input)

    text, unit = _extract_unit(text, raw_input)

    if scale_word and unit != Unit.NONE:
        raise CanonicalizationError(
            RejectReason.SCALE_UNIT_CONFLICT,
            f"scale word {scale_word!r} combined with unit {unit.value!r} is not "
            f"a coherent financial quantity",
            raw_input,
        )

    text = text.strip()
    if text == "":
        raise CanonicalizationError(
            RejectReason.NO_DIGITS, "no digits remained after stripping tokens", raw_input
        )
    if not any(ch.isdigit() for ch in text):
        raise CanonicalizationError(
            RejectReason.NO_DIGITS,
            f"no digit characters found in remaining token {text!r}",
            raw_input,
        )

    # Scientific notation branch
    sci_match = _SCI_NOTATION_RE.match(text)
    if sci_match:
        mantissa, exponent = sci_match.groups()
        core_str = mantissa
        try:
            exp_val = int(exponent)
        except ValueError:
            raise CanonicalizationError(
                RejectReason.MALFORMED_SCIENTIFIC_NOTATION,
                f"could not parse exponent {exponent!r}",
                raw_input,
            )
        sci_exponent = Decimal(10) ** exp_val
    else:
        core_str = text
        sci_exponent = Decimal(1)

    core_str, precision_digits = _resolve_separators(core_str, raw_input, locale)

    if not _CORE_NUMBER_RE.match(core_str):
        raise CanonicalizationError(
            RejectReason.UNRECOGNIZED_CHARACTERS,
            f"residual token {core_str!r} is not a valid plain number",
            raw_input,
        )

    try:
        value = Decimal(core_str)
    except InvalidOperation:
        raise CanonicalizationError(
            RejectReason.NO_DIGITS, f"could not convert {core_str!r} to Decimal", raw_input
        )

    value = value * sci_exponent * scale_multiplier

    is_negative = paren_negative or sign_negative
    if is_negative:
        value = -value

    return CanonicalNumber(
        raw_input=raw_input,
        value=value,
        unit=unit,
        currency=currency,
        scale_applied=scale_word,
        is_negative=is_negative,
        precision_digits=precision_digits,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Stage implementations
# ---------------------------------------------------------------------------

def _normalize_unicode(text: str, warnings: list[str]) -> str:
    if _UNICODE_MINUS in text:
        text = text.replace(_UNICODE_MINUS, "-")
        warnings.append("unicode minus sign normalized to ASCII '-'")
    if _NBSP in text:
        text = text.replace(_NBSP, " ")
        warnings.append("non-breaking space normalized to ASCII space")
    return text.strip()


def _extract_currency(text: str, raw_input: str) -> tuple[str, Optional[str]]:
    found: list[str] = []

    # symbol at start
    stripped = text.strip()
    for sym, code in _CURRENCY_SYMBOLS.items():
        if stripped.startswith(sym):
            found.append(code)
            stripped = stripped[len(sym):]
            break
        if stripped.endswith(sym):
            found.append(code)
            stripped = stripped[: -len(sym)]
            break

    # ISO code at start or end (word boundary)
    code_match = re.match(r"^([A-Za-z]{3})\b", stripped.strip())
    if code_match and code_match.group(1).upper() in _CURRENCY_CODES:
        found.append(code_match.group(1).upper())
        stripped = stripped.strip()[len(code_match.group(1)):]
    else:
        code_match_end = re.search(r"\b([A-Za-z]{3})$", stripped.strip())
        if code_match_end and code_match_end.group(1).upper() in _CURRENCY_CODES:
            found.append(code_match_end.group(1).upper())
            stripped = stripped.strip()[: -len(code_match_end.group(1))]

    unique = set(found)
    if len(unique) > 1:
        raise CanonicalizationError(
            RejectReason.CONFLICTING_CURRENCY,
            f"multiple conflicting currency indicators found: {sorted(unique)}",
            raw_input,
        )

    currency = found[0] if found else None
    return stripped.strip(), currency


def _strip_parentheses(text: str) -> tuple[str, bool]:
    """
    Strip a leading parenthesized negative magnitude.

    Handles both the simple case where parens wrap the entire token
    ("(1234.56)") and the case where a trailing modifier follows the
    closing paren ("(56.78) million") -- common in earnings-call
    transcripts and filings. Only a single, non-nested leading paren
    group is recognized; anything more exotic is left for downstream
    stages to reject as unrecognized rather than guessed at here.
    """
    t = text.strip()
    if not t.startswith("("):
        return t, False

    close_idx = t.find(")")
    if close_idx == -1:
        # Unmatched opening paren -- not our job to guess; let the
        # downstream numeric-core validation reject it.
        return t, False

    inner = t[1:close_idx].strip()
    rest = t[close_idx + 1:].strip()
    combined = f"{inner} {rest}".strip() if rest else inner
    return combined, True


def _extract_sign(
    text: str, raw_input: str, warnings: list[str]
) -> tuple[str, Optional[str]]:
    """Extract a single leading or trailing +/- sign. Returns (remainder, sign_char)."""
    t = text.strip()
    leading = t[:1] if t[:1] in "+-" else None
    trailing = t[-1:] if t[-1:] in "+-" else None

    if leading and trailing:
        raise CanonicalizationError(
            RejectReason.CONTRADICTORY_SIGN,
            "sign markers found at both start and end of token",
            raw_input,
        )

    sign_char = leading or trailing
    if sign_char is None:
        return t, None

    if leading:
        t = t[1:]
    else:
        t = t[:-1]
        warnings.append("trailing sign notation used")

    return t.strip(), sign_char


def _extract_unit(text: str, raw_input: str) -> tuple[str, Unit]:
    t = text.strip()
    lower = t.lower()

    matches: list[Unit] = []
    remainder = t

    # percent symbol / words (longest words first)
    for word in sorted(_PERCENT_WORDS, key=len, reverse=True):
        pattern = re.escape(word)
        if word == "%":
            regex = re.compile(pattern + r"$")
        else:
            regex = re.compile(r"\s*" + pattern + r"$", re.IGNORECASE)
        if regex.search(lower):
            matches.append(Unit.PERCENT)
            remainder = regex.sub("", remainder, count=1)
            lower = remainder.lower()
            break

    for word in sorted(_BPS_WORDS, key=len, reverse=True):
        regex = re.compile(r"\s*" + re.escape(word) + r"$", re.IGNORECASE)
        if regex.search(lower):
            matches.append(Unit.BASIS_POINT)
            remainder = regex.sub("", remainder, count=1)
            lower = remainder.lower()
            break

    for word in sorted(_PP_WORDS, key=len, reverse=True):
        regex = re.compile(r"\s*" + re.escape(word) + r"$", re.IGNORECASE)
        if regex.search(lower):
            matches.append(Unit.PERCENTAGE_POINT)
            remainder = regex.sub("", remainder, count=1)
            lower = remainder.lower()
            break

    unique = set(matches)
    if len(unique) > 1:
        raise CanonicalizationError(
            RejectReason.MULTIPLE_UNIT_MARKERS,
            f"multiple conflicting unit markers found: {sorted(u.value for u in unique)}",
            raw_input,
        )

    unit = matches[0] if matches else Unit.NONE
    return remainder.strip(), unit


def _extract_scale(
    text: str, raw_input: str
) -> tuple[str, Optional[str], Decimal]:
    t = text.strip()
    lower = t.lower()

    candidates = sorted(_SCALE_WORDS.keys(), key=len, reverse=True)
    found: list[str] = []
    remainder = t

    for word in candidates:
        if word in _SINGLE_LETTER_SCALE:
            # require immediate attachment to a digit, or a single
            # preceding space -- never a bare/standalone letter elsewhere
            regex = re.compile(r"(?<=[\d])" + word + r"$", re.IGNORECASE)
            regex_spaced = re.compile(r"\s" + word + r"$", re.IGNORECASE)
            m = regex.search(lower) or regex_spaced.search(lower)
        else:
            regex = re.compile(r"(?:\s|(?<=\d))" + word + r"$", re.IGNORECASE)
            m = regex.search(lower)

        if m:
            found.append(word)
            remainder = remainder[: m.start()]
            lower = remainder.lower()
            break  # longest-match-first; stop at first hit per pass

    # second pass to detect a *second* scale word stacked behind the first
    # (e.g. "2.4 billion million") which must be rejected, not compounded
    for word in candidates:
        if word in found:
            continue
        if word in _SINGLE_LETTER_SCALE:
            regex = re.compile(r"(?<=[\d])" + word + r"$", re.IGNORECASE)
            regex_spaced = re.compile(r"\s" + word + r"$", re.IGNORECASE)
            m = regex.search(lower) or regex_spaced.search(lower)
        else:
            regex = re.compile(r"(?:\s|(?<=\d))" + word + r"$", re.IGNORECASE)
            m = regex.search(lower)
        if m:
            found.append(word)

    if len(found) > 1:
        raise CanonicalizationError(
            RejectReason.MULTIPLE_SCALE_WORDS,
            f"multiple scale words found: {found}",
            raw_input,
        )

    if not found:
        return remainder.strip(), None, Decimal(1)

    scale_word = found[0]
    return remainder.strip(), scale_word, _SCALE_WORDS[scale_word]


def _resolve_separators(core: str, raw_input: str, locale: str) -> tuple[str, int]:
    """
    Resolve comma/period grouping vs. decimal separator per explicit locale.
    Returns (plain_decimal_string, precision_digits).
    """
    if locale == "en_US":
        thousands_sep, decimal_sep = ",", "."
    else:  # eu_EU
        thousands_sep, decimal_sep = ".", ","

    has_thousands = thousands_sep in core
    has_decimal = decimal_sep in core

    if has_decimal:
        parts = core.split(decimal_sep)
        if len(parts) > 2:
            raise CanonicalizationError(
                RejectReason.MULTIPLE_DECIMAL_POINTS,
                f"more than one decimal separator found in {core!r}",
                raw_input,
            )
        int_part, frac_part = parts
        precision_digits = len(frac_part)
    else:
        int_part, frac_part = core, ""
        precision_digits = 0

    if has_thousands:
        groups = int_part.split(thousands_sep)
        if len(groups) < 2 or not groups[0] or not all(g.isdigit() for g in groups):
            raise CanonicalizationError(
                RejectReason.MALFORMED_GROUPING,
                f"malformed thousands grouping in {core!r}",
                raw_input,
            )
        if len(groups[0]) > 3 or any(len(g) != 3 for g in groups[1:]):
            raise CanonicalizationError(
                RejectReason.MALFORMED_GROUPING,
                f"thousands groups must be exactly 3 digits (except the leading "
                f"group) in {core!r}",
                raw_input,
            )
        int_part = "".join(groups)

    if not int_part.isdigit() and int_part != "":
        raise CanonicalizationError(
            RejectReason.UNRECOGNIZED_CHARACTERS,
            f"non-digit characters remain in integer part {int_part!r}",
            raw_input,
        )
    if frac_part and not frac_part.isdigit():
        raise CanonicalizationError(
            RejectReason.UNRECOGNIZED_CHARACTERS,
            f"non-digit characters remain in fractional part {frac_part!r}",
            raw_input,
        )

    if int_part == "":
        int_part = "0"

    plain = f"{int_part}.{frac_part}" if has_decimal else int_part
    return plain, precision_digits
