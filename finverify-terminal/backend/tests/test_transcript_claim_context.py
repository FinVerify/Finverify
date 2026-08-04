"""
Tests for Phase 7F: structured claim identity at extraction time.

The Phase 7F audit found that FinVerify's downstream verification layers
(7C canonical concept identity, 7D period identity, 7E raw-vs-corrected
verification isolation) all assume the *extraction* layer handed them a
claim that already knows what it is -- and on real, already-shipped
repository data, it often didn't:

  1. NVIDIA's own headline Q4 revenue ("...revenue for the fourth quarter
     ended January 26, 2025, of $39.3 billion...") was missed entirely,
     because the old 'revenue' regex required the connector word and the
     number to sit immediately next to "revenue" with nothing in between.
  2. Goldman Sachs' "Net revenues were $13.9 billion" was missed because
     the old pattern was singular-only.
  3. Goldman Sachs' "FICC revenue was $2.7 billion" incorrectly mapped to
     company-level Revenue because "FICC" was absent from the segment
     qualifier list.
  4. GAAP and non-GAAP values for the same underlying metric (diluted EPS,
     gross margin) collapsed into the same canonical concept, with no
     structured basis tag anywhere.
  5. Forward-looking guidance had no structured identity at all.
  6. Prior/comparison values ("down from $16.8 billion") were extracted as
     structurally identical, unmarked facts.

This file proves the Phase 7F fixes: a broadened (but still conservative)
'revenue' regex, plus four deterministic identity tags computed once per
claim at extraction time (accounting_basis, scope, value_role,
temporal_frame) that survive the BatchClaim transport boundary.

IMPORTANT (explicit Phase 7F scope decision): these tags are proven to
exist and be accurate here. They are NOT yet consulted by
scripts.verify_transcript._claim_status() to produce new VERIFIED/
UNRESOLVED semantics (only `scope` is consulted, by
_map_claim_to_metric() -- hardening a pre-existing mapping safeguard, not
inventing a new verification layer). No test in this file asserts
anything about VERIFIED/VERIFIED_WITH_CORRECTION/UNRESOLVED status based
on accounting_basis, value_role, or temporal_frame.

Usage: pytest tests/test_transcript_claim_context.py   (from backend/)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from ingestion.transcripts import (
    SAMPLE_TRANSCRIPTS,
    compute_accounting_basis,
    compute_scope,
    compute_temporal_frame,
    compute_value_role,
    extract_claims,
)
from scripts import verify_transcript

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
NVDA_FIXTURE_TEXT = (FIXTURES_DIR / "nvda_q4fy2025_transcript.txt").read_text()


def _claims_for(text: str, claim_type: str | None = None) -> list[dict]:
    claims = extract_claims(text)
    if claim_type is not None:
        claims = [c for c in claims if c["claim_type"] == claim_type]
    return claims


def _find_one(claims: list[dict], **filters) -> dict:
    matches = [c for c in claims if all(c.get(k) == v for k, v in filters.items())]
    assert len(matches) >= 1, f"no claim matched {filters} among {claims}"
    return matches[0]


# ---------------------------------------------------------------------------
# A. NVDA headline revenue: extracted as 'revenue', eligible for company
#    Revenue mapping
# ---------------------------------------------------------------------------


def test_a_nvda_headline_revenue_extracted_and_mappable():
    sentence = (
        "NVIDIA today reported revenue for the fourth quarter ended January 26, "
        "2025, of $39.3 billion, up 12% from the previous quarter and up 78% "
        "from a year ago."
    )
    claims = _claims_for(sentence, "revenue")
    headline = _find_one(claims, raw_value=39_300_000_000.0)
    assert headline["scope"] == "company"
    assert verify_transcript._map_claim_to_metric(headline) == "Revenue"

    # Also prove it end-to-end against the real, already-shipped fixture
    # (not just an isolated sentence).
    fixture_claims = _claims_for(NVDA_FIXTURE_TEXT, "revenue")
    fixture_headline = _find_one(fixture_claims, raw_value=39_300_000_000.0)
    assert fixture_headline["scope"] == "company"
    assert verify_transcript._map_claim_to_metric(fixture_headline) == "Revenue"


# ---------------------------------------------------------------------------
# B. GS plural "Net revenues": extracted, company-level mapping possible
# ---------------------------------------------------------------------------


def test_b_gs_plural_net_revenues_extracted_and_mappable():
    sentence = "Net revenues were $13.9 billion, up 23% from a year ago."
    claims = _claims_for(sentence, "revenue")
    claim = _find_one(claims, raw_value=13_900_000_000.0)
    assert claim["scope"] == "company"
    assert verify_transcript._map_claim_to_metric(claim) == "Revenue"


# ---------------------------------------------------------------------------
# C. FICC: NOT company Revenue
# ---------------------------------------------------------------------------


def test_c_ficc_revenue_is_not_company_revenue():
    sentence = "FICC revenue was $2.7 billion, up 35% from Q4 2023."
    claims = _claims_for(sentence, "revenue")
    claim = _find_one(claims, raw_value=2_700_000_000.0)
    assert claim["scope"] == "segment"
    assert verify_transcript._map_claim_to_metric(claim) is None


# ---------------------------------------------------------------------------
# D. Accounting basis: GAAP vs non_GAAP, distinguishable, match-local
# ---------------------------------------------------------------------------


def test_d_gaap_vs_non_gaap_diluted_eps_distinguished():
    gaap_sentence = "GAAP earnings per diluted share was $0.89, up 14% from the previous quarter."
    non_gaap_sentence = "Non-GAAP earnings per diluted share was $0.89, up 10% from the previous quarter."

    gaap_claim = _find_one(_claims_for(gaap_sentence, "currency_raw"), raw_value=0.89)
    non_gaap_claim = _find_one(_claims_for(non_gaap_sentence, "currency_raw"), raw_value=0.89)

    assert gaap_claim["accounting_basis"] == "GAAP"
    assert non_gaap_claim["accounting_basis"] == "non_GAAP"
    assert gaap_claim["accounting_basis"] != non_gaap_claim["accounting_basis"]


def test_d_non_gaap_is_never_misclassified_as_gaap():
    """Guards against the literal 'gaap' substring inside 'non-GAAP'
    causing a false GAAP classification."""
    assert compute_accounting_basis("Non-GAAP net income was $22.1 billion.", 20) == "non_GAAP"


def test_d_gaap_and_non_gaap_gross_margin_in_same_sentence_distinguished():
    """Real NVDA sentence: basis label follows each value here, not
    precedes it -- match-local (nearest by distance) detection is required,
    not simply 'nearest preceding'."""
    sentence = "Gross margin was 73.0% on a GAAP basis and 73.5% on a non-GAAP basis."
    claims = _claims_for(sentence, "percentage")
    gaap_value = _find_one(claims, raw_value=73.0)
    non_gaap_value = _find_one(claims, raw_value=73.5)
    assert gaap_value["accounting_basis"] == "GAAP"
    assert non_gaap_value["accounting_basis"] == "non_GAAP"


# ---------------------------------------------------------------------------
# E. Guidance: temporal_frame == guidance, no VERIFIED/UNRESOLVED claim made
# ---------------------------------------------------------------------------


def test_e_guidance_sentence_tagged_guidance():
    sentence = "Revenue is expected to be $43.0 billion, plus or minus 2%."
    claims = extract_claims(sentence)
    assert claims, "expected at least the $43.0B currency claim to be extracted"
    for claim in claims:
        assert claim["temporal_frame"] == "guidance"


def test_e_guidance_sentence_does_not_produce_a_revenue_type_claim():
    """The broadened revenue regex must not accidentally capture forward
    guidance as a 'revenue' claim_type at all -- structurally protected by
    requiring a connector word (of/was/were/:) as a standalone word between
    'revenue' and the number, which guidance phrasing ('is expected to
    be') never satisfies."""
    sentence = "Revenue is expected to be $43.0 billion, plus or minus 2%."
    revenue_claims = _claims_for(sentence, "revenue")
    assert revenue_claims == []


def test_e_actual_statement_not_tagged_guidance():
    sentence = "For fiscal 2025, revenue was $130.5 billion, up 114% from a year ago."
    for claim in extract_claims(sentence):
        assert claim["temporal_frame"] == "actual"


# ---------------------------------------------------------------------------
# F. Comparison role: current vs. comparison
# ---------------------------------------------------------------------------


def test_f_fcf_current_vs_comparison_value_role():
    sentence = "Free cash flow was $15.5 billion for the quarter, down from $16.8 billion in the previous quarter."
    claims = _claims_for(sentence, "currency")
    current = _find_one(claims, raw_value=15_500_000_000.0)
    comparison = _find_one(claims, raw_value=16_800_000_000.0)
    assert current["value_role"] == "current"
    assert comparison["value_role"] == "comparison"


@pytest.mark.parametrize(
    "sentence,value,expected_role",
    [
        ("EPS was $1.64, up from $1.52 a year ago, an increase of 8%.", 1.64, "current"),
        ("EPS was $1.64, up from $1.52 a year ago, an increase of 8%.", 1.52, "comparison"),
        ("Gross margin was 46.6%, compared to 45.0% in the year-ago quarter.", 46.6, "current"),
        ("Gross margin was 46.6%, compared to 45.0% in the year-ago quarter.", 45.0, "comparison"),
    ],
)
def test_f_value_role_does_not_over_trigger_on_every_number_near_from(sentence, value, expected_role):
    """Only a value immediately governed by 'down from'/'up from'/
    'compared to'/'versus' is tagged comparison -- not every number in a
    sentence that happens to contain 'from' somewhere."""
    claims = extract_claims(sentence)
    matches = [c for c in claims if abs(c["raw_value"] - value) < 1e-6]
    assert matches, f"expected a claim with raw_value == {value}"
    assert all(c["value_role"] == expected_role for c in matches)


# ---------------------------------------------------------------------------
# G. NVDA known segments remain non-company-level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sentence,value",
    [
        ("Data Center fourth-quarter revenue was a record $35.6 billion, up 16% from the previous quarter.", 35_600_000_000.0),
        ("Fourth-quarter Gaming revenue was $2.5 billion, down 22% from the previous quarter.", 2_500_000_000.0),
        ("Automotive fourth-quarter revenue was $570 million, up 27% from the previous quarter.", 570_000_000.0),
        ("Professional Visualization fourth-quarter revenue was $511 million, up 5% from the previous quarter.", 511_000_000.0),
    ],
)
def test_g_nvda_known_segments_remain_non_company_scope(sentence, value):
    claims = _claims_for(sentence, "revenue")
    claim = _find_one(claims, raw_value=value)
    assert claim["scope"] == "segment"
    assert verify_transcript._map_claim_to_metric(claim) is None


# ---------------------------------------------------------------------------
# H. MSFT segment-like margin: must not be confidently company scope
# ---------------------------------------------------------------------------


def test_h_msft_cloud_gross_margin_not_confidently_company_scope():
    sentence = "Cloud gross margin declined 100 basis points to 72%."
    claims = extract_claims(sentence)
    assert claims, "expected bps/percentage claims to be extracted from this sentence"
    for claim in claims:
        assert claim["scope"] != "company", f"claim wrongly scoped company: {claim}"
        assert claim["scope"] in ("segment", "unknown")


# ---------------------------------------------------------------------------
# I. Unknown safety: ambiguous scope stays unknown, never guessed company
# ---------------------------------------------------------------------------


def test_i_unrecognized_capitalized_qualifier_fails_closed_to_unknown():
    """A synthetic, deliberately unlisted segment-like proper noun
    immediately preceding 'revenue' must NOT be silently promoted to
    company-level scope -- this is the Phase 7F hardening itself, proven
    directly rather than only via already-known qualifiers."""
    scope = compute_scope(
        "Widgets Division revenue was $5 million, up 10% year over year.",
        "revenue was $5 million",
    )
    assert scope == "unknown"


def test_i_plain_unqualified_revenue_still_defaults_to_company():
    """The safe, pre-existing default for a genuinely unqualified figure
    ('Revenue was $X' with nothing before it) must be preserved -- Phase
    7F hardens the UNRECOGNIZED-QUALIFIER case, not the no-qualifier case."""
    assert compute_scope("Revenue was $39.3 billion for the quarter.", "revenue was $39.3 billion") == "company"


# ---------------------------------------------------------------------------
# J. Transport: identity fields survive extraction -> BatchClaim
# ---------------------------------------------------------------------------


def test_j_identity_fields_survive_batch_claim_transport():
    sentence = "Non-GAAP earnings per diluted share was $0.89, up 10% from the previous quarter."
    claim = _find_one(_claims_for(sentence, "currency_raw"), raw_value=0.89)
    assert claim["accounting_basis"] == "non_GAAP"

    batch_claim = verify_transcript._batch_claim_from_transcript_claim(claim, "NVDA", "Q4 FY2025")
    assert batch_claim.accounting_basis == "non_GAAP"
    assert batch_claim.scope == claim["scope"]
    assert batch_claim.value_role == claim["value_role"]
    assert batch_claim.temporal_frame == claim["temporal_frame"]


def test_j_batch_claim_defaults_are_none_for_pre_phase_7f_style_dict():
    """A hand-built claim dict lacking the new keys entirely must not
    raise, and should default the new BatchClaim fields to None."""
    claim = {"claim_type": "revenue", "sentence": "Revenue was $39.3 billion for the quarter.", "match": "revenue was $39.3 billion", "raw_value": 39_300_000_000.0}
    batch_claim = verify_transcript._batch_claim_from_transcript_claim(claim, "NVDA", "Q4 FY2025")
    assert batch_claim.accounting_basis is None
    assert batch_claim.value_role is None
    assert batch_claim.temporal_frame is None
    # scope is still None on the BatchClaim (claim dict never set it), but
    # mapping itself must still work correctly via the compute_scope()
    # fallback inside _map_claim_to_metric().
    assert batch_claim.scope is None
    assert batch_claim.metric == "Revenue"


# ---------------------------------------------------------------------------
# K. Existing period transport (Phase 7D) remains intact
# ---------------------------------------------------------------------------


def test_k_period_transport_unaffected_by_phase_7f():
    """Phase 7F does not touch _claim_period_struct()/period.py at all;
    prove the period-related BatchClaim fields are identical to what
    _batch_claim_from_transcript_claim() would have produced by calling
    _claim_period_struct() directly (its own, still-unmodified logic) and
    checking they match -- i.e. Phase 7F's new identity fields are purely
    additive and don't perturb the existing period transport path."""
    claim = _find_one(_claims_for(NVDA_FIXTURE_TEXT, "revenue"), raw_value=130_500_000_000.0)  # FY2025 total
    metric = verify_transcript._map_claim_to_metric(claim)
    expected_period_struct = verify_transcript._claim_period_struct(claim, metric, "Q4 FY2025")

    batch_claim = verify_transcript._batch_claim_from_transcript_claim(claim, "NVDA", "Q4 FY2025")

    assert batch_claim.period_struct == expected_period_struct
    assert batch_claim.period == (verify_transcript._format_period(expected_period_struct) or "Q4 FY2025")
    # And Phase 7D's own period test suite (run separately in the full
    # test plan) remains the actual authority on period-matching
    # correctness -- this test only guards against 7F silently changing
    # period plumbing.


# ---------------------------------------------------------------------------
# L. Existing Phase 7E raw/corrected semantics remain intact
# ---------------------------------------------------------------------------


def test_l_phase_7e_claim_status_semantics_unaffected_by_7f_tags():
    """_claim_status() (Phase 7E) must still decide status purely from
    raw_value/verified_value/correction_log/evidence -- never from the new
    Phase 7F identity tags, which aren't wired into it at all yet."""
    import inspect

    source = inspect.getsource(verify_transcript._claim_status)
    for forbidden in ("accounting_basis", "temporal_frame", "value_role"):
        assert forbidden not in source, (
            f"_claim_status() must not consult '{forbidden}' in Phase 7F -- "
            "that enforcement is explicitly deferred to a later phase"
        )


# ---------------------------------------------------------------------------
# Cross-company regression: mapped-claim identity remains correct
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ticker", ["AAPL", "TSLA", "JPM", "NVDA", "MSFT", "GS"])
def test_cross_company_every_claim_carries_all_four_identity_tags(ticker):
    """Every single extracted claim -- regardless of claim_type -- carries
    all four Phase 7F identity keys (never silently omitted)."""
    for claim in extract_claims(SAMPLE_TRANSCRIPTS[ticker]):
        assert "accounting_basis" in claim
        assert "scope" in claim
        assert "value_role" in claim
        assert "temporal_frame" in claim
        assert claim["scope"] in ("company", "segment", "unknown")
        assert claim["value_role"] in ("current", "comparison", "unknown")
        assert claim["temporal_frame"] in ("actual", "guidance", "unknown")
        assert claim["accounting_basis"] in ("GAAP", "non_GAAP", None)


@pytest.mark.parametrize("ticker", ["AAPL", "TSLA", "JPM", "NVDA", "MSFT", "GS"])
def test_cross_company_no_segment_claim_ever_maps_to_company_revenue(ticker):
    """Every claim tagged scope='segment' must stay unmapped -- across all
    six real sample transcripts, not just the ones with explicit test
    cases above."""
    for claim in extract_claims(SAMPLE_TRANSCRIPTS[ticker]):
        if claim["claim_type"] == "revenue" and claim["scope"] == "segment":
            assert verify_transcript._map_claim_to_metric(claim) is None, (
                f"segment-scoped claim incorrectly mapped: {claim}"
            )


def test_cross_company_ficc_never_maps_to_company_revenue_in_gs_transcript():
    gs_claims = extract_claims(SAMPLE_TRANSCRIPTS["GS"])
    ficc_claims = [c for c in gs_claims if c["claim_type"] == "revenue" and abs(c["raw_value"] - 2_700_000_000.0) < 1]
    assert ficc_claims, "expected the FICC revenue claim to be extracted"
    for claim in ficc_claims:
        assert claim["scope"] == "segment"
        assert verify_transcript._map_claim_to_metric(claim) is None
