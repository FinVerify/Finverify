"""AST parser for constraint formulas."""

from __future__ import annotations

import ast
from typing import Mapping

from core.financial.formula import FormulaEngine

from .dimensions import Dimension, infer_expression_dimension
from .models import Expression, IRNode


class FormulaParser:
    """Parse formula strings into a serializable IR."""

    _binary_operators = {
        ast.Add: "add",
        ast.Sub: "sub",
        ast.Mult: "mul",
        ast.Div: "div",
    }
    _unary_operators = {
        ast.UAdd: "pos",
        ast.USub: "neg",
    }

    def __init__(self) -> None:
        engine_binary = set(FormulaEngine._binary_operators)
        engine_unary = set(FormulaEngine._unary_operators)
        if engine_binary != set(self._binary_operators):
            raise ValueError("FormulaParser binary whitelist must match FormulaEngine")
        if engine_unary != set(self._unary_operators):
            raise ValueError("FormulaParser unary whitelist must match FormulaEngine")

    def parse(self, formula: str) -> Expression:
        parsed = ast.parse(formula, mode="eval")
        return Expression(formula=formula, ir=self._build_ir(parsed.body))

    def variable_names(self, formula: str) -> tuple[str, ...]:
        return self.parse(formula).variable_names()

    def operations(self, formula: str) -> tuple[str, ...]:
        return self.parse(formula).operations()

    def infer_dimension(
        self,
        expression: Expression | str,
        variable_dimensions: Mapping[str, Dimension | None],
    ) -> Dimension | None:
        parsed = expression if isinstance(expression, Expression) else self.parse(expression)
        return infer_expression_dimension(parsed.ir, variable_dimensions)

    def _build_ir(self, node: ast.AST) -> IRNode:
        if isinstance(node, ast.BinOp):
            operator_type = type(node.op)
            if operator_type not in self._binary_operators:
                raise ValueError(f"Unsupported operator: {operator_type.__name__}")
            return {
                "kind": "binary",
                "op": self._binary_operators[operator_type],
                "left": self._build_ir(node.left),
                "right": self._build_ir(node.right),
            }
        if isinstance(node, ast.UnaryOp):
            operator_type = type(node.op)
            if operator_type not in self._unary_operators:
                raise ValueError(f"Unsupported operator: {operator_type.__name__}")
            return {
                "kind": "unary",
                "op": self._unary_operators[operator_type],
                "operand": self._build_ir(node.operand),
            }
        if isinstance(node, ast.Name):
            return {"kind": "variable", "name": node.id}
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return {"kind": "constant", "value": float(node.value)}
        if isinstance(node, ast.Num):
            return {"kind": "constant", "value": float(node.n)}
        raise ValueError(f"Unsupported formula node: {ast.dump(node)}")
