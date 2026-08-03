"""Shared financial period parsing and compatibility utilities."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal, Optional

from .document import FinancialPeriod

PeriodCompatibility = Literal["MATCH", "MISMATCH", "UNKNOWN"]
StatementPeriodType = Literal["instant", "duration"]

_FISCAL_YEAR_RE = re.compile(
    r"\b(?:fy|fiscal(?:\s+year)?)\s*(20\d{2})\b",
    re.IGNORECASE,
)
_QUARTER_FISCAL_YEAR_RE = re.compile(
    r"\bq([1-4])\s*(?:fy|fiscal(?:\s+year)?)?\s*(20\d{2})\b",
    re.IGNORECASE,
)
_QUARTER_YEAR_RE = re.compile(
    r"\bq([1-4])\s+(20\d{2})\b",
    re.IGNORECASE,
)
_WORD_QUARTER_FISCAL_YEAR_RE = re.compile(
    r"\b(first|second|third|fourth)\s+quarter(?:\s+(?:of|for))?\s+(?:fy|fiscal(?:\s+year)?)\s*(20\d{2})\b",
    re.IGNORECASE,
)
_GUIDANCE_CUE_RE = re.compile(
    r"\b(guidance|expect|expects|expected|forecast|forecasts|outlook|project|projects|projected|target|targets)\b",
    re.IGNORECASE,
)
_FUTURE_CUE_RE = re.compile(
    r"\b(next\s+quarter|next\s+year|coming\s+quarter|coming\s+year|future)\b",
    re.IGNORECASE,
)
_RELATIVE_AMBIGUOUS_RE = re.compile(
    r"\b(previous\s+quarter|prior\s+quarter|last\s+quarter|year\s+ago|a\s+year\s+ago|last\s+year|prior\s+year|bare\s+quarter|full\s+year)\b",
    re.IGNORECASE,
)
_BARE_QUARTER_RE = re.compile(r"\b(?:q[1-4]|first quarter|second quarter|third quarter|fourth quarter)\b", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_QUARTER_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4}


def parse_period_string(
    raw_period: Optional[str],
    *,
    statement_period_type: Optional[StatementPeriodType] = None,
) -> Optional[FinancialPeriod]:
    """Parse a transcript or evidence period string into FinancialPeriod."""
    if raw_period is None:
        return None

    text = raw_period.strip()
    if not text:
        return None

    if _GUIDANCE_CUE_RE.search(text) or _FUTURE_CUE_RE.search(text):
        return FinancialPeriod(kind="future")

    quarter_match = _QUARTER_FISCAL_YEAR_RE.search(text) or _QUARTER_YEAR_RE.search(text)
    if quarter_match:
        return FinancialPeriod(
            kind="quarterly",
            fiscal_quarter=int(quarter_match.group(1)),
            fiscal_year=int(quarter_match.group(2)),
        )

    word_quarter_match = _WORD_QUARTER_FISCAL_YEAR_RE.search(text)
    if word_quarter_match:
        return FinancialPeriod(
            kind="quarterly",
            fiscal_quarter=_QUARTER_WORDS[word_quarter_match.group(1).lower()],
            fiscal_year=int(word_quarter_match.group(2)),
        )

    fy_match = _FISCAL_YEAR_RE.search(text)
    if fy_match:
        return FinancialPeriod(
            kind="annual",
            fiscal_year=int(fy_match.group(1)),
        )

    date_matches = list(_DATE_RE.finditer(text))
    if date_matches:
        dates = [
            date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            for match in date_matches
        ]
        start_date = dates[0] if len(dates) > 1 else None
        end_date = dates[-1]
        kind: Literal["instant", "unknown"] = "unknown"
        if statement_period_type == "instant":
            kind = "instant"
        return FinancialPeriod(
            kind=kind,
            start_date=start_date,
            end_date=end_date,
            fiscal_year=end_date.year,
        )

    if _RELATIVE_AMBIGUOUS_RE.search(text):
        return FinancialPeriod(kind="unknown")

    if _BARE_QUARTER_RE.search(text):
        return FinancialPeriod(kind="unknown")

    return None


def periods_compatible(
    claim_period: Optional[FinancialPeriod],
    evidence_period: Optional[FinancialPeriod],
) -> PeriodCompatibility:
    """Return whether two structured periods are compatible for verification."""
    if claim_period is None or evidence_period is None:
        return "UNKNOWN"

    claim_kind = claim_period.kind
    evidence_kind = evidence_period.kind

    if claim_kind == "unknown" or evidence_kind == "unknown":
        return "UNKNOWN"

    future_kinds = {claim_kind, evidence_kind}
    if "future" in future_kinds:
        if claim_kind == evidence_kind == "future":
            return "UNKNOWN"
        return "MISMATCH"

    if claim_kind == "instant" or evidence_kind == "instant":
        if claim_kind != "instant" or evidence_kind != "instant":
            return "MISMATCH"
        if claim_period.end_date is None or evidence_period.end_date is None:
            return "UNKNOWN"
        return "MATCH" if claim_period.end_date == evidence_period.end_date else "MISMATCH"

    if claim_kind != evidence_kind:
        return "MISMATCH"

    if claim_period.fiscal_year is None or evidence_period.fiscal_year is None:
        return "UNKNOWN"

    if claim_period.fiscal_year != evidence_period.fiscal_year:
        return "MISMATCH"

    if claim_kind == "quarterly":
        if claim_period.fiscal_quarter is None or evidence_period.fiscal_quarter is None:
            return "UNKNOWN"
        return "MATCH" if claim_period.fiscal_quarter == evidence_period.fiscal_quarter else "MISMATCH"

    return "MATCH"
