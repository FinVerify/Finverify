"""Rule-level and integration parity tests for the modular math engine."""

import pytest

from app.dvl import full_verify
from core.engine import verify
from core.math_engine.engine import MathEngine
from core.math_engine.rules import MagnitudeRule, ScaleRule, SignRule
from core.models import Claim, VerificationContext


def make_context(claim: Claim, *, current_value: float | None = None) -> VerificationContext:
    return VerificationContext(
        claim=claim,
        entity=claim.entity,
        metric=claim.metric,
        period=claim.period,
        metadata=dict(claim.metadata),
        current_value=claim.raw_value if current_value is None else current_value,
    )


def test_scale_rule_compound_lookahead_matches_legacy_behavior():
    claim = Claim(
        question="What was the percentage decrease in HTM securities?",
        raw_value=-34.11,
        actual_value=0.34146,
    )
    result = ScaleRule().evaluate(claim, make_context(claim))
    assert result.applied is True
    assert result.metadata["correction"]["rule"] == "scale_div100"
    assert result.corrected_value == pytest.approx(-0.3411, abs=1e-9)


def test_scale_rule_ambiguous_range_without_actual_stays_unchanged():
    claim = Claim(
        question="What was JPMorgan's CET1 ratio?",
        raw_value=10.935,
        actual_value=None,
    )
    context = make_context(claim)
    result = ScaleRule().evaluate(claim, context)
    assert result.applied is False
    assert context.ambiguous_scale is True
    assert context.current_value == pytest.approx(10.935, abs=1e-9)


def test_sign_rule_flips_only_when_sign_is_the_remaining_error():
    claim = Claim(
        question="What was the percentage decrease in HTM securities?",
        raw_value=-34.11,
        actual_value=0.34146,
    )
    result = SignRule().evaluate(claim, make_context(claim, current_value=-0.3411))
    assert result.applied is True
    assert result.metadata["correction"]["rule"] == "sign_corrected"
    assert result.corrected_value == pytest.approx(0.3411, abs=1e-9)


def test_magnitude_rule_matches_legacy_x10_case():
    claim = Claim(
        question="What was the increase in Class A shares outstanding?",
        raw_value=104.0,
        actual_value=995.0,
    )
    result = MagnitudeRule().evaluate(claim, make_context(claim))
    assert result.applied is True
    assert result.metadata["correction"]["rule"] == "magnitude_x10"
    assert result.corrected_value == pytest.approx(1040.0, abs=1e-9)


@pytest.mark.parametrize(
    "question,raw_value,actual_value",
    [
        ("What was JPMorgan's CET1 ratio change?", 0.07004, 0.10935),
        ("What was the increase in Class A shares outstanding?", 104.0, 995.0),
        ("What was the percentage decrease in HTM securities?", -34.11, 0.34146),
        ("What was the profit margin?", 0.2531, None),
        ("What was the revenue growth rate?", 0.0, None),
        ("What was the net income increase?", -1234.0, None),
        ("What was the price to earnings ratio?", 28.5, None),
        ("What was the return on assets?", 1500000000000.0, None),
    ],
)
def test_math_engine_legacy_tuple_matches_full_verify(question, raw_value, actual_value):
    claim = Claim(question=question, raw_value=raw_value, actual_value=actual_value)
    context = make_context(claim)
    engine = MathEngine()
    math_result = engine.run(claim, context)
    legacy_tuple = engine.to_legacy_tuple(math_result, claim, context)
    assert legacy_tuple == full_verify(question, raw_value, actual_value)
    assert len(math_result.rule_trace.results) >= 3


def test_core_verify_matches_legacy_dvl_output_for_known_case():
    claim = Claim(
        question="What was the percentage decrease in HTM securities?",
        raw_value=-34.11,
        actual_value=0.34146,
    )
    verified, raw_log, _label, _color = full_verify(claim.question, claim.raw_value, claim.actual_value)
    result = verify(claim)
    assert result.verified_value == pytest.approx(verified, abs=1e-9)
    assert [entry["rule"] for entry in result.correction_log] == [entry["rule"] for entry in raw_log]
    assert result.trust_score.label == "LOW"
    assert result.trust_score.color == "#f87171"
    assert "findings" not in result.trust_score.model_dump()


def test_core_verify_missing_number_returns_legacy_low_trust_shape():
    result = verify(Claim(question="What was the revenue growth rate?", raw_value=None))
    assert result.verified_value is None
    assert result.correction_log == []
    assert result.trust_score.label == "LOW"
    assert result.verified is False
