"""
Tests for finverify.dvl — Pure Python DVL verification.

This is a pytest port of finverify-terminal/sdk/tests/test_dvl.py,
covering the same cases against the module as vendored into this SDK.
"""

from finverify.dvl import DVLResult, verify_local


def test_scale_mul100_profit_margin():
    r = verify_local("What was the profit margin?", 0.2531)
    assert abs(r.verified_value - 25.31) < 0.01
    assert r.trust_score == "MEDIUM"
    assert r.was_corrected
    assert "scale_mul100" in r.correction_rules


def test_scale_mul100_revenue_growth():
    r = verify_local("What was the revenue growth rate?", 0.0623)
    assert abs(r.verified_value - 6.23) < 0.01
    assert r.trust_score == "MEDIUM"
    assert "scale_mul100" in r.correction_rules


def test_scale_div100():
    r = verify_local("What was the growth rate?", 1240.0)
    assert abs(r.verified_value - 12.40) < 0.01
    assert r.trust_score == "MEDIUM"
    assert "scale_div100" in r.correction_rules


def test_no_correction_ambiguous_range():
    r = verify_local("What was the CET1 ratio?", 10.935)
    assert abs(r.verified_value - 10.935) < 0.001
    assert r.trust_score == "HIGH"
    assert not r.was_corrected


def test_no_correction_pe_ratio():
    r = verify_local("What was the price to earnings ratio?", 28.5)
    assert abs(r.verified_value - 28.5) < 0.01
    assert r.trust_score == "HIGH"
    assert not r.was_corrected


def test_no_correction_non_ratio():
    r = verify_local("How many employees does the company have?", 0.5)
    assert abs(r.verified_value - 0.5) < 0.01
    assert r.trust_score == "HIGH"


def test_sign_correction_growth():
    r = verify_local("What was the revenue growth?", -0.08)
    assert r.verified_value > 0
    assert r.was_corrected


def test_sign_correction_decrease():
    r = verify_local("What was the decrease in expenses?", 0.12)
    assert r.verified_value < 0


def test_dvl_result_properties():
    r = verify_local("margin", 0.25)
    assert isinstance(r, DVLResult)
    assert r.question == "margin"
    assert r.raw_value == 0.25
    assert r.delta_pct > 0
    assert r.correction_summary is not None


def test_zero_value():
    r = verify_local("What was the change?", 0.0)
    assert r.verified_value == 0.0
    assert r.trust_score == "HIGH"


def test_large_magnitude():
    r = verify_local("total revenue", 1e12)
    assert r.verified_value > 0


def test_normalize_metric_name_exact_and_fuzzy():
    from finverify.normalizer import normalize_metric_name

    assert normalize_metric_name("net revenues") == "revenue"
    assert normalize_metric_name("cost of goods sold") == "cogs"
    assert normalize_metric_name("totally unrelated gibberish xyz") is None
