"""finverify.resources.fcg — Financial Constraint Graph endpoints."""

from __future__ import annotations

from ..models import Constraint, FCGVerifyResult, NormalizeResult
from ..validators import require_dict_of_numbers


def build_fcg_verify_request(values: dict, normalize: bool = True) -> tuple[str, str, dict, None]:
    values = require_dict_of_numbers(values, "values")
    body = {"values": values, "normalize": normalize}
    return "POST", "/v1/fcg/verify", body, None


def parse_fcg_verify_response(data: dict) -> FCGVerifyResult:
    return FCGVerifyResult.from_dict(data)


def build_fcg_normalize_request(names: list[str]) -> tuple[str, str, dict, None]:
    if not names:
        from ..exceptions import ValidationError

        raise ValidationError("'names' must be a non-empty list of metric names")
    body = {"names": list(names)}
    return "POST", "/v1/fcg/normalize", body, None


def parse_fcg_normalize_response(data: dict) -> NormalizeResult:
    return NormalizeResult.from_dict(data)


def build_fcg_constraints_request() -> tuple[str, str, None, None]:
    return "GET", "/v1/fcg/constraints", None, None


def parse_fcg_constraints_response(data: dict) -> list[Constraint]:
    return [Constraint.from_dict(item) for item in data.get("constraints", [])]


__all__ = [
    "build_fcg_verify_request",
    "parse_fcg_verify_response",
    "build_fcg_normalize_request",
    "parse_fcg_normalize_response",
    "build_fcg_constraints_request",
    "parse_fcg_constraints_response",
]
