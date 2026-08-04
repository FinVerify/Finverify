"""
Regression tests for the numeric.canonicalizer integration in
ingestion/transcripts.py.

tests/test_transcripts.py already covers the regex pipeline and
downstream question-building/report logic end-to-end, and all of it
passes unchanged against this refactor -- that's the primary
regression guard. This file adds targeted tests for the specific
thing that changed: how a regex match's captured groups get turned
into a numeric value.

Structure:
  1. An exact old-vs-new parity oracle, run across every sample
     transcript, comparing every single extracted claim.
  2. Targeted tests for each _build_canonicalization_token() branch.
  3. Tests for the one deliberate behavior improvement (malformed
     comma grouping is now rejected instead of silently mis-parsed).
  4. A regression lock on per-ticker claim counts and a few
     previously-untested tickers/values (only AAPL was spot-checked
     in the original test file).
"""

import re

import pytest

from ingestion.transcripts import (
    CLAIM_PATTERNS,
    SAMPLE_TRANSCRIPTS,
    SCALE_MAP,
    extract_claims,
    _build_canonicalization_token,
)


# ---------------------------------------------------------------------------
# 1. Old-vs-new parity oracle
# ---------------------------------------------------------------------------
#
# This is the pre-refactor extract_claims() body, preserved verbatim as a
# reference oracle. It is intentionally NOT imported from transcripts.py --
# the whole point is to compare the new implementation against the exact
# old one, independent of any future changes to either.

def _reference_extract_claims_old_implementation(text: str) -> list[dict]:
    claims = []
    seen_matches = set()

    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|\n+', text)
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue

        for pattern, claim_type in CLAIM_PATTERNS:
            matches = re.finditer(pattern, sentence, re.IGNORECASE)
            for m in matches:
                try:
                    num_str = m.group(1).replace(",", "")
                    value = float(num_str)

                    scale_label = None
                    if m.lastindex and m.lastindex >= 2:
                        scale_label = m.group(2)
                        if scale_label and scale_label in SCALE_MAP:
                            value *= SCALE_MAP[scale_label]

                    bps_original = None
                    if claim_type == 'bps':
                        bps_original = value
                        value = value / 100.0

                    match_key = f"{sentence[:50]}:{m.group(0)}"
                    if match_key in seen_matches:
                        continue
                    seen_matches.add(match_key)

                    claim = {
                        "sentence": sentence[:200],
                        "raw_value": value,
                        "claim_type": claim_type,
                        "match": m.group(0),
                    }
                    if bps_original is not None:
                        claim["bps_original"] = bps_original
                    if scale_label:
                        claim["scale_label"] = scale_label

                    claims.append(claim)
                except (ValueError, IndexError):
                    continue

    return claims


def _comparable_key(claim: dict) -> tuple:
    """(sentence, match, claim_type) -- identifies "the same claim" across
    old and new implementations, independent of any additive metadata
    (currency/unit) the new implementation attaches."""
    return (claim["sentence"], claim["match"], claim["claim_type"])


_PHANTOM_TRUNCATED_MATCH_RE = re.compile(r'^\$\d+\.$')


def _is_known_phantom_truncated_match(claim: dict) -> bool:
    """
    Identifies a specific pre-existing bug in CLAIM_PATTERNS' currency_raw
    pattern, discovered while building this oracle: for input like
    "$46.2 billion", the negative lookahead `(?!\\s*(?:billion|...))`
    causes the greedy `[\\d,.]+` to backtrack to a truncated match like
    "$46." (missing the ".2"), because "$46." is NOT followed by
    "billion" (the "2" is). Old code's `float("46.")` == 46.0 succeeded
    silently, producing a phantom currency_raw claim with a wrong,
    truncated value -- 46.0 instead of the real 46.2 billion, which is
    already captured correctly and separately by the 'currency' pattern
    match on the same sentence.

    The canonicalizer correctly rejects "46." (a decimal point with no
    trailing digits), eliminating this phantom claim entirely. That is a
    genuine bug fix, not a regression, so the parity oracle explicitly
    carves it out here instead of either failing on it or silently
    ignoring all differences.
    """
    return (
        claim["claim_type"] == "currency_raw"
        and bool(_PHANTOM_TRUNCATED_MATCH_RE.match(claim["match"]))
    )


@pytest.mark.parametrize("ticker", list(SAMPLE_TRANSCRIPTS.keys()))
def test_exact_parity_with_old_implementation(ticker):
    """
    For every sample transcript, the new canonicalizer-backed
    extract_claims() must produce exactly the same set of claims (by
    sentence+match+type) with exactly the same raw_value, bps_original,
    and scale_label as the old regex+SCALE_MAP implementation --
    EXCEPT for the one class of claim documented in
    _is_known_phantom_truncated_match(), which the new implementation
    correctly drops as a bug fix.
    """
    text = SAMPLE_TRANSCRIPTS[ticker]
    old_claims = _reference_extract_claims_old_implementation(text)
    new_claims = extract_claims(text)

    old_by_key = {_comparable_key(c): c for c in old_claims}
    new_by_key = {_comparable_key(c): c for c in new_claims}

    only_in_old = set(old_by_key) - set(new_by_key)
    unexplained = {k for k in only_in_old if not _is_known_phantom_truncated_match(old_by_key[k])}
    assert not unexplained, (
        f"{ticker}: claims present in old but missing in new, and NOT "
        f"explained by the known phantom-match bug fix: {unexplained}"
    )

    only_in_new = set(new_by_key) - set(old_by_key)
    assert not only_in_new, f"{ticker}: unexpected new-only claims: {only_in_new}"

    for key, old_claim in old_by_key.items():
        if key not in new_by_key:
            continue  # accounted for above as a known, deliberate fix
        new_claim = new_by_key[key]
        assert new_claim["raw_value"] == pytest.approx(old_claim["raw_value"], rel=1e-9), (
            f"{ticker}: raw_value mismatch for {key}: "
            f"old={old_claim['raw_value']} new={new_claim['raw_value']}"
        )
        assert new_claim.get("bps_original") == old_claim.get("bps_original")
        assert new_claim.get("scale_label") == old_claim.get("scale_label")


def test_phantom_truncated_currency_matches_are_fixed_not_regressed():
    """
    Explicit, positive assertion of the bug fix itself (not just its
    absence): "$46.2 billion" no longer also produces a phantom
    currency_raw claim of 46.0.
    """
    claims = extract_claims("Revenue was $46.2 billion for the quarter overall.")
    phantom = [c for c in claims if c["claim_type"] == "currency_raw" and c["raw_value"] == 46.0]
    assert phantom == []
    # The real value is still captured correctly by the 'currency' pattern.
    real = [c for c in claims if c["claim_type"] == "currency" and c["raw_value"] == pytest.approx(46.2e9)]
    assert len(real) == 1


def test_trailing_comma_artifact_still_recovers_real_value():
    """
    Positive assertion for the companion fix: "$1.64, up from..." must
    still yield a correct 1.64 claim (recovering a value that a naive
    "reject anything with a stray comma" approach would have lost).
    """
    claims = extract_claims("EPS was $1.64, up from $1.52 a year ago overall.")
    eps_claims = [c for c in claims if c["claim_type"] == "eps"]
    assert len(eps_claims) == 1
    assert eps_claims[0]["raw_value"] == pytest.approx(1.64)


def test_exact_parity_claim_counts_locked_per_ticker():
    """
    Explicit regression lock on total claim counts per ticker (the
    original test file only spot-checked AAPL in this much detail).
    If this changes, something about extraction behavior changed --
    intentionally or not.

    Counts are two higher than a naive byte-for-byte port of the old
    implementation would produce for AAPL/NVDA/MSFT (+2 each) and JPM
    (+1): those are recovered "EPS was $X.XX," / "$X.XX," claims that
    the old blind comma-stripping happened to parse correctly but a
    naive direct port of the new stricter canonicalizer would have
    dropped, before the trailing-comma fix in
    _build_canonicalization_token(). See
    test_trailing_comma_artifact_still_recovers_real_value().

    PHASE 7A UPDATE: counts for AAPL (-2), NVDA (-1), and GS (-2) dropped
    again after fixing a second, previously-unaddressed instance of the
    same currency_raw backtracking behavior described in
    _is_known_phantom_truncated_match() above. That carve-out only
    covered the case where the backtracked residue was rejected by the
    canonicalizer (a trailing decimal point, e.g. "$46."). It missed the
    case where the residue is itself a syntactically valid number that
    the canonicalizer happily accepts -- e.g. "$153 billion" backtracks
    to "$15" (153 -> 15, with "3 billion" left over, which doesn't start
    with "billion" so the old lookahead let it through), silently
    producing a wrong, real-looking phantom claim (15.0) instead of being
    rejected outright. This was only caught via real-data validation
    against NVDA's actual Q4 FY2025 8-K exhibit text ("$570 million" ->
    phantom "$57"), then confirmed present in AAPL ("$153 billion" ->
    phantom "$15", "$29 billion" -> phantom "$2") and GS ("$351 million"
    -> phantom "$35", "$934 million" -> phantom "$93") samples too. Fixed
    at the regex level in CLAIM_PATTERNS' currency_raw pattern (see its
    definition and comment in ingestion/transcripts.py) rather than
    relying on the canonicalizer to reject it, since not every backtrack
    residue is invalid. TSLA/JPM/MSFT counts are unaffected because none
    of their sample sentences happen to contain a "$NNN million/billion"
    figure whose backtrack residue is itself a valid number.

    PHASE 7F UPDATE: counts for AAPL (+1), NVDA (+1), and GS (+1) rose
    again after intentionally broadening the 'revenue' claim_type pattern
    to fix two proven real-data extraction gaps (see CLAIM_PATTERNS'
    'revenue' entry and its comment in ingestion/transcripts.py):
      - AAPL +1: "Services revenue reached an all-time high of $24.2
        billion" is now extracted as claim_type='revenue' (it wasn't
        before, since "reached an all-time high" sat between "revenue"
        and the connector/number). Correctly tagged scope="segment" and
        stays unmapped -- see test_transcript_claim_context.py.
      - NVDA +1: "Revenue was a record $39.3 billion" -- NVIDIA's own
        headline figure -- is now extracted (the filler "a record"
        previously broke the match the same way the real 8-K exhibit
        text's fuller clause did). Correctly tagged scope="company" and
        is now eligible for mapping.
      - GS +1: "Net revenues were $13.9 billion" -- plural "revenues" plus
        the "were" connector -- is now extracted (previously matched
        nothing at all for claim_type='revenue'). Correctly tagged
        scope="company".
    TSLA/JPM/MSFT counts are unaffected because none of their sample
    sentences trip the broadened lookahead in a way that produces a new
    match (JPM's/TSLA's segment-revenue sentences either already matched
    under the old adjacency-only pattern, or still lack any of
    of/was/were/: as a standalone word between "revenue" and the number
    and so still don't match under the new pattern either -- e.g. TSLA's
    "Energy revenue grew 67% ... to $3.1 billion").
    """
    expected_counts = {
        "AAPL": 35,
        "TSLA": 32,
        "JPM": 37,
        "NVDA": 44,
        "MSFT": 42,
        "GS": 47,
    }
    for ticker, expected in expected_counts.items():
        claims = extract_claims(SAMPLE_TRANSCRIPTS[ticker])
        assert len(claims) == expected, f"{ticker}: expected {expected} claims, got {len(claims)}"


# ---------------------------------------------------------------------------
# 2. _build_canonicalization_token() unit tests
# ---------------------------------------------------------------------------


def _match_for(pattern: str, text: str) -> "re.Match":
    m = re.search(pattern, text, re.IGNORECASE)
    assert m is not None, f"pattern did not match {text!r}"
    return m


@pytest.mark.parametrize(
    "claim_type,pattern,text,expected_token",
    [
        ("currency", r'\$\s*([\d,.]+)\s*(billion|million|thousand|B|M|K|bn|mn)',
         "$94.9 billion", "$94.9 billion"),
        ("currency_raw", r'\$\s*([\d,.]+)(?!\s*(?:billion|million|thousand|B|M|K|bn|mn))',
         "$1.64", "$1.64"),
        ("percentage", r'([\d,.]+)\s*%', "46.6%", "46.6%"),
        ("bps", r'([\d,.]+)\s*(?:basis\s*points?|bps)', "240 basis points", "240 bps"),
        ("growth_pct", r'(?:grew|growth|increased|rose|up|gained|improved|expanded)\s+([\d,.]+)\s*%',
         "grew 15%", "15%"),
        ("decline_pct", r'(?:declined?|decreased?|fell|down|dropped|contracted|narrowed)\s+([\d,.]+)\s*%',
         "declined 11%", "11%"),
        ("shares", r'([\d,.]+)\s*(?:million|billion)\s*shares',
         "10.4 million shares", "10.4"),
        ("eps", r'EPS\s*(?:of|was|:)?\s*\$?\s*([\d,.]+)', "EPS was $0.89", "0.89"),
        ("margin", r'margin\s*(?:of|was|:)?\s*([\d,.]+)\s*%?', "margin was 43.1%", "43.1"),
        ("revenue", r'revenue\s*(?:of|was|:)?\s*\$?\s*([\d,.]+)\s*(billion|million|B|M|bn|mn)?',
         "revenue of $25.2 billion", "25.2 billion"),
        ("ratio", r'(?:CET1|tier\s*1|capital)\s*(?:ratio)?\s*(?:of|was|:)?\s*([\d,.]+)\s*%?',
         "CET1 ratio was 15.3%", "15.3"),
        ("return_metric", r'(?:return|ROTCE|ROE|ROA)\s*(?:on\s*\w+\s*\w*)?\s*(?:of|was|:)?\s*([\d,.]+)\s*%?',
         "Return on equity was 12.7%", "12.7"),
    ],
)
def test_build_canonicalization_token(claim_type, pattern, text, expected_token):
    m = _match_for(pattern, text)
    assert _build_canonicalization_token(claim_type, m) == expected_token


def test_build_canonicalization_token_shares_ignores_scale_word():
    """
    Documents the preserved pre-existing limitation: the 'shares' pattern
    never captures the scale word as a group, so the token intentionally
    excludes it -- exactly matching the old implementation's behavior of
    never multiplying share counts by the stated scale.
    """
    m = _match_for(r'([\d,.]+)\s*(?:million|billion)\s*shares', "500 billion shares")
    assert _build_canonicalization_token("shares", m) == "500"


# ---------------------------------------------------------------------------
# 3. Deliberate behavior improvement: malformed grouping is now rejected
#    instead of silently mis-parsed by blind comma-stripping
# ---------------------------------------------------------------------------


def test_malformed_comma_grouping_is_skipped_not_silently_wrong():
    """
    Old behavior: '$1,23 million'.replace(',', '') -> '123' -> * 1e6 ->
    123,000,000 -- silently wrong, since '1,23' isn't valid grouping.
    New behavior: the canonicalizer rejects malformed grouping outright,
    so no claim is emitted rather than a fabricated value.
    """
    claims = extract_claims("Revenue was $1,23 million for the quarter overall.")
    assert claims == []


def test_well_formed_comma_grouping_still_works():
    claims = extract_claims("Revenue was $1,234 million for the quarter overall.")
    currency_claims = [c for c in claims if c["claim_type"] == "currency"]
    assert len(currency_claims) == 1
    assert currency_claims[0]["raw_value"] == pytest.approx(1_234_000_000.0)


# ---------------------------------------------------------------------------
# 4. Additive metadata now available from the canonicalizer
# ---------------------------------------------------------------------------


def test_currency_metadata_attached_for_dollar_claims():
    claims = extract_claims(SAMPLE_TRANSCRIPTS["NVDA"])
    full_year = [c for c in claims if abs(c["raw_value"] - 130_500_000_000) < 1]
    assert len(full_year) >= 1
    currency_type_claims = [c for c in full_year if c["claim_type"] == "currency"]
    assert len(currency_type_claims) == 1
    assert currency_type_claims[0]["currency"] == "USD"


def test_unit_metadata_attached_for_bps_claims():
    claims = extract_claims(SAMPLE_TRANSCRIPTS["GS"])
    bps_claims = [c for c in claims if c.get("bps_original") == 850.0]
    assert len(bps_claims) == 1
    assert bps_claims[0]["unit"] == "basis_point"
    assert bps_claims[0]["raw_value"] == pytest.approx(8.5)


# ---------------------------------------------------------------------------
# 5. Backward compatibility: SCALE_MAP / CLAIM_PATTERNS remain importable
# ---------------------------------------------------------------------------


def test_scale_map_still_importable_and_unchanged():
    assert SCALE_MAP["billion"] == 1e9
    assert SCALE_MAP["million"] == 1e6
    assert SCALE_MAP["thousand"] == 1e3


def test_claim_patterns_unchanged_count():
    assert len(CLAIM_PATTERNS) == 12
