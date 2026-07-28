"""
finverify.validators — Request-side validation
================================================
Fails fast, locally, before spending a network round trip on a request
the API would reject anyway (HTTP 422 from FastAPI/Pydantic).
"""

from __future__ import annotations

from .exceptions import ValidationError


def require_str(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"'{name}' must be a non-empty string, got {value!r}")
    return value


def require_number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"'{name}' must be a number, got {value!r}")
    return float(value)


def require_ticker(value: str) -> str:
    ticker = require_str(value, "ticker")
    return ticker.strip().upper()


def require_dict_of_numbers(value, name: str) -> dict:
    if not isinstance(value, dict) or not value:
        raise ValidationError(f"'{name}' must be a non-empty dict of metric -> number")
    cleaned = {}
    for key, val in value.items():
        try:
            cleaned[key] = float(val)
        except (TypeError, ValueError):
            raise ValidationError(
                f"'{name}[{key!r}]' must be numeric, got {val!r}"
            ) from None
    return cleaned


__all__ = [
    "require_str",
    "require_number",
    "require_ticker",
    "require_dict_of_numbers",
]
