"""Phase 6.4 tests for the balance sheet identity constraint."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.financial.concepts import ConceptRegistry
from core.financial.constraints.graph import ConstraintGraph
from core.financial.constraints.models import ConstraintStatus, EquationStatus
from core.financial.constraints.verifier import ConstraintVerifier


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "concepts.yaml"


def _assets_equation():
    registry = ConceptRegistry(CONFIG_PATH)
    equations = registry.load_equations()
    return registry, equations, {equation.target.name: equation for equation in equations}["Assets"]


def test_assets_equation_loads_with_expected_dependencies_and_no_cycle():
    registry, equations, assets = _assets_equation()

    assert [equation.target.name for equation in equations] == [
        "Assets",
        "GrossMargin",
        "OperatingMargin",
        "RevenueYoYGrowth",
    ]
    assert registry.get_concept("Assets")["formula"] == "LiabilitiesAndStockholdersEquity"
    assert assets.target.name == "Assets"
    assert assets.formula == "LiabilitiesAndStockholdersEquity"
    assert assets.dependency_names() == ("LiabilitiesAndStockholdersEquity",)

    graph = ConstraintGraph(equations)

    assert graph.edges() == (
        ("CostOfGoodsSold", "GrossMargin"),
        ("LiabilitiesAndStockholdersEquity", "Assets"),
        ("OperatingIncome", "OperatingMargin"),
        ("Revenue", "GrossMargin"),
        ("Revenue", "OperatingMargin"),
        ("Revenue", "RevenueYoYGrowth"),
        ("Revenue_prior", "RevenueYoYGrowth"),
    )
    assert graph.topological_order() == (
        "CostOfGoodsSold",
        "LiabilitiesAndStockholdersEquity",
        "Assets",
        "OperatingIncome",
        "Revenue",
        "GrossMargin",
        "OperatingMargin",
        "Revenue_prior",
        "RevenueYoYGrowth",
    )


def test_assets_identity_verifies_when_exact():
    _, equations, _ = _assets_equation()

    result = ConstraintVerifier(equations).verify(
        {
            "Assets": 100.0,
            "LiabilitiesAndStockholdersEquity": 100.0,
        }
    )

    assets_outcome = next(outcome for outcome in result.outcomes if outcome.target == "Assets")

    assert result.status == ConstraintStatus.CONSISTENT
    assert assets_outcome.status == EquationStatus.VERIFIED
    assert assets_outcome.expected == pytest.approx(100.0)
    assert assets_outcome.actual == pytest.approx(100.0)


def test_assets_identity_verifies_within_default_tolerance():
    _, equations, _ = _assets_equation()

    result = ConstraintVerifier(equations).verify(
        {
            "Assets": 100.00009,
            "LiabilitiesAndStockholdersEquity": 100.0,
        }
    )

    assets_outcome = next(outcome for outcome in result.outcomes if outcome.target == "Assets")

    assert result.status == ConstraintStatus.CONSISTENT
    assert assets_outcome.status == EquationStatus.VERIFIED
    assert assets_outcome.expected == pytest.approx(100.0)
    assert assets_outcome.actual == pytest.approx(100.00009)


def test_assets_identity_records_violation_for_real_mismatch():
    _, equations, _ = _assets_equation()

    result = ConstraintVerifier(equations).verify(
        {
            "Assets": 100.0,
            "LiabilitiesAndStockholdersEquity": 90.0,
        }
    )

    assets_outcome = next(outcome for outcome in result.outcomes if outcome.target == "Assets")
    assets_violation = next(violation for violation in result.violations if violation.metric == "Assets")

    assert result.status == ConstraintStatus.INCONSISTENT
    assert assets_outcome.status == EquationStatus.VIOLATION
    assert assets_outcome.expected == pytest.approx(90.0)
    assert assets_outcome.actual == pytest.approx(100.0)
    assert assets_violation.expected == pytest.approx(90.0)
    assert assets_violation.actual == pytest.approx(100.0)
    assert assets_violation.actual - assets_violation.expected == pytest.approx(10.0)


def test_assets_identity_is_indeterminate_when_dependency_is_missing():
    _, equations, _ = _assets_equation()

    result = ConstraintVerifier(equations).verify(
        {
            "Assets": 100.0,
        }
    )

    assets_outcome = next(outcome for outcome in result.outcomes if outcome.target == "Assets")

    assert result.status == ConstraintStatus.INDETERMINATE
    assert assets_outcome.status == EquationStatus.INDETERMINATE
    assert assets_outcome.reason == "Missing dependency values"
    assert result.indeterminate == ["Assets"]


def test_assets_identity_is_derivable_when_target_is_missing():
    _, equations, _ = _assets_equation()

    result = ConstraintVerifier(equations).verify(
        {
            "LiabilitiesAndStockholdersEquity": 100.0,
        }
    )

    assets_outcome = next(outcome for outcome in result.outcomes if outcome.target == "Assets")

    assert result.status == ConstraintStatus.NOT_EVALUATED
    assert assets_outcome.status == EquationStatus.DERIVABLE
    assert assets_outcome.expected is None
    assert assets_outcome.actual is None
