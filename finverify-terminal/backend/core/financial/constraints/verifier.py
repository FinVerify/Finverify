"""Deterministic multi-claim constraint verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from core.financial.formula import FormulaEngine

from .dimensions import (
    Dimension,
    DimensionMismatchError,
    are_dimensions_compatible,
    dimension_from_unit,
    parse_dimension,
)
from .graph import ConstraintGraph
from .models import (
    ConstraintCoverage,
    ConstraintStatus,
    Equation,
    EquationOutcome,
    EquationStatus,
    Violation,
)
from .parser import FormulaParser


@dataclass(frozen=True)
class ConstraintResult:
    status: ConstraintStatus
    coverage: ConstraintCoverage
    consistent: bool | None
    outcomes: tuple[EquationOutcome, ...] = field(default_factory=tuple)
    violations: list[Violation] = field(default_factory=list)
    indeterminate: list[str] = field(default_factory=list)
    indeterminate_reasons: dict[str, str] = field(default_factory=dict)


class ConstraintVerifier:
    """Verify reported claims against formula-backed equations."""

    def __init__(
        self,
        equations: list[Equation],
        *,
        abs_tol: float = 1e-8,
        rel_tol: float = 1e-6,
        formula_engine: FormulaEngine | None = None,
    ):
        self._equations = tuple(equations)
        self._abs_tol = abs_tol
        self._rel_tol = rel_tol
        self._formula_engine = formula_engine or FormulaEngine()
        self._parser = FormulaParser()
        self._graph = ConstraintGraph(self._equations)

        equations_by_target = {}
        for equation in self._equations:
            target = equation.target.name
            if target in equations_by_target:
                raise ValueError(f"Duplicate equation target: {target}")
            equations_by_target[target] = equation

        self._ordered_equations = tuple(
            equations_by_target[node]
            for node in self._graph.topological_order()
            if node in equations_by_target
        )

    def verify(self, claims: Mapping[str, float | Mapping[str, Any] | None]) -> ConstraintResult:
        normalized_claims = {
            metric: _normalize_claim_entry(raw_claim)
            for metric, raw_claim in claims.items()
        }
        violations: list[Violation] = []
        indeterminate: list[str] = []
        indeterminate_reasons: dict[str, str] = {}
        outcomes: list[EquationOutcome] = []

        for equation in self._ordered_equations:
            target = equation.target.name
            expected_dimension = equation.dimension or equation.target.dimension
            target_claim = normalized_claims.get(target)
            target_reported = target_claim is not None and target_claim["value"] is not None

            dependency_values: dict[str, float] = {}
            missing_dependency = False
            for dependency in equation.dependency_names():
                dependency_claim = normalized_claims.get(dependency)
                if dependency_claim is None or dependency_claim["value"] is None:
                    missing_dependency = True
                    break
                dependency_values[dependency] = float(dependency_claim["value"])

            if missing_dependency:
                if target_reported:
                    reason = "Missing dependency values"
                    indeterminate.append(target)
                    indeterminate_reasons[target] = reason
                    outcomes.append(
                        EquationOutcome(
                            target=target,
                            status=EquationStatus.INDETERMINATE,
                            formula=equation.formula,
                            dependencies=dependency_values,
                            reason=reason,
                        )
                    )
                else:
                    outcomes.append(
                        EquationOutcome(
                            target=target,
                            status=EquationStatus.NOT_APPLICABLE,
                            formula=equation.formula,
                            dependencies=dependency_values,
                            reason="Target not reported and dependency values are incomplete",
                        )
                    )
                continue

            if not target_reported:
                outcomes.append(
                    EquationOutcome(
                        target=target,
                        status=EquationStatus.DERIVABLE,
                        formula=equation.formula,
                        dependencies=dependency_values,
                        reason="Target not reported but dependency values are complete",
                    )
                )
                continue

            try:
                inferred_dimension = self._parser.infer_dimension(
                    equation.expression,
                    {
                        dependency.source.name: dependency.source.dimension
                        for dependency in equation.dependencies
                    },
                )
                if expected_dimension is not None and inferred_dimension is not None and not are_dimensions_compatible(
                    expected_dimension,
                    inferred_dimension,
                ):
                    raise DimensionMismatchError(
                        f"Dimension mismatch: expected {expected_dimension.value}, got {inferred_dimension.value}"
                    )
                expected = self._formula_engine.evaluate(equation.formula, dependency_values)
            except (DimensionMismatchError, KeyError, ZeroDivisionError) as exc:
                reason = str(exc)
                indeterminate.append(target)
                indeterminate_reasons[target] = reason
                outcomes.append(
                    EquationOutcome(
                        target=target,
                        status=EquationStatus.INDETERMINATE,
                        formula=equation.formula,
                        dependencies=dependency_values,
                        reason=reason,
                    )
                )
                continue

            actual = float(target_claim["value"])
            actual_dimension = target_claim["dimension"]
            if actual_dimension is not None and expected_dimension is not None and not are_dimensions_compatible(
                expected_dimension,
                actual_dimension,
            ):
                reason = (
                    f"Dimension mismatch: expected {expected_dimension.value}, "
                    f"got {actual_dimension.value}"
                )
                indeterminate.append(target)
                indeterminate_reasons[target] = reason
                outcomes.append(
                    EquationOutcome(
                        target=target,
                        status=EquationStatus.INDETERMINATE,
                        formula=equation.formula,
                        dependencies=dependency_values,
                        reason=reason,
                    )
                )
                continue

            if not self._within_tolerance(actual, expected):
                violations.append(
                    Violation(
                        metric=target,
                        expected=expected,
                        actual=actual,
                        formula=equation.formula,
                        dependencies=dependency_values,
                    )
                )
                outcomes.append(
                    EquationOutcome(
                        target=target,
                        status=EquationStatus.VIOLATION,
                        formula=equation.formula,
                        dependencies=dependency_values,
                        expected=expected,
                        actual=actual,
                    )
                )
                continue

            outcomes.append(
                EquationOutcome(
                    target=target,
                    status=EquationStatus.VERIFIED,
                    formula=equation.formula,
                    dependencies=dependency_values,
                    expected=expected,
                    actual=actual,
                )
            )

        coverage = ConstraintCoverage(
            loaded=len(outcomes),
            verified=sum(1 for outcome in outcomes if outcome.status == EquationStatus.VERIFIED),
            violated=sum(1 for outcome in outcomes if outcome.status == EquationStatus.VIOLATION),
            indeterminate=sum(1 for outcome in outcomes if outcome.status == EquationStatus.INDETERMINATE),
            derivable=sum(1 for outcome in outcomes if outcome.status == EquationStatus.DERIVABLE),
            not_applicable=sum(1 for outcome in outcomes if outcome.status == EquationStatus.NOT_APPLICABLE),
        )

        if coverage.violated > 0:
            status = ConstraintStatus.INCONSISTENT
        elif coverage.indeterminate > 0:
            status = ConstraintStatus.INDETERMINATE
        elif coverage.verified > 0:
            status = ConstraintStatus.CONSISTENT
        else:
            status = ConstraintStatus.NOT_EVALUATED

        if status == ConstraintStatus.CONSISTENT:
            consistent = True
        elif status == ConstraintStatus.INCONSISTENT:
            consistent = False
        else:
            consistent = None

        return ConstraintResult(
            status=status,
            coverage=coverage,
            outcomes=tuple(outcomes),
            consistent=consistent,
            violations=violations,
            indeterminate=indeterminate,
            indeterminate_reasons=indeterminate_reasons,
        )

    def _within_tolerance(self, actual: float, expected: float) -> bool:
        difference = abs(actual - expected)
        tolerance = max(self._abs_tol, self._rel_tol * max(1.0, abs(expected)))
        return difference <= tolerance


def _normalize_claim_entry(raw_claim: float | Mapping[str, Any] | None) -> dict[str, Any] | None:
    if raw_claim is None:
        return None
    if isinstance(raw_claim, Mapping):
        value = raw_claim.get("value")
        unit = raw_claim.get("unit")
        dimension = _parse_claim_dimension(raw_claim.get("dimension"), unit)
        return {"value": value, "unit": unit, "dimension": dimension}
    return {"value": raw_claim, "unit": None, "dimension": None}


def _parse_claim_dimension(
    raw_dimension: Dimension | str | None,
    unit: str | None,
) -> Dimension | None:
    if raw_dimension is not None:
        return parse_dimension(raw_dimension)
    return dimension_from_unit(unit)
