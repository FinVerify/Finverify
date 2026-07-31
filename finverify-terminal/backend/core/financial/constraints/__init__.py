"""Constraint-building primitives for financial concepts."""

from .dimensions import Dimension, DimensionMismatchError, infer_dimension
from .loader import ConstraintConfigError, load_equations_from_concepts
from .models import Dependency, Equation, EvaluationResult, Expression, Variable, Violation
from .parser import FormulaParser
from .verifier import ConstraintResult, ConstraintVerifier

__all__ = [
    "ConstraintConfigError",
    "ConstraintResult",
    "ConstraintVerifier",
    "Dependency",
    "Dimension",
    "DimensionMismatchError",
    "Equation",
    "EvaluationResult",
    "Expression",
    "FormulaParser",
    "Variable",
    "Violation",
    "infer_dimension",
    "load_equations_from_concepts",
]
