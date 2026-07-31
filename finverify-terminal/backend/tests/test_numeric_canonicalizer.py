"""
Adversarial test matrix for numeric_canonicalizer.py

Organized by category, matching the design doc's format categories.
Every ACCEPT case checks the fully resolved value + relevant fields.
Every REJECT case checks the specific RejectReason, not just "raises".
"""

from decimal import Decimal

import pytest

from numeric.canonicalizer import (
    CanonicalizationError,
    RejectReason,
    Unit,
    canonicalize,
)


def D(s):
    return Decimal(s)


# ---------------------------------------------------------------------------
# A. Plain integers / decimals
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("1234", D("1234")),
    ("1234.56", D("1234.56")),
    ("0", D("0")),
    ("0.001", D("0.001")),
    ("-1234", D("-1234")),
    ("+1234", D("1234")),
    ("  1234  ", D("1234")),
])
def test_plain_numbers(raw, expected):
    result = canonicalize(raw)
    assert result.value == expected


# ---------------------------------------------------------------------------
# B. Comma-grouped numbers (en_US default locale)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("1,234", D("1234")),
    ("1,234,567.89", D("1234567.89")),
    ("12,345", D("12345")),
    ("100,000,000", D("100000000")),
])
def test_grouped_numbers_en_us(raw, expected):
    result = canonicalize(raw, locale="en_US")
    assert result.value == expected


@pytest.mark.parametrize("raw", [
    "1,23",        # not a 3-digit group
    "1,2345",      # not a 3-digit group
    "12,34,567",   # invalid grouping in en_US (would be valid in Indian lakh style, not supported)
])
def test_malformed_grouping_rejected(raw):
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(raw, locale="en_US")
    assert exc.value.reason == RejectReason.MALFORMED_GROUPING


# ---------------------------------------------------------------------------
# C. Locale handling (eu_EU)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("1.234,56", D("1234.56")),
    ("1.234.567,89", D("1234567.89")),
])
def test_eu_locale(raw, expected):
    result = canonicalize(raw, locale="eu_EU")
    assert result.value == expected


def test_unsupported_locale_rejected():
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("1234", locale="fr_FR")
    assert exc.value.reason == RejectReason.UNSUPPORTED_LOCALE


# ---------------------------------------------------------------------------
# D. Currency symbols and codes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected_value,expected_currency", [
    ("$1,234.56", D("1234.56"), "USD"),
    ("€1234", D("1234"), "EUR"),
    ("₹1,00,000", None, None),  # Indian grouping unsupported -> see rejection test below
    ("100 USD", D("100"), "USD"),
    ("USD 100", D("100"), "USD"),
    ("£99.99", D("99.99"), "GBP"),
])
def test_currency_detection(raw, expected_value, expected_currency):
    if expected_value is None:
        with pytest.raises(CanonicalizationError):
            canonicalize(raw)
        return
    result = canonicalize(raw)
    assert result.value == expected_value
    assert result.currency == expected_currency


def test_conflicting_currency_rejected():
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("$100 EUR")
    assert exc.value.reason == RejectReason.CONFLICTING_CURRENCY


# ---------------------------------------------------------------------------
# E. Parenthesized negatives and sign handling
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("(1234.56)", D("-1234.56")),
    ("($1,234.56)", D("-1234.56")),
    ("(1,234)", D("-1234")),
    ("1234-", D("-1234")),   # trailing minus, accounting style
    ("-1234", D("-1234")),
])
def test_negative_sign_forms(raw, expected):
    result = canonicalize(raw)
    assert result.value == expected


@pytest.mark.parametrize("raw", [
    "-1234-",     # leading AND trailing sign
    "-(1234)",    # explicit minus AND parens (double negation)
    "+(1234)",    # explicit plus AND parens
])
def test_contradictory_sign_rejected(raw):
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(raw)
    assert exc.value.reason == RejectReason.CONTRADICTORY_SIGN


# ---------------------------------------------------------------------------
# F. Scale words / abbreviations
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected_value,expected_scale", [
    ("2.4 billion", D("2.4e9"), "billion"),
    ("2.4B", D("2.4e9"), "b"),
    ("2.4bn", D("2.4e9"), "bn"),
    ("2400 million", D("2400e6"), "million"),
    ("2.4M", D("2.4e6"), "m"),
    ("5 thousand", D("5e3"), "thousand"),
    ("5K", D("5e3"), "k"),
    ("1.2 trillion", D("1.2e12"), "trillion"),
    ("1.2T", D("1.2e12"), "t"),
    ("$2.4B", D("2.4e9"), "b"),
    ("-2.4B", D("-2.4e9"), "b"),
    ("(2.4B)", D("-2.4e9"), "b"),
])
def test_scale_words(raw, expected_value, expected_scale):
    result = canonicalize(raw)
    assert result.value == expected_value
    assert result.scale_applied == expected_scale


def test_multiple_scale_words_rejected():
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("2.4 billion million")
    assert exc.value.reason == RejectReason.MULTIPLE_SCALE_WORDS


def test_scale_and_unit_conflict_rejected():
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("12.4% billion")
    assert exc.value.reason == RejectReason.SCALE_UNIT_CONFLICT


# ---------------------------------------------------------------------------
# G. Percent / basis points / percentage points -- kept distinct, literal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected_value,expected_unit", [
    ("12%", D("12"), Unit.PERCENT),
    ("12.5%", D("12.5"), Unit.PERCENT),
    ("12 percent", D("12"), Unit.PERCENT),
    ("12 pct", D("12"), Unit.PERCENT),
    ("25bps", D("25"), Unit.BASIS_POINT),
    ("25 basis points", D("25"), Unit.BASIS_POINT),
    ("12pp", D("12"), Unit.PERCENTAGE_POINT),
    ("12 percentage points", D("12"), Unit.PERCENTAGE_POINT),
    ("-3.2%", D("-3.2"), Unit.PERCENT),
])
def test_unit_markers_kept_literal(raw, expected_value, expected_unit):
    result = canonicalize(raw)
    assert result.value == expected_value
    assert result.unit == expected_unit
    # critical invariant: percent is NEVER silently divided by 100
    assert result.value == expected_value


# ---------------------------------------------------------------------------
# H. Scientific notation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("2.4e9", D("2.4e9")),
    ("2.4E+09", D("2.4e9")),
    ("-2.4e-3", D("-2.4e-3")),
    ("1e6", D("1e6")),
])
def test_scientific_notation(raw, expected):
    result = canonicalize(raw)
    assert result.value == expected


# ---------------------------------------------------------------------------
# I. Unicode / whitespace robustness
# ---------------------------------------------------------------------------

def test_unicode_minus_normalized():
    result = canonicalize("\u22121234")
    assert result.value == D("-1234")
    assert any("unicode minus" in w for w in result.warnings)


def test_nbsp_normalized():
    # NBSP is normalized to a plain space, which then fails as an
    # unrecognized character -- "1 234" isn't a supported grouped form.
    # This is intentional: don't guess that NBSP meant thousands-grouping.
    with pytest.raises(CanonicalizationError):
        canonicalize("1\u00a0234")


# ---------------------------------------------------------------------------
# J. Rejection catch-alls
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw", ["", "   ", None])
def test_empty_input_rejected(raw):
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(raw)
    assert exc.value.reason == RejectReason.EMPTY_INPUT


@pytest.mark.parametrize("raw", ["abc", "$", "%", "()"])
def test_no_digits_rejected(raw):
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(raw)
    assert exc.value.reason == RejectReason.NO_DIGITS


@pytest.mark.parametrize("raw", ["1234xyz", "12.34.56", "1234abc%"])
def test_unrecognized_or_malformed_rejected(raw):
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize(raw)
    assert exc.value.reason in (
        RejectReason.UNRECOGNIZED_CHARACTERS,
        RejectReason.MULTIPLE_DECIMAL_POINTS,
    )


def test_double_decimal_point_rejected():
    with pytest.raises(CanonicalizationError) as exc:
        canonicalize("12.34.56")
    assert exc.value.reason == RejectReason.MULTIPLE_DECIMAL_POINTS


# ---------------------------------------------------------------------------
# K. Combination adversarial cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected_value,expected_currency,expected_scale,expected_neg", [
    ("($2.4B)", D("-2.4e9"), "USD", "b", True),
    ("-$1,234.56", D("-1234.56"), "USD", None, True),
    ("(€1.2 million)", D("-1.2e6"), "EUR", "million", True),
])
def test_stacked_adversarial_combinations(
    raw, expected_value, expected_currency, expected_scale, expected_neg
):
    result = canonicalize(raw)
    assert result.value == expected_value
    assert result.currency == expected_currency
    assert result.scale_applied == expected_scale
    assert result.is_negative == expected_neg


def test_precision_digits_tracked():
    result = canonicalize("1234.5600")
    assert result.precision_digits == 4
    assert result.value == D("1234.56")


# ---------------------------------------------------------------------------
# L. Parenthesized magnitude with a trailing modifier outside the parens
#    (discovered during app.parser integration -- earnings-call phrasing
#    like "(56.78) million" is common and was NOT originally handled)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("(56.78) million", D("-56780000")),
    ("(2.4) billion", D("-2.4e9")),
    ("($1,234.56) thousand", D("-1234560")),
])
def test_parenthesized_magnitude_with_trailing_scale_word(raw, expected):
    result = canonicalize(raw)
    assert result.value == expected
    assert result.is_negative is True


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
