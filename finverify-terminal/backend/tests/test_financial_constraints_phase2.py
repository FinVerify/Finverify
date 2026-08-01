"""Phase 2 tests for the financial constraint graph and verifier."""

from __future__ import annotations

import pytest

from core.financial.constraints.graph import ConstraintGraph
from core.financial.constraints.models import ConstraintStatus, Dependency, Equation, Variable
from core.financial.constraints.parser import FormulaParser
from core.financial.constraints.verifier import ConstraintVerifier


def make_equation(target: str, formula: str) -> Equation:
    parser = FormulaParser()
    expression = parser.parse(formula)
    target_variable = Variable(name=target)
    dependencies = tuple(
        Dependency(source=Variable(name=name), target=target_variable)
        for name in expression.variable_names()
    )
    return Equation(
        target=target_variable,
        expression=expression,
        dependencies=dependencies,
    )


def test_graph_builds_correctly():
    equations = [
        make_equation("GrossProfit", "Revenue - COGS"),
        make_equation("GrossMargin", "GrossProfit / Revenue"),
        make_equation("OperatingProfit", "GrossProfit - OperatingExpenses"),
    ]

    graph = ConstraintGraph(equations)

    assert graph.nodes == (
        "COGS",
        "GrossMargin",
        "GrossProfit",
        "OperatingExpenses",
        "OperatingProfit",
        "Revenue",
    )
    assert graph.edges() == (
        ("COGS", "GrossProfit"),
        ("GrossProfit", "GrossMargin"),
        ("GrossProfit", "OperatingProfit"),
        ("OperatingExpenses", "OperatingProfit"),
        ("Revenue", "GrossMargin"),
        ("Revenue", "GrossProfit"),
    )
    assert graph.get_dependencies("GrossProfit") == ("COGS", "Revenue")
    assert graph.get_dependents("GrossProfit") == ("GrossMargin", "OperatingProfit")
    assert graph.topological_order() == (
        "COGS",
        "OperatingExpenses",
        "Revenue",
        "GrossProfit",
        "GrossMargin",
        "OperatingProfit",
    )


def test_cycle_detection():
    equations = [
        make_equation("A", "B"),
        make_equation("B", "C"),
        make_equation("C", "A"),
    ]

    with pytest.raises(ValueError, match=r"Cycle detected: A -> C -> B -> A|Cycle detected: C -> B -> A -> C|Cycle detected: B -> A -> C -> B"):
        ConstraintGraph(equations)


def test_consistent_claims():
    verifier = ConstraintVerifier(
        [
            make_equation("GrossProfit", "Revenue - COGS"),
            make_equation("GrossMargin", "GrossProfit / Revenue"),
        ]
    )

    result = verifier.verify(
        {
            "Revenue": 100.0,
            "COGS": 60.0,
            "GrossProfit": 40.0,
            "GrossMargin": 0.4,
        }
    )

    assert result.status == ConstraintStatus.CONSISTENT
    assert result.consistent is True
    assert result.coverage.verified == 2
    assert result.violations == []
    assert result.indeterminate == []


def test_inconsistent_claims():
    verifier = ConstraintVerifier(
        [
            make_equation("GrossProfit", "Revenue - COGS"),
            make_equation("GrossMargin", "GrossProfit / Revenue"),
        ]
    )

    result = verifier.verify(
        {
            "Revenue": 100.0,
            "COGS": 60.0,
            "GrossProfit": 40.0,
            "GrossMargin": 0.5,
        }
    )

    assert result.status == ConstraintStatus.INCONSISTENT
    assert result.consistent is False
    assert result.coverage.violated == 1
    assert result.indeterminate == []
    assert len(result.violations) == 1

    violation = result.violations[0]
    assert violation.metric == "GrossMargin"
    assert violation.expected == pytest.approx(0.4)
    assert violation.actual == pytest.approx(0.5)
    assert violation.formula == "GrossProfit / Revenue"
    assert violation.dependencies == {"GrossProfit": 40.0, "Revenue": 100.0}


def test_indeterminate_claims():
    verifier = ConstraintVerifier(
        [
            make_equation("GrossProfit", "Revenue - COGS"),
            make_equation("GrossMargin", "GrossProfit / Revenue"),
        ]
    )

    result = verifier.verify(
        {
            "Revenue": 100.0,
            "GrossProfit": 40.0,
            "GrossMargin": 0.4,
        }
    )

    assert result.status == ConstraintStatus.INDETERMINATE
    assert result.consistent is None
    assert result.coverage.verified == 1
    assert result.coverage.indeterminate == 1
    assert result.violations == []
    assert result.indeterminate == ["GrossProfit"]


def test_mixed_violations_and_indeterminate():
    verifier = ConstraintVerifier(
        [
            make_equation("GrossProfit", "Revenue - COGS"),
            make_equation("GrossMargin", "GrossProfit / Revenue"),
        ]
    )

    result = verifier.verify(
        {
            "Revenue": 100.0,
            "GrossProfit": 50.0,
            "GrossMargin": 0.6,
        }
    )

    assert result.status == ConstraintStatus.INCONSISTENT
    assert result.consistent is False
    assert result.coverage.violated == 1
    assert result.coverage.indeterminate == 1
    assert result.indeterminate == ["GrossProfit"]
    assert len(result.violations) == 1
    assert result.violations[0].metric == "GrossMargin"
    assert result.violations[0].expected == pytest.approx(0.5)
    assert result.violations[0].actual == pytest.approx(0.6)
