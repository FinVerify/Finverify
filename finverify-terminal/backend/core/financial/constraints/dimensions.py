"""Semantic dimension inference for financial formulas."""

from __future__ import annotations

from enum import Enum
from typing import Mapping


class Dimension(str, Enum):
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    PER_SHARE = "per_share"
    GROWTH_RATE = "growth_rate"
    COUNT = "count"
    TIME_PERIOD = "time_period"
    DIMENSIONLESS = "dimensionless"


class DimensionMismatchError(ValueError):
    """Raised when dimensions cannot be combined or compared."""


_SCALAR_DIMENSIONS = {
    Dimension.DIMENSIONLESS,
    Dimension.RATIO,
    Dimension.PERCENTAGE,
    Dimension.GROWTH_RATE,
}

_CURRENCY_UNITS = {"usd", "eur", "gbp", "jpy", "cad", "aud", "chf", "inr", "cny"}
_COUNT_UNITS = {"count", "shares", "share"}
_TIME_UNITS = {"year", "quarter", "month"}
_PERCENTAGE_UNITS = {"fraction", "percentage", "percent", "%"}


def parse_dimension(value: Dimension | str | None) -> Dimension | None:
    if value is None:
        return None
    if isinstance(value, Dimension):
        return value
    normalized = value.strip().lower()
    try:
        return Dimension(normalized)
    except ValueError as exc:
        raise DimensionMismatchError(f"Unknown dimension: {value}") from exc


def dimension_from_unit(unit: str | None) -> Dimension | None:
    if unit is None:
        return None
    normalized = unit.strip().lower()
    if normalized in _CURRENCY_UNITS:
        return Dimension.CURRENCY
    if normalized in _COUNT_UNITS:
        return Dimension.COUNT
    if normalized in _TIME_UNITS:
        return Dimension.TIME_PERIOD
    if normalized in _PERCENTAGE_UNITS:
        return Dimension.PERCENTAGE
    return None


def are_dimensions_compatible(expected: Dimension | None, actual: Dimension | None) -> bool:
    if expected is None or actual is None:
        return True
    if expected == actual:
        return True
    return expected in _SCALAR_DIMENSIONS and actual in _SCALAR_DIMENSIONS


def infer_dimension(
    op: str,
    left: Dimension | None,
    right: Dimension | None = None,
) -> Dimension | None:
    """Infer the result dimension for a symbolic arithmetic operator."""
    normalized_op = {
        "+": "add",
        "-": "sub",
        "*": "mul",
        "/": "div",
        "unary+": "pos",
        "unary-": "neg",
    }.get(op, op)
    return infer_operation_dimension(normalized_op, left, right)


def infer_operation_dimension(
    op: str,
    left: Dimension | None,
    right: Dimension | None = None,
) -> Dimension | None:
    if op in {"pos", "neg"}:
        return left

    if left is None or right is None:
        return None

    if op in {"add", "sub"}:
        if left != right:
            raise DimensionMismatchError(f"Cannot {op} {left.value} and {right.value}")
        return left

    if op == "mul":
        return _infer_multiplication_dimension(left, right)

    if op == "div":
        return _infer_division_dimension(left, right)

    raise DimensionMismatchError(f"Unsupported dimension operation: {op}")


def infer_expression_dimension(
    ir: Mapping[str, object],
    variable_dimensions: Mapping[str, Dimension | None],
) -> Dimension | None:
    kind = ir.get("kind")
    if kind == "constant":
        return Dimension.DIMENSIONLESS
    if kind == "variable":
        return variable_dimensions.get(str(ir["name"]))
    if kind == "unary":
        operand_dimension = infer_expression_dimension(ir["operand"], variable_dimensions)
        return infer_operation_dimension(str(ir["op"]), operand_dimension)
    if kind == "binary":
        left_dimension = infer_expression_dimension(ir["left"], variable_dimensions)
        right_dimension = infer_expression_dimension(ir["right"], variable_dimensions)
        return infer_operation_dimension(str(ir["op"]), left_dimension, right_dimension)
    raise DimensionMismatchError(f"Unsupported IR node kind: {kind}")


def _infer_multiplication_dimension(left: Dimension, right: Dimension) -> Dimension:
    if left == Dimension.CURRENCY and right == Dimension.CURRENCY:
        # TODO: Revisit whether currency * currency should become a richer composite
        # dimension once FinVerify supports multi-step unit algebra.
        return Dimension.CURRENCY
    if left == Dimension.CURRENCY and right == Dimension.COUNT:
        return Dimension.PER_SHARE
    if left == Dimension.COUNT and right == Dimension.CURRENCY:
        return Dimension.PER_SHARE
    if left in _SCALAR_DIMENSIONS and right == Dimension.CURRENCY:
        return Dimension.CURRENCY
    if right in _SCALAR_DIMENSIONS and left == Dimension.CURRENCY:
        return Dimension.CURRENCY
    if left in _SCALAR_DIMENSIONS and right == Dimension.COUNT:
        return Dimension.COUNT
    if right in _SCALAR_DIMENSIONS and left == Dimension.COUNT:
        return Dimension.COUNT
    if left in _SCALAR_DIMENSIONS and right in _SCALAR_DIMENSIONS:
        return Dimension.DIMENSIONLESS
    if left in _SCALAR_DIMENSIONS and right not in _SCALAR_DIMENSIONS:
        return right
    if right in _SCALAR_DIMENSIONS and left not in _SCALAR_DIMENSIONS:
        return left
    raise DimensionMismatchError(f"Cannot multiply {left.value} and {right.value}")


def _infer_division_dimension(left: Dimension, right: Dimension) -> Dimension:
    if left == Dimension.CURRENCY and right == Dimension.CURRENCY:
        return Dimension.RATIO
    if left == Dimension.CURRENCY and right == Dimension.COUNT:
        return Dimension.PER_SHARE
    if left == right:
        return Dimension.RATIO
    if left == Dimension.PERCENTAGE and right == Dimension.PERCENTAGE:
        return Dimension.RATIO
    if left in _SCALAR_DIMENSIONS and right in _SCALAR_DIMENSIONS:
        return Dimension.RATIO
    if right in _SCALAR_DIMENSIONS and left not in _SCALAR_DIMENSIONS:
        return left
    raise DimensionMismatchError(f"Cannot divide {left.value} by {right.value}")
