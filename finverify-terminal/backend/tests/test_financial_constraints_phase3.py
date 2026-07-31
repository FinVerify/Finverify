"""Phase 3 tests for semantic dimension analysis."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.financial.concepts import ConceptRegistry
from core.financial.constraints import (
    ConstraintConfigError,
    Dimension,
    DimensionMismatchError,
    FormulaParser,
    infer_dimension,
)
from core.financial.constraints.models import Dependency, Equation, Variable
from core.financial.constraints.verifier import ConstraintVerifier


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "concepts.yaml"


def make_equation(
    target: str,
    formula: str,
    target_dimension: Dimension,
    dependency_dimensions: dict[str, Dimension],
) -> Equation:
    parser = FormulaParser()
    expression = parser.parse(formula)
    target_variable = Variable(name=target, dimension=target_dimension)
    dependencies = tuple(
        Dependency(
            source=Variable(name=name, dimension=dependency_dimensions[name]),
            target=target_variable,
        )
        for name in expression.variable_names()
    )
    return Equation(
        target=target_variable,
        expression=expression,
        dependencies=dependencies,
        dimension=target_dimension,
    )


def test_dimension_addition_mismatch():
    with pytest.raises(DimensionMismatchError, match="Cannot add currency and percentage"):
        infer_dimension("+", Dimension.CURRENCY, Dimension.PERCENTAGE)


def test_dimension_division_inference():
    parser = FormulaParser()

    inferred = parser.infer_dimension(
        "Revenue / SharesOutstanding",
        {
            "Revenue": Dimension.CURRENCY,
            "SharesOutstanding": Dimension.COUNT,
        },
    )

    assert inferred == Dimension.PER_SHARE


def test_dimension_validation_in_concepts_yaml(tmp_path):
    registry = ConceptRegistry(CONFIG_PATH)
    equations = {equation.target.name: equation for equation in registry.load_equations()}

    gross_margin = equations["GrossMargin"]
    assert gross_margin.dimension == Dimension.PERCENTAGE
    assert gross_margin.target.dimension == Dimension.PERCENTAGE
    assert [dependency.source.dimension for dependency in gross_margin.dependencies] == [
        Dimension.CURRENCY,
        Dimension.CURRENCY,
    ]

    config_path = tmp_path / "concepts.yaml"
    config_path.write_text(
        json.dumps(
            {
                "concepts": {
                    "Revenue": {"dimension": "currency", "unit": "USD"},
                    "SharesOutstanding": {"dimension": "count", "unit": "shares"},
                    "BadMetric": {
                        "formula": "Revenue + SharesOutstanding",
                        "dimension": "currency",
                        "unit": "USD",
                        "requires": ["Revenue", "SharesOutstanding"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    invalid_registry = ConceptRegistry(config_path)

    with pytest.raises(ConstraintConfigError, match="BadMetric"):
        invalid_registry.load_equations()


def test_verifier_with_dimension_mismatch():
    verifier = ConstraintVerifier(
        [
            make_equation(
                "InvalidMetric",
                "Revenue + GrossMargin",
                Dimension.CURRENCY,
                {
                    "Revenue": Dimension.CURRENCY,
                    "GrossMargin": Dimension.PERCENTAGE,
                },
            )
        ]
    )

    result = verifier.verify(
        {
            "Revenue": 100.0,
            "GrossMargin": 0.4,
            "InvalidMetric": 100.4,
        }
    )

    assert result.consistent is True
    assert result.violations == []
    assert result.indeterminate == ["InvalidMetric"]
    assert "Cannot add currency and percentage" in result.indeterminate_reasons["InvalidMetric"]
