"""Phase 1 tests for financial constraint parsing and equation loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.financial.concepts import ConceptRegistry
from core.financial.constraints import ConstraintConfigError, FormulaParser


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "concepts.yaml"


def test_formula_parser_builds_serializable_ir():
    parser = FormulaParser()

    expression = parser.parse("(Revenue - CostOfGoodsSold) / Revenue")

    assert expression.to_dict() == {
        "formula": "(Revenue - CostOfGoodsSold) / Revenue",
        "ir": {
            "kind": "binary",
            "op": "div",
            "left": {
                "kind": "binary",
                "op": "sub",
                "left": {"kind": "variable", "name": "Revenue"},
                "right": {"kind": "variable", "name": "CostOfGoodsSold"},
            },
            "right": {"kind": "variable", "name": "Revenue"},
        },
    }
    assert expression.variable_names() == ("CostOfGoodsSold", "Revenue")
    assert expression.operations() == ("div", "sub")


def test_formula_parser_supports_constants_and_unary_ops():
    parser = FormulaParser()

    expression = parser.parse("-(Revenue / 2)")

    assert expression.variable_names() == ("Revenue",)
    assert expression.operations() == ("div", "neg")


def test_formula_parser_rejects_unsafe_ast():
    parser = FormulaParser()

    with pytest.raises(ValueError):
        parser.parse("__import__('os').system('dir')")


def test_concept_registry_load_equations_is_deterministic():
    registry = ConceptRegistry(CONFIG_PATH)

    first = registry.load_equations()
    second = registry.load_equations()

    assert [equation.target.name for equation in first] == [
        "GrossMargin",
        "OperatingMargin",
        "RevenueYoYGrowth",
    ]
    assert first == second


def test_concept_registry_load_equations_derives_dependencies_from_formula():
    registry = ConceptRegistry(CONFIG_PATH)

    equations = {equation.target.name: equation for equation in registry.load_equations()}
    gross_margin = equations["GrossMargin"]

    assert gross_margin.target.unit == "percentage"
    assert gross_margin.formula == "(Revenue - CostOfGoodsSold) / Revenue"
    assert gross_margin.dependency_names() == ("CostOfGoodsSold", "Revenue")
    assert [dependency.source.unit for dependency in gross_margin.dependencies] == ["USD", "USD"]


def test_concept_registry_load_equations_validates_declared_requires(tmp_path):
    config_path = tmp_path / "concepts.yaml"
    config_path.write_text(
        json.dumps(
            {
                "concepts": {
                    "Revenue": {"unit": "USD"},
                    "GrossMargin": {
                        "formula": "Revenue / Revenue",
                        "unit": "percentage",
                        "requires": ["Revenue", "CostOfGoodsSold"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    registry = ConceptRegistry(config_path)

    with pytest.raises(ConstraintConfigError, match="GrossMargin"):
        registry.load_equations()
