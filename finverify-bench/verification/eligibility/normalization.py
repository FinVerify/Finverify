"""Exact, conservative Amendment 1 normalization."""

from __future__ import annotations

import json
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

STATES = {"UNKNOWN", "UNSPECIFIED", "NOT_APPLICABLE"}


def lexical(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = " ".join(text.split())
    return text.casefold()


def state_or_lexical(value: Any) -> str:
    if value is None:
        return "UNSPECIFIED"
    text = lexical(value)
    if text in {s.casefold() for s in STATES}:
        return text.upper()
    return text


def normalize_identity(identity: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    result["entity"] = state_or_lexical(identity.get("entity"))
    result["concept"] = state_or_lexical(identity.get("concept"))
    result["period"] = _structured(identity.get("period"))
    result["scope"] = state_or_lexical(identity.get("scope"))
    result["accounting_basis"] = state_or_lexical(identity.get("accounting_basis"))
    result["temporal_frame"] = state_or_lexical(identity.get("temporal_frame"))
    result["value_role"] = state_or_lexical(identity.get("value_role"))
    return result


def _structured(value: Any) -> Any:
    if value is None:
        return "UNSPECIFIED"
    if isinstance(value, dict):
        return {lexical(key): _structured(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_structured(item) for item in value]
    return state_or_lexical(value)


def normalized_value_key(value: Any, unit: Any, scale: Any) -> str:
    """Produce an exact decimal key; no tolerance or float comparison."""
    try:
        number = Decimal(str(value)) * Decimal(str(scale))
        number_text = format(number.normalize(), "f")
    except (InvalidOperation, ValueError):
        number_text = lexical(value)
    return json.dumps({"value": number_text, "unit": lexical(unit), "scale": lexical(scale)}, separators=(",", ":"), sort_keys=True)


def determinate(value: Any) -> bool:
    return value not in {None, "UNKNOWN", "UNSPECIFIED", "unknown", "unspecified"}
