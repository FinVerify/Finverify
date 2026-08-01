"""Tests for Phase 6.2 constraint semantics."""

from __future__ import annotations

import pytest

from core.financial.constraints.models import (
    ConstraintStatus,
    Dependency,
    Dimension,
    Equation,
    EquationStatus,
    Variable,
)
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


def test_records_verified_outcome_when_target_and_dependencies_are_present():
    result = ConstraintVerifier([make_equation("GrossMargin", "(Revenue - COGS) / Revenue")]).verify(
        {"Revenue": 100.0, "COGS": 60.0, "GrossMargin": 0.4}
    )

    assert result.status == ConstraintStatus.CONSISTENT
    assert result.consistent is True
    assert result.coverage.verified == 1
    assert result.coverage.applicable == 1
    assert result.outcomes[0].status == EquationStatus.VERIFIED
    assert result.outcomes[0].expected == pytest.approx(0.4)
    assert result.outcomes[0].actual == pytest.approx(0.4)


def test_records_violation_outcome_when_target_disagrees_with_formula():
    result = ConstraintVerifier([make_equation("GrossMargin", "(Revenue - COGS) / Revenue")]).verify(
        {"Revenue": 100.0, "COGS": 60.0, "GrossMargin": 0.5}
    )

    assert result.status == ConstraintStatus.INCONSISTENT
    assert result.consistent is False
    assert result.coverage.violated == 1
    assert result.outcomes[0].status == EquationStatus.VIOLATION
    assert result.outcomes[0].expected == pytest.approx(0.4)
    assert result.outcomes[0].actual == pytest.approx(0.5)
    assert result.violations[0].metric == "GrossMargin"


def test_records_indeterminate_outcome_when_target_present_but_dependencies_missing():
    result = ConstraintVerifier([make_equation("GrossMargin", "(Revenue - COGS) / Revenue")]).verify(
        {"Revenue": 100.0, "GrossMargin": 0.4}
    )

    assert result.status == ConstraintStatus.INDETERMINATE
    assert result.consistent is None
    assert result.coverage.indeterminate == 1
    assert result.outcomes[0].status == EquationStatus.INDETERMINATE
    assert result.outcomes[0].reason == "Missing dependency values"
    assert result.indeterminate == ["GrossMargin"]
    assert result.indeterminate_reasons["GrossMargin"] == "Missing dependency values"


def test_records_derivable_outcome_when_target_missing_but_dependencies_complete():
    result = ConstraintVerifier([make_equation("GrossMargin", "(Revenue - COGS) / Revenue")]).verify(
        {"Revenue": 100.0, "COGS": 60.0}
    )

    assert result.status == ConstraintStatus.NOT_EVALUATED
    assert result.consistent is None
    assert result.coverage.derivable == 1
    assert result.coverage.applicable == 0
    assert result.outcomes[0].status == EquationStatus.DERIVABLE
    assert result.outcomes[0].expected is None
    assert result.outcomes[0].actual is None


def test_records_not_applicable_outcome_when_target_and_dependencies_are_missing():
    result = ConstraintVerifier([make_equation("GrossMargin", "(Revenue - COGS) / Revenue")]).verify(
        {"Revenue": 100.0}
    )

    assert result.status == ConstraintStatus.NOT_EVALUATED
    assert result.consistent is None
    assert result.coverage.not_applicable == 1
    assert result.outcomes[0].status == EquationStatus.NOT_APPLICABLE
    assert result.outcomes[0].reason == "Target not reported and dependency values are incomplete"


def test_status_prefers_inconsistent_over_indeterminate():
    verifier = ConstraintVerifier(
        [
            make_equation("GrossProfit", "Revenue - COGS"),
            make_equation("GrossMargin", "GrossProfit / Revenue"),
        ]
    )

    result = verifier.verify({"Revenue": 100.0, "GrossProfit": 50.0, "GrossMargin": 0.6})

    assert result.status == ConstraintStatus.INCONSISTENT
    assert result.consistent is False
    assert result.coverage.violated == 1
    assert result.coverage.indeterminate == 1


def test_status_is_consistent_when_verified_outcomes_exist_alongside_derivable_ones():
    verifier = ConstraintVerifier(
        [
            make_equation("GrossProfit", "Revenue - COGS"),
            make_equation("GrossMargin", "GrossProfit / Revenue"),
        ]
    )

    result = verifier.verify({"Revenue": 100.0, "COGS": 60.0, "GrossProfit": 40.0, "GrossMargin": None})

    assert result.status == ConstraintStatus.CONSISTENT
    assert result.consistent is True
    assert result.coverage.verified == 1
    assert result.coverage.derivable == 1


def test_status_is_indeterminate_when_any_applicable_equation_is_indeterminate_and_none_violate():
    verifier = ConstraintVerifier(
        [
            make_equation("GrossProfit", "Revenue - COGS"),
            make_equation("GrossMargin", "GrossProfit / Revenue"),
        ]
    )

    result = verifier.verify({"Revenue": 100.0, "GrossProfit": 40.0, "GrossMargin": 0.4})

    assert result.status == ConstraintStatus.INDETERMINATE
    assert result.consistent is None
    assert result.coverage.verified == 1
    assert result.coverage.indeterminate == 1


def test_status_is_not_evaluated_when_only_non_applicable_outcomes_exist():
    verifier = ConstraintVerifier(
        [
            make_equation("GrossProfit", "Revenue - COGS"),
            make_equation("GrossMargin", "GrossProfit / Revenue"),
        ]
    )

    result = verifier.verify({"Revenue": 100.0})

    assert result.status == ConstraintStatus.NOT_EVALUATED
    assert result.consistent is None
    assert result.coverage.loaded == 2
    assert result.coverage.verified == 0
    assert result.coverage.violated == 0
    assert result.coverage.indeterminate == 0
    assert result.coverage.derivable == 0
    assert result.coverage.not_applicable == 2


def test_dimension_mismatch_produces_indeterminate_outcome():
    parser = FormulaParser()
    expression = parser.parse("Revenue + GrossMargin")
    target = Variable(name="InvalidMetric", dimension=Dimension.CURRENCY)
    equation = Equation(
        target=target,
        expression=expression,
        dependencies=(
            Dependency(source=Variable(name="Revenue", dimension=Dimension.CURRENCY), target=target),
            Dependency(source=Variable(name="GrossMargin", dimension=Dimension.PERCENTAGE), target=target),
        ),
        dimension=Dimension.CURRENCY,
    )

    result = ConstraintVerifier([equation]).verify(
        {
            "Revenue": {"value": 100.0, "dimension": "currency"},
            "GrossMargin": {"value": 0.4, "dimension": "percentage"},
            "InvalidMetric": 100.4,
        }
    )

    assert result.status == ConstraintStatus.INDETERMINATE
    assert result.consistent is None
    assert result.outcomes[0].status == EquationStatus.INDETERMINATE
    assert "Cannot add currency and percentage" in result.outcomes[0].reason


def test_zero_division_produces_indeterminate_outcome():
    result = ConstraintVerifier([make_equation("GrossMargin", "GrossProfit / Revenue")]).verify(
        {"Revenue": 0.0, "GrossProfit": 10.0, "GrossMargin": 0.0}
    )

    assert result.status == ConstraintStatus.INDETERMINATE
    assert result.consistent is None
    assert result.coverage.indeterminate == 1
    assert result.outcomes[0].status == EquationStatus.INDETERMINATE
