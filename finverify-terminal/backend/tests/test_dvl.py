"""
DVL Test Suite (pytest)
=======================
Tests the DVL verification engine and number parser against
the paper's known failure cases and tricky extraction inputs.

Usage: pytest tests/test_dvl.py   (from backend/ directory)
"""

import pytest

from app.parser import extract_number, extract_canonical, clean_llm_output
from app.dvl import full_verify, is_correct, format_correction_log, verify_canonical
from app.router import classify_query
from numeric.canonicalizer import Unit


# ---------------------------------------------------------------------------
# Number extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("$1,234.56", 1234.56),
        ("-0.3411", -0.3411),
        ("(1234)", -1234.0),
        ("The answer is 42.5%", 42.5),
        ("Revenue was $12,345,678", 12345678.0),
        ("+0.07004", 0.07004),
        # NOTE: this used to expect -56.78 -- the old regex-only parser had
        # no concept of scale words and silently dropped "million" entirely.
        # That was a real bug (see the parser/canonicalizer audit), not
        # intended behavior; the canonicalizer-backed implementation now
        # correctly expands the scale word.
        ("(56.78) million", -56780000.0),
        ("3.14159", 3.14159),
        ("-$999,999.99", -999999.99),
        ("0.001", 0.001),
    ],
)
def test_extract_number(text, expected):
    assert extract_number(text) == pytest.approx(expected, abs=1e-6)


def test_extract_number_handles_billion_word():
    """The specific bug the canonicalizer integration was built to fix."""
    assert extract_number("$2.4 billion") == pytest.approx(2.4e9, abs=1e-3)


def test_extract_number_handles_scientific_notation():
    assert extract_number("2.4e9") == pytest.approx(2.4e9, abs=1e-3)


# ---------------------------------------------------------------------------
# Canonical (structured) extraction
# ---------------------------------------------------------------------------


def test_extract_canonical_keeps_percent_literal():
    result = extract_canonical("The margin was 25.31%")
    assert result is not None
    assert result.unit == Unit.PERCENT
    assert float(result.value) == pytest.approx(25.31, abs=1e-6)


def test_extract_canonical_returns_none_for_unparseable_text():
    assert extract_canonical("no numbers in this sentence at all") is None


# ---------------------------------------------------------------------------
# DVL paper cases
# ---------------------------------------------------------------------------


def test_full_verify_cet1_ratio_unchanged():
    """Reasoning error: DVL should not fix the value."""
    verified, log, label, color = full_verify(
        "What was JPMorgan's CET1 ratio change?",
        0.07004,
        0.10935,
    )
    assert not is_correct(verified, 0.10935) or len(log) == 0
    # Trust is HIGH because DVL left it unchanged (reasoning error).
    assert label == "HIGH"


def test_full_verify_class_a_shares_magnitude_x10():
    """Magnitude error: DVL should multiply by 10."""
    verified, log, label, color = full_verify(
        "What was the increase in Class A shares outstanding?",
        104.0,
        995.0,
    )
    assert is_correct(verified, 995.0)
    assert any(e["rule"] == "magnitude_x10" for e in log)


def test_full_verify_htm_securities_compound_correction():
    """Compound error: scale_div100 then sign_corrected."""
    verified, log, label, color = full_verify(
        "What was the percentage decrease in HTM securities?",
        -34.11,
        0.34146,
    )
    assert is_correct(verified, 0.34146)
    rules = [e["rule"] for e in log]
    assert "scale_div100" in rules
    assert "sign_corrected" in rules


# ---------------------------------------------------------------------------
# Canonical-aware full_verify / verify_canonical
# ---------------------------------------------------------------------------


def test_full_verify_with_canonical_percent_skips_keyword_guessing():
    """
    Question has no RATIO_KEYWORDS hit, but the token was explicitly "%"
    in the source text -- canonical.unit should still trigger ratio
    handling instead of leaving the value untouched.
    """
    canonical = extract_canonical("34.11%")
    verified, log, label, color = full_verify(
        "What number appears in the filing?",  # no ratio keywords
        -34.11,
        0.34146,
        canonical=canonical,
    )
    assert is_correct(verified, 0.34146)


def test_full_verify_with_canonical_bps_skips_scale_heuristic():
    """
    Basis points live on a different scale than plain percentages;
    the scale_div100/scale_mul100 heuristic must not fire for them.
    """
    canonical = extract_canonical("850 bps")
    verified, log, label, color = full_verify(
        "What was the change in efficiency ratio?",
        850.0,
        None,
        canonical=canonical,
    )
    assert not any(e["rule"] in ("scale_div100", "scale_mul100") for e in log)
    assert verified == 850.0


def test_verify_canonical_threads_currency_and_scale_through():
    canonical = extract_canonical("$2.4 billion")
    result = verify_canonical("What was total revenue?", canonical, actual=2.4e9)
    assert result.currency == "USD"
    assert result.scale_applied in ("billion",)
    assert result.verified_value == pytest.approx(2.4e9, rel=1e-9)


# ---------------------------------------------------------------------------
# LLM output cleaning
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Answer: 42.5", 42.5),
        ("The answer is $1,234", 1234.0),
        ("Therefore, (56.78)", -56.78),
        ("Question: blah\nAnswer: 0.3411", 0.3411),
    ],
)
def test_clean_llm_output(raw, expected):
    cleaned, number = clean_llm_output(raw)
    assert number is not None
    assert number == pytest.approx(expected, abs=1e-6)


# ---------------------------------------------------------------------------
# Ambiguous scale without ground truth
# ---------------------------------------------------------------------------


def test_ambiguous_scale_no_ground_truth():
    """CET1 ratio 10.935 without actual should remain unchanged."""
    verified, log, label, color = full_verify(
        "What was JPMorgan's CET1 ratio?",
        10.935,
        None,
    )
    assert verified == pytest.approx(10.935, abs=1e-9)
    assert len(log) == 0


# ---------------------------------------------------------------------------
# Query classifier
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query,expected",
    [
        ("What was the CET1 ratio?", "numerical"),
        ("Should I buy Apple stock?", "advisory"),
        ("What is JPMorgan's revenue growth?", "financial_reasoning"),
        ("What is Apple's gross margin?", "financial_reasoning"),
        ("Compare revenue YoY for Nvidia", "financial_reasoning"),
        ("Which stock should I invest in?", "advisory"),
        ("Tell me about quarterly reports", "general"),
        ("What was the YoY margin change?", "numerical"),
        ("Recommend a portfolio allocation", "advisory"),
    ],
)
def test_classify_query(query, expected):
    assert classify_query(query) == expected


# ---------------------------------------------------------------------------
# Correction log formatting
# ---------------------------------------------------------------------------


def test_format_correction_log_empty():
    assert format_correction_log([]) == []


def test_format_correction_log_preserves_rule():
    log = [{"rule": "magnitude_x10", "before": 104.0, "after": 1040.0}]
    formatted = format_correction_log(log)
    assert len(formatted) == 1
    assert formatted[0]["rule"] == "magnitude_x10"
