"""Deterministic arithmetic formula evaluation without eval()."""

import ast
import operator
from typing import Mapping


class FormulaEngine:
    """Safe arithmetic evaluator backed by Python's AST."""

    _binary_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    _unary_operators = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(self, formula: str, values: Mapping[str, float]) -> float:
        parsed = ast.parse(formula, mode="eval")
        return float(self._evaluate_node(parsed.body, values))

    def _evaluate_node(self, node: ast.AST, values: Mapping[str, float]) -> float:
        if isinstance(node, ast.BinOp):
            return self._evaluate_binary(node, values)
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._unary_operators:
            operand = self._evaluate_node(node.operand, values)
            return self._unary_operators[type(node.op)](operand)
        if isinstance(node, ast.Name):
            if node.id not in values:
                raise KeyError(f"Missing value for concept '{node.id}'")
            return float(values[node.id])
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Num):
            return float(node.n)
        raise ValueError(f"Unsupported formula node: {ast.dump(node)}")

    def _evaluate_binary(self, node: ast.BinOp, values: Mapping[str, float]) -> float:
        operator_type = type(node.op)
        if operator_type not in self._binary_operators:
            raise ValueError(f"Unsupported operator: {operator_type.__name__}")
        left = self._evaluate_node(node.left, values)
        right = self._evaluate_node(node.right, values)
        if operator_type is ast.Div and right == 0:
            raise ZeroDivisionError("Division by zero in formula evaluation")
        return self._binary_operators[operator_type](left, right)
