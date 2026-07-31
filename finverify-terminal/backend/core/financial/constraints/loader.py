"""Deterministic equation loading from the concept registry."""

from __future__ import annotations

from typing import Any, Mapping

from .dimensions import DimensionMismatchError, are_dimensions_compatible, parse_dimension
from .models import Dependency, Equation, Variable
from .parser import FormulaParser


class ConstraintConfigError(ValueError):
    """Raised when constraint-related concept configuration is invalid."""


def load_equations_from_concepts(
    concepts: Mapping[str, Mapping[str, Any]],
    *,
    parser: FormulaParser | None = None,
) -> list[Equation]:
    parser = parser or FormulaParser()
    equations: list[Equation] = []

    for concept_name in sorted(concepts):
        spec = concepts[concept_name]
        formula = spec.get("formula")
        if not formula:
            continue

        expression = parser.parse(formula)
        derived_dependencies = expression.variable_names()
        declared_dependencies = tuple(sorted(spec.get("requires", [])))
        if declared_dependencies and declared_dependencies != derived_dependencies:
            raise ConstraintConfigError(
                f"Concept '{concept_name}' requires {list(declared_dependencies)} but formula derives {list(derived_dependencies)}"
            )

        target = _build_variable(concept_name, spec)
        dependencies = tuple(
            Dependency(
                source=_build_variable(dependency_name, _resolve_variable_spec(dependency_name, concepts)),
                target=target,
            )
            for dependency_name in derived_dependencies
        )
        try:
            inferred_dimension = parser.infer_dimension(
                expression,
                {
                    dependency.source.name: dependency.source.dimension
                    for dependency in dependencies
                },
            )
        except DimensionMismatchError as exc:
            raise ConstraintConfigError(
                f"Concept '{concept_name}' has incompatible dimensions in formula '{formula}': {exc}"
            ) from exc
        if target.dimension is not None and inferred_dimension is not None and not are_dimensions_compatible(
            target.dimension,
            inferred_dimension,
        ):
            raise ConstraintConfigError(
                f"Concept '{concept_name}' declares dimension '{target.dimension.value}' but formula infers '{inferred_dimension.value}'"
            )
        equations.append(
            Equation(
                target=target,
                expression=expression,
                dependencies=dependencies,
                dimension=target.dimension,
            )
        )

    return equations


def _build_variable(name: str, spec: Mapping[str, Any]) -> Variable:
    try:
        dimension = parse_dimension(spec.get("dimension"))
    except ValueError as exc:
        raise ConstraintConfigError(f"Concept '{name}' has invalid dimension: {spec.get('dimension')}") from exc
    return Variable(name=name, dimension=dimension, unit=spec.get("unit"))


def _resolve_variable_spec(
    name: str,
    concepts: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    if name in concepts:
        return concepts[name]
    if name.endswith("_prior"):
        base_name = name[: -len("_prior")]
        return concepts.get(base_name, {})
    return {}
