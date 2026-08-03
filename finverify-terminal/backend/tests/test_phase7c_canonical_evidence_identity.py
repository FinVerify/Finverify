"""
Tests for Phase 7C: canonical evidence metric identity.

Background: scripts.verify_transcript._claim_status() decides whether a
mapped transcript claim (canonical concept name, e.g. "Revenue",
"EarningsPerShareDiluted") is VERIFIED by looking for primary-filing
Evidence whose `.locator` matches that concept. Before Phase 7C this was a
raw, lower-cased string comparison between the transcript's canonical
concept name and whatever identifier the evidence provider happened to use
for `.locator`. Revenue "worked" only by coincidence -- SEC ingestion's ad
hoc metric_name key "revenue" (ingestion/sec_edgar.py XBRL_METRICS) is
case-identical to the canonical concept name "Revenue". Every other
concept's snake_case ingestion key ("eps_diluted", "operating_income",
"net_income", ...) never string-equals its canonical name
("EarningsPerShareDiluted", "OperatingIncome", "NetIncome", ...), so real,
correctly-retrieved evidence was silently reported UNRESOLVED.

Phase 7C fixes this by canonicalizing both sides through the repository's
existing ConceptRegistry.resolve_alias() index (config/concepts.yaml)
before comparing, and declares the SEC ingestion snake_case keys as
aliases of their canonical concepts so real evidence resolves correctly --
without introducing any fuzzy or substring matching, and without changing
value-comparison tolerance or period handling.

These tests exercise the actual production functions
(_primary_evidence_values / _claim_status) and the actual
config/concepts.yaml, the same way tests/test_transcript_verification.py
already does -- no parallel/fake canonicalization abstraction.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from core.models import Calculation, Claim, Evidence, Metric, Source, TrustScore, VerificationResult
from scripts import verify_transcript


def _make_result(
    *,
    raw_value: float,
    verified_value: float | None = None,
    evidence: list[Evidence] | None = None,
    evidence_mode: str | None = "retrieved",
    metric: str | None = None,
    period: str | None = "FY2025",
) -> VerificationResult:
    claim = Claim(
        question="What was the value?",
        raw_value=raw_value,
        metric=Metric(name=metric, canonical_name=metric) if metric else None,
        period=period,
    )
    return VerificationResult(
        claim=claim,
        verified_value=verified_value if verified_value is not None else raw_value,
        correction_log=[],
        evidence=evidence or [],
        calculations=[Calculation(name="deterministic_dvl", inputs={"evidence_mode": evidence_mode}, output=raw_value, passed=True)],
        trust_score=TrustScore(label="HIGH" if evidence_mode == "retrieved" else "LOW"),
        verified=True,
    )


def _primary_evidence(locator: str, value: float, *, period: str | None = "FY2025") -> Evidence:
    return Evidence(
        source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0),
        claim="q",
        value=value,
        locator=locator,
        period=period,
    )


# ---------------------------------------------------------------------------
# TEST 1 -- Revenue remains correct (existing accidental-match path unbroken)
# ---------------------------------------------------------------------------


def test_revenue_still_matches_lowercase_ingestion_locator():
    evidence = [_primary_evidence("revenue", 130_497_000_000.0)]
    result = _make_result(raw_value=130_500_000_000.0, evidence=evidence, metric="Revenue")
    status, _ = verify_transcript._claim_status({"raw_value": 130_500_000_000.0}, result, metric="Revenue")
    assert status == "VERIFIED"


# ---------------------------------------------------------------------------
# TEST 2 -- EPS diluted canonicalization (the concrete bug from Phase 7C)
# ---------------------------------------------------------------------------


def test_eps_diluted_matches_snake_case_ingestion_locator():
    evidence = [_primary_evidence("eps_diluted", 2.94)]
    result = _make_result(raw_value=2.94, evidence=evidence, metric="EarningsPerShareDiluted")
    status, note = verify_transcript._claim_status({"raw_value": 2.94}, result, metric="EarningsPerShareDiluted")
    assert status == "VERIFIED"
    assert "EarningsPerShareDiluted" in note


# ---------------------------------------------------------------------------
# TEST 3 -- OperatingIncome canonicalization
# ---------------------------------------------------------------------------


def test_operating_income_matches_snake_case_ingestion_locator():
    evidence = [_primary_evidence("operating_income", 81_451_000_000.0)]
    result = _make_result(raw_value=81_500_000_000.0, evidence=evidence, metric="OperatingIncome")
    status, _ = verify_transcript._claim_status({"raw_value": 81_500_000_000.0}, result, metric="OperatingIncome")
    assert status == "VERIFIED"


# ---------------------------------------------------------------------------
# TEST 4 -- EPS diluted vs basic isolation
# ---------------------------------------------------------------------------


def test_eps_diluted_does_not_match_eps_basic_evidence():
    evidence = [_primary_evidence("eps_basic", 2.94)]
    result = _make_result(raw_value=2.94, evidence=evidence, metric="EarningsPerShareDiluted")
    status, note = verify_transcript._claim_status({"raw_value": 2.94}, result, metric="EarningsPerShareDiluted")
    assert status == "UNRESOLVED"
    assert "none tagged for metric" in note


# ---------------------------------------------------------------------------
# TEST 5 -- OperatingIncome vs NetIncome isolation
# ---------------------------------------------------------------------------


def test_operating_income_does_not_match_net_income_evidence():
    evidence = [_primary_evidence("net_income", 72_880_000_000.0)]
    result = _make_result(raw_value=72_900_000_000.0, evidence=evidence, metric="OperatingIncome")
    status, _ = verify_transcript._claim_status({"raw_value": 72_900_000_000.0}, result, metric="OperatingIncome")
    assert status == "UNRESOLVED"


# ---------------------------------------------------------------------------
# TEST 6 -- Unknown evidence identifier stays unresolved (no fuzzy fallback)
# ---------------------------------------------------------------------------


def test_unrecognized_locator_never_matches_anything():
    evidence = [_primary_evidence("some_unrecognized_metric_key", 130_500_000_000.0)]
    result = _make_result(raw_value=130_500_000_000.0, evidence=evidence, metric="Revenue")
    status, _ = verify_transcript._claim_status({"raw_value": 130_500_000_000.0}, result, metric="Revenue")
    assert status == "UNRESOLVED"


def test_unrecognized_metric_never_matches_anything():
    # Defensive case: if metric itself were ever an unrecognized string,
    # canonicalization must not silently pass it through as a match key.
    evidence = [_primary_evidence("revenue", 130_500_000_000.0)]
    result = _make_result(raw_value=130_500_000_000.0, evidence=evidence, metric="NotARealConcept")
    values = verify_transcript._primary_evidence_values(result, "NotARealConcept")
    assert values == []


# ---------------------------------------------------------------------------
# TEST 7 -- Existing transcript claim -> metric mapping is unweakened
# ---------------------------------------------------------------------------


def test_segment_revenue_still_unmapped():
    """Phase 7C only touches evidence-side concept identity. The conservative
    transcript-side claim -> concept mapping (_map_claim_to_metric) must be
    completely untouched: segment revenue must still refuse to map to the
    consolidated Revenue concept."""
    claim = {
        "claim_type": "revenue",
        "sentence": "Automotive fourth-quarter revenue was $570 million.",
        "match": "revenue was $570 million",
        "raw_value": 570_000_000.0,
    }
    assert verify_transcript._map_claim_to_metric(claim) is None


def test_diluted_eps_sentence_still_maps_to_diluted_concept():
    claim = {
        "claim_type": "eps",
        "sentence": "GAAP earnings per diluted share was $2.94.",
        "match": "$2.94",
        "raw_value": 2.94,
    }
    assert verify_transcript._map_claim_to_metric(claim) == "EarningsPerShareDiluted"


# ---------------------------------------------------------------------------
# TEST 8 -- Existing Revenue VERIFIED path remains working end-to-end
# ---------------------------------------------------------------------------


def test_real_nvda_revenue_verified_path_unchanged():
    """Regression guard for the one path that already worked before Phase
    7C: full-year Revenue against the real NVDA fallback fundamental."""
    evidence = [_primary_evidence("revenue", 130_497_000_000.0)]
    result = _make_result(raw_value=130_500_000_000.0, evidence=evidence, metric="Revenue")
    status, note = verify_transcript._claim_status({"raw_value": 130_500_000_000.0}, result, metric="Revenue")
    assert status == "VERIFIED"
    assert "Revenue" in note
