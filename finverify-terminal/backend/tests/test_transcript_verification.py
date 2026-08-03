"""
Tests for Phase 7A: real earnings-transcript verification.

Covers:
  1. The currency_raw backtracking regex fix (ingestion/transcripts.py) --
     both that it eliminates the phantom-match bug, and that it does NOT
     regress legitimate extraction (currency, percentage, bps, EPS, growth,
     negative values, million/billion scaling, standalone per-share dollar
     values, guidance ranges).
  2. scripts.verify_transcript's claim-to-metric mapping adapter.
  3. The honest verification-status logic (_claim_status), including the
     "absence of contradiction != verification" case.
  4. Report building / JSON serialization.
  5. CLI behavior (run(), including error handling for a missing file).

Usage: pytest tests/test_transcript_verification.py   (from backend/ directory)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from core.engine import verify_batch
from core.evidence import EvidenceRetriever
from core.models import BatchClaim, BatchVerifyRequest, Entity, Evidence, Source, TrustScore, VerificationResult
from core.models import Claim, Calculation
from ingestion.transcripts import extract_claims
from scripts import verify_transcript


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ---------------------------------------------------------------------------
# 1. Regex fix: eliminates the phantom match, preserves legitimate recall
# ---------------------------------------------------------------------------


def test_currency_raw_no_spurious_match_before_scale_word():
    """The bug found via real NVDA transcript validation: '$511 million' /
    '$570 million' / '$153 billion' must NOT also produce a phantom short
    currency_raw match ('$51' / '$57' / '$15')."""
    cases = [
        ("Automotive revenue was $570 million, up 27% from the previous quarter.", 57.0),
        ("Professional Visualization revenue was $511 million, up 5%.", 51.0),
        ("We had $153 billion in cash and marketable securities on the balance sheet.", 15.0),
    ]
    for text, phantom_value in cases:
        claims = extract_claims(text)
        phantom = [c for c in claims if c["claim_type"] == "currency_raw" and c["raw_value"] == phantom_value]
        assert phantom == [], f"phantom currency_raw match still present for: {text!r}"


@pytest.mark.parametrize(
    "text,expected_type,expected_value",
    [
        ("EPS was $0.68", "eps", 0.68),
        ("EPS of $0.68 per share", "eps", 0.68),
        ("The board declared a dividend of $0.10 per share.", "currency_raw", 0.10),
        ("Adjusted EBITDA was negative $150 million for the quarter.", "currency", 150_000_000.0),
        ("Operating income declined by $200 million year over year.", "currency", 200_000_000.0),
    ],
)
def test_regex_fix_does_not_regress_legitimate_extraction(text, expected_type, expected_value):
    """Values the reviewer explicitly asked to confirm are unaffected by the
    backtracking fix."""
    claims = extract_claims(text)
    matches = [c for c in claims if c["claim_type"] == expected_type and c["raw_value"] == pytest.approx(expected_value)]
    assert matches, f"expected a {expected_type} claim of {expected_value} in {text!r}, got {claims}"


def test_regex_fix_handles_guidance_ranges():
    """'between $46.7 billion and $47.2 billion' must extract both bounds
    correctly, with no phantom truncated matches from either one."""
    text = "Revenue is expected to be between $46.7 billion and $47.2 billion."
    claims = extract_claims(text)
    values = {c["raw_value"] for c in claims if c["claim_type"] == "currency"}
    assert 46_700_000_000.0 in values
    assert 47_200_000_000.0 in values
    phantom = [c for c in claims if c["claim_type"] == "currency_raw"]
    assert phantom == [], f"unexpected currency_raw matches in a guidance range: {phantom}"


def test_regex_fix_handles_revenue_of_phrasing():
    text = "revenue of $46.7 billion"
    claims = extract_claims(text)
    assert any(c["claim_type"] == "revenue" and c["raw_value"] == pytest.approx(46_700_000_000.0) for c in claims)


def test_percentage_and_bps_extraction_unaffected():
    text = "Gross margin was 46.6% compared to 45.0% a year ago. Operating margin improved 240 basis points."
    claims = extract_claims(text)
    assert any(c["claim_type"] == "margin" and c["raw_value"] == pytest.approx(46.6) for c in claims)
    assert any(c["claim_type"] == "bps" and c.get("bps_original") == 240.0 for c in claims)


def test_malformed_and_empty_transcript_produce_no_claims():
    assert extract_claims("") == []
    assert extract_claims("   \n\n  ") == []
    assert extract_claims("Hello there, how are you today friend?") == []


def test_transcript_with_no_numeric_claims():
    text = "The company continued to execute on its strategy and outlook remained positive."
    assert extract_claims(text) == []


def test_duplicate_extraction_deduplicated_within_real_fixture():
    text = (FIXTURES_DIR / "nvda_q4fy2025_transcript.txt").read_text(encoding="utf-8")
    claims = extract_claims(text)
    keys = [(c["sentence"], c["match"], c["claim_type"]) for c in claims]
    assert len(keys) == len(set(keys))


# ---------------------------------------------------------------------------
# 2. Claim -> canonical metric mapping (adapter)
# ---------------------------------------------------------------------------


def _claim(claim_type: str, sentence: str, match: str, raw_value: float = 1.0) -> dict:
    return {"claim_type": claim_type, "sentence": sentence, "match": match, "raw_value": raw_value}


def test_map_generic_revenue_to_canonical_concept():
    claim = _claim("revenue", "Revenue was $39.3 billion for the quarter.", "revenue was $39.3 billion")
    assert verify_transcript._map_claim_to_metric(claim) == "Revenue"


@pytest.mark.parametrize(
    "sentence",
    [
        "Data Center revenue was $35.6 billion, up 93% year over year.",
        "Automotive revenue was $570 million, up 27% from the previous quarter.",
        "Gaming revenue was $2.5 billion, down 22% from the previous quarter.",
    ],
)
def test_segment_revenue_left_unmapped(sentence):
    """Segment/geo revenue must NOT be mapped to the consolidated 'Revenue'
    concept -- config/concepts.yaml has no segment breakdown."""
    claim = _claim("revenue", sentence, "revenue was")
    assert verify_transcript._map_claim_to_metric(claim) is None


def test_segment_revenue_with_filler_words_before_qualifier_left_unmapped():
    """Regression test for a real bug found during Phase 7A validation: a
    fixed-width lookback window missed the qualifier in phrasing like
    "Professional Visualization fourth-quarter revenue was $511 million" --
    the filler words "fourth-quarter " pushed "professional visualization"
    just outside a ~40-char window, so it was incorrectly mapped to the
    consolidated 'Revenue' concept. Fixed by scanning the whole sentence
    prefix instead of a fixed window."""
    claim = _claim(
        "revenue",
        "Professional Visualization fourth-quarter revenue was $511 million, "
        "up 5% from the previous quarter and up 10% from a year ago.",
        "revenue was $511 million",
    )
    assert verify_transcript._map_claim_to_metric(claim) is None


def test_map_gross_margin():
    claim = _claim("margin", "GAAP gross margin was 73.0% for the quarter.", "margin was 73.0%")
    assert verify_transcript._map_claim_to_metric(claim) == "GrossMargin"


def test_map_operating_margin():
    claim = _claim("margin", "Operating margin was 43.1%, down from 43.6% a year ago.", "margin was 43.1%")
    assert verify_transcript._map_claim_to_metric(claim) == "OperatingMargin"


def test_map_diluted_eps_phrasing():
    claim = _claim("currency_raw", "GAAP earnings per diluted share was $0.89, up 14%.", "$0.89")
    assert verify_transcript._map_claim_to_metric(claim) == "EarningsPerShareDiluted"


def test_ambiguous_eps_left_unmapped():
    """Plain 'EPS was $X' with no basic/diluted qualifier stays unmapped --
    concepts.yaml distinguishes Basic vs Diluted and we should not guess."""
    claim = _claim("eps", "EPS was $1.64, up from $1.52 a year ago.", "EPS was $1.64")
    assert verify_transcript._map_claim_to_metric(claim) is None


def test_unmappable_claim_types_stay_unmapped():
    for claim_type in ("percentage", "growth_pct", "decline_pct", "bps", "shares", "ratio", "return_metric", "currency"):
        claim = _claim(claim_type, "Some sentence with a number 12.3", "12.3")
        assert verify_transcript._map_claim_to_metric(claim) is None


def test_batch_claim_from_transcript_claim_preserves_ticker():
    claim = _claim("revenue", "Revenue was $39.3 billion for the quarter.", "revenue was $39.3 billion", 39_300_000_000.0)

    batch_claim = verify_transcript._batch_claim_from_transcript_claim(claim, "NVDA", "Q4 FY2025")

    assert batch_claim.entity == "NVDA"
    assert batch_claim.ticker == "NVDA"
    assert batch_claim.cik is None
    assert batch_claim.period == "Q4 FY2025"


# ---------------------------------------------------------------------------
# 3. Honest verification status (_claim_status)
# ---------------------------------------------------------------------------


def _make_result(
    *,
    raw_value: float,
    verified_value: float | None = None,
    evidence: list[Evidence] | None = None,
    evidence_mode: str | None = "missing",
    correction_log: list | None = None,
    metric: str | None = None,
) -> VerificationResult:
    from core.models import Metric

    claim = Claim(
        question="What was the value?",
        raw_value=raw_value,
        metric=Metric(name=metric, canonical_name=metric) if metric else None,
    )
    return VerificationResult(
        claim=claim,
        verified_value=verified_value if verified_value is not None else raw_value,
        correction_log=correction_log or [],
        evidence=evidence or [],
        calculations=[Calculation(name="deterministic_dvl", inputs={"evidence_mode": evidence_mode}, output=raw_value, passed=True)],
        trust_score=TrustScore(label="HIGH" if evidence_mode == "retrieved" else "LOW"),
        verified=True,
    )


def test_unmapped_claim_is_reported_unmapped_not_verified():
    result = _make_result(raw_value=39_300_000_000.0, evidence_mode="missing")
    status, note = verify_transcript._claim_status({"raw_value": 39_300_000_000.0}, result, metric=None)
    assert status == "UNMAPPED"


def test_mapped_claim_without_retrieved_evidence_is_evidence_unavailable():
    """This is the realistic default state in a fresh environment: no SEC
    data has been ingested into the local fundamentals DB, so evidence_mode
    is 'model_input', not 'retrieved'. Trust label may still be computed,
    but that must NOT be reported as VERIFIED."""
    result = _make_result(raw_value=39_300_000_000.0, evidence_mode="model_input", metric="Revenue")
    status, note = verify_transcript._claim_status({"raw_value": 39_300_000_000.0}, result, metric="Revenue")
    assert status == "EVIDENCE_UNAVAILABLE"


def test_mapped_claim_with_retrieved_evidence_but_no_matching_metric_is_unresolved():
    evidence = [Evidence(source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0), claim="q", value=999.0, locator="NetIncome")]
    result = _make_result(raw_value=39_300_000_000.0, evidence_mode="retrieved", evidence=evidence, metric="Revenue")
    status, note = verify_transcript._claim_status({"raw_value": 39_300_000_000.0}, result, metric="Revenue")
    assert status == "UNRESOLVED"


def test_mapped_claim_matching_real_evidence_value_is_verified():
    """The one case that should actually be labeled VERIFIED: a real
    primary-source value exists for the mapped metric AND it numerically
    matches the claim -- absence-of-contradiction alone is not enough."""
    evidence = [Evidence(source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0), claim="q", value=39_331_000_000.0, locator="Revenue")]
    result = _make_result(raw_value=39_300_000_000.0, evidence_mode="retrieved", evidence=evidence, metric="Revenue")
    status, note = verify_transcript._claim_status({"raw_value": 39_300_000_000.0}, result, metric="Revenue")
    assert status == "VERIFIED"


def test_mapped_claim_mismatching_evidence_value_is_unresolved_not_contradicted():
    """A value far from the known primary figure is reported UNRESOLVED,
    not an invented 'CONTRADICTED' status -- Phase 7A does not implement
    period-aware matching, so a mismatch may just mean a different period."""
    evidence = [Evidence(source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0), claim="q", value=130_497_000_000.0, locator="Revenue")]
    result = _make_result(raw_value=39_300_000_000.0, evidence_mode="retrieved", evidence=evidence, metric="Revenue")
    status, note = verify_transcript._claim_status({"raw_value": 39_300_000_000.0}, result, metric="Revenue")
    assert status == "UNRESOLVED"


def test_engine_verified_flag_alone_never_drives_status():
    """Regression guard for the core semantics bug this module works around:
    VerificationResult.verified is True purely because verified_value is not
    None (see core/output.py build_result), independent of evidence. Confirm
    our status logic does not read that flag at all for a no-evidence case."""
    result = _make_result(raw_value=1.0, evidence_mode="model_input", metric="Revenue")
    assert result.verified is True  # the engine's own (vacuous) flag
    status, _ = verify_transcript._claim_status({"raw_value": 1.0}, result, metric="Revenue")
    assert status == "EVIDENCE_UNAVAILABLE"  # our honest status disagrees


# ---------------------------------------------------------------------------
# 4. Report building / JSON serialization
# ---------------------------------------------------------------------------


def test_build_report_counts_and_json_safe():
    claims = [
        {"claim_type": "revenue", "sentence": "Revenue was $39.3 billion.", "match": "revenue was $39.3 billion", "raw_value": 39_300_000_000.0},
        {"claim_type": "percentage", "sentence": "Up 78% year over year.", "match": "78%", "raw_value": 78.0},
    ]
    batch_claims = [verify_transcript._batch_claim_from_transcript_claim(c, "NVDA", "Q4 FY2025") for c in claims]
    request = BatchVerifyRequest(claims=batch_claims, include_constraints=True)
    response = verify_batch(request, evidence_retriever=EvidenceRetriever())

    report = verify_transcript.build_report("NVDA", "Q4 FY2025", "tests/fixtures/x.txt", claims, response)

    assert report["counts"]["detected"] == 2
    assert report["counts"]["mapped"] == 1  # only the revenue claim maps
    assert report["counts"]["skipped"] == 0
    # Neither claim has real retrieved SEC evidence in this stubbed retriever,
    # so nothing should be VERIFIED.
    assert report["counts"]["verified"] == 0
    assert report["counts"]["unresolved"] == 2

    # Must round-trip through json.dumps with no custom encoder needed
    # beyond `default=str` (matches scripts/verify_sec_filing.py convention).
    serialized = json.dumps(report, indent=2, default=str)
    reloaded = json.loads(serialized)
    assert reloaded["ticker"] == "NVDA"
    assert len(reloaded["claims"]) == 2


def test_build_report_metric_not_clobbered_by_engine_internal_resolver():
    """Regression test for a real bug found during Phase 7A validation:
    core.engine.verify() internally runs resolve_metric() (core/resolvers.py),
    which does its own generic keyword search over the question text and
    sets claim.metric = 'revenue' for ANY claim whose question text happens
    to mention the word "revenue" -- even a growth_pct claim deliberately
    left unmapped by _map_claim_to_metric(). build_report() must report such
    a claim as unmapped, not silently adopt the engine's internal guess."""
    claims = [
        {
            "claim_type": "growth_pct",
            "sentence": "Data Center revenue was a record $35.6 billion, up 93% year over year.",
            "match": "up 93%",
            "raw_value": 93.0,
        },
    ]
    batch_claims = [verify_transcript._batch_claim_from_transcript_claim(c, "NVDA", "Q4 FY2025") for c in claims]
    # Sanity check: our adapter really did leave this unmapped.
    assert batch_claims[0].metric is None

    response = verify_batch(BatchVerifyRequest(claims=batch_claims), evidence_retriever=EvidenceRetriever())
    # Confirm the engine really does silently mutate metric internally,
    # otherwise this test would not be exercising the bug it guards against.
    assert response.results[0].claim.metric is not None
    assert response.results[0].claim.metric.canonical_name == "revenue"

    report = verify_transcript.build_report("NVDA", "Q4 FY2025", "x.txt", claims, response)
    assert report["claims"][0]["metric"] is None
    assert report["claims"][0]["status"] == "UNMAPPED"
    assert report["counts"]["mapped"] == 0


def test_build_report_preserves_original_claim_context():
    claims = [{"claim_type": "eps", "sentence": "EPS was $0.89 for the quarter.", "match": "EPS was $0.89", "raw_value": 0.89, "unit": "USD/shares", "currency": "USD"}]
    batch_claims = [verify_transcript._batch_claim_from_transcript_claim(c, "NVDA", "Q4 FY2025") for c in claims]
    response = verify_batch(BatchVerifyRequest(claims=batch_claims), evidence_retriever=EvidenceRetriever())
    report = verify_transcript.build_report("NVDA", "Q4 FY2025", "src.txt", claims, response)

    claim_report = report["claims"][0]
    assert claim_report["sentence"] == "EPS was $0.89 for the quarter."
    assert claim_report["claim_type"] == "eps"
    assert claim_report["unit"] == "USD/shares"
    assert claim_report["currency"] == "USD"
    assert claim_report["raw_value"] == pytest.approx(0.89)


# ---------------------------------------------------------------------------
# 5. CLI behavior
# ---------------------------------------------------------------------------


def test_run_end_to_end_on_real_fixture_writes_json_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(verify_transcript, "REPORTS_DIR", tmp_path)
    fixture = FIXTURES_DIR / "nvda_q4fy2025_transcript.txt"

    output_path = verify_transcript.run(str(fixture), "NVDA", "Q4 FY2025")

    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["ticker"] == "NVDA"
    assert data["counts"]["detected"] > 0

    captured = capsys.readouterr()
    assert "Earnings Transcript Verification" in captured.out
    assert "Claims detected" in captured.out


def test_run_raises_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(verify_transcript, "REPORTS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        verify_transcript.run(str(tmp_path / "does_not_exist.txt"), "NVDA", None)


def test_run_handles_transcript_with_no_claims(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(verify_transcript, "REPORTS_DIR", tmp_path)
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("The company remained focused on its long-term strategy.", encoding="utf-8")

    output_path = verify_transcript.run(str(empty_file), "NVDA", None)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["counts"]["detected"] == 0
    captured = capsys.readouterr()
    assert "No numeric claims extracted" in captured.err
