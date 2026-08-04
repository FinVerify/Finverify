"""Frozen deterministic quantitative lexical grammar."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple

from .models import NumericTarget


NUMBER = r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+)|(?:\d+))(?:\.\d+)?"
NUMBER_BOUNDARY = r"(?<![\d,])" + NUMBER + r"(?!\d)(?!,\d)"
SCALE_WORD = r"(?:thousand|million|billion|trillion|K|M|B|T)"
SCALE_FACTORS = {
    "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12,
    "k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12,
}


def _compile(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("currency", _compile(r"(?<![\w,])(?:\(\s*)?[+-]?(?:US\$|USD|\$)\s*" + NUMBER.replace("[+-]?", "") + r"(?!\d)(?!,\d)(?:\s*" + SCALE_WORD + r")?\s*\)?")),
    ("percentage", _compile(NUMBER_BOUNDARY + r"(?:\s*%|\s+percent)")),
    ("basis_points", _compile(NUMBER_BOUNDARY + r"\s+(?:bps|basis\s+point(?:s)?)")),
    ("ratio", _compile(NUMBER_BOUNDARY + r"(?:x|\s+times)")),
    ("scaled_number", _compile(NUMBER_BOUNDARY + r"\s*" + SCALE_WORD)),
    ("number", _compile(NUMBER_BOUNDARY)),
)


def _number_text(raw: str) -> str:
    text = raw.replace(",", "")
    text = re.sub(r"^[()]", "", text)
    text = re.sub(r"[()]$", "", text)
    text = re.sub(r"^[+-]?\s*(?:US\$|USD|\$)\s*", "", text, flags=re.IGNORECASE)
    text = text.strip()
    match = re.search(r"[+-]?(?:\d+(?:\.\d+)?)", text)
    if not match:
        raise ValueError("numeric text missing number: %r" % raw)
    return match.group(0)


def _normalize(raw: str, kind: str, context: str) -> Tuple[str, float, str, float, Dict[str, object]]:
    negative = raw.strip().startswith("(") or raw.strip().startswith("-")
    base = float(_number_text(raw))
    factor = 1.0
    scale_token = None
    scale_match = re.search(r"(?:thousand|million|billion|trillion|K|M|B|T)\s*\)?$", raw, re.IGNORECASE)
    if scale_match:
        scale_token = scale_match.group(0).strip(" )").lower()
        factor = SCALE_FACTORS[scale_token]
    if negative:
        base = -abs(base)
    if kind == "currency":
        unit = "USD"
    elif kind == "percentage":
        unit = "percent"
    elif kind == "basis_points":
        unit = "basis_points"
    elif kind == "ratio":
        unit = "ratio"
    elif kind == "scaled_number":
        unit = "number"
    else:
        unit = "number"
    if kind == "currency" and re.search(r"\b(?:per\s+(?:diluted\s+|basic\s+)?share|EPS|earnings\s+per\s+share)\b", context, re.IGNORECASE):
        kind = "per_share_numeric"
    return kind, base * factor, unit, factor, {"scale_token": scale_token} if scale_token else {}


def find_targets(text: str) -> List[NumericTarget]:
    """Find non-overlapping targets by frozen precedence, earliest position."""
    matches = []
    for precedence, (kind, pattern) in enumerate(PATTERNS):
        for match in pattern.finditer(text):
            raw = match.group(0).rstrip()
            end = match.start() + len(raw)
            matches.append((match.start(), precedence, -len(raw), end, kind, raw))
    selected = []
    cursor = -1
    while matches:
        available = [item for item in matches if item[0] >= cursor]
        if not available:
            break
        start = min(item[0] for item in available)
        at_start = [item for item in available if item[0] == start]
        chosen = sorted(at_start, key=lambda item: (item[1], item[2]))[0]
        end, kind, raw = chosen[3], chosen[4], chosen[5]
        effective_kind, normalized, unit, scale, metadata = _normalize(raw, kind, text)
        selected.append(NumericTarget(start, end, raw, effective_kind, normalized, unit, scale, metadata))
        cursor = end
        matches = [item for item in matches if item[3] > cursor or item[0] >= cursor]
    return selected
