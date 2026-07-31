"""Immutable mathematical primitives for financial constraints."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .dimensions import Dimension

IRNode = dict[str, Any]


@dataclass(frozen=True)
class Variable:
    name: str
    dimension: Dimension | None = None
    unit: str | None = None


@dataclass(frozen=True)
class Expression:
    formula: str
    ir: IRNode

    def to_dict(self) -> IRNode:
        return {"formula": self.formula, "ir": self.ir}

    def variable_names(self) -> tuple[str, ...]:
        names: set[str] = set()
        _collect_variable_names(self.ir, names)
        return tuple(sorted(names))

    def operations(self) -> tuple[str, ...]:
        ops: set[str] = set()
        _collect_operations(self.ir, ops)
        return tuple(sorted(ops))


@dataclass(frozen=True)
class Dependency:
    source: Variable
    target: Variable


@dataclass(frozen=True)
class Equation:
    target: Variable
    expression: Expression
    dependencies: tuple[Dependency, ...]
    dimension: Dimension | None = None

    @property
    def formula(self) -> str:
        return self.expression.formula

    def dependency_names(self) -> tuple[str, ...]:
        return tuple(sorted(dependency.source.name for dependency in self.dependencies))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": asdict(self.target),
            "expression": self.expression.to_dict(),
            "dependencies": [asdict(dependency) for dependency in self.dependencies],
            "dimension": self.dimension.value if self.dimension is not None else None,
        }


@dataclass(frozen=True)
class EvaluationResult:
    value: float | None
    dimension: Dimension | None = None
    status: str = "ok"


@dataclass(frozen=True)
class Violation:
    metric: str
    expected: float
    actual: float
    formula: str
    dependencies: Mapping[str, float]
    reason: str | None = None


def _collect_variable_names(node: IRNode, names: set[str]) -> None:
    kind = node.get("kind")
    if kind == "variable":
        names.add(str(node["name"]))
        return
    if kind == "binary":
        _collect_variable_names(node["left"], names)
        _collect_variable_names(node["right"], names)
        return
    if kind == "unary":
        _collect_variable_names(node["operand"], names)


def _collect_operations(node: IRNode, ops: set[str]) -> None:
    kind = node.get("kind")
    if kind == "binary":
        ops.add(str(node["op"]))
        _collect_operations(node["left"], ops)
        _collect_operations(node["right"], ops)
        return
    if kind == "unary":
        ops.add(str(node["op"]))
        _collect_operations(node["operand"], ops)
