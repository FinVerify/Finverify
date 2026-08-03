from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from core.financial.document import FinancialPeriod
from core.financial.period import parse_period_string, periods_compatible
from core.models import Calculation, Claim, Evidence, Metric, Source, TrustScore, VerificationResult
from scripts import verify_transcript


def _make_result(
    *,
    raw_value: float,
    verified_value: float | None = None,
    evidence: list[Evidence] | None = None,
    evidence_mode: str = "retrieved",
    metric: str | None = None,
    period: str | None = None,
    period_struct: FinancialPeriod | None = None,
) -> VerificationResult:
    claim = Claim(
        question="What was the value?",
        raw_value=raw_value,
        metric=Metric(name=metric, canonical_name=metric) if metric else None,
        period=period,
        period_struct=period_struct,
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


def _primary_evidence(locator: str, value: float, *, period: str | None) -> Evidence:
    return Evidence(
        source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0),
        claim="q",
        value=value,
        locator=locator,
        period=period,
    )


@pytest.mark.parametrize(
    ("claim_period", "evidence_period", "expected"),
    [
        (FinancialPeriod(kind="annual", fiscal_year=2025), FinancialPeriod(kind="annual", fiscal_year=2025), "MATCH"),
        (
            FinancialPeriod(kind="quarterly", fiscal_year=2025, fiscal_quarter=4),
            FinancialPeriod(kind="quarterly", fiscal_year=2025, fiscal_quarter=4),
            "MATCH",
        ),
        (
            FinancialPeriod(kind="quarterly", fiscal_year=2025, fiscal_quarter=4),
            FinancialPeriod(kind="annual", fiscal_year=2025),
            "MISMATCH",
        ),
        (
            FinancialPeriod(kind="annual", fiscal_year=2025),
            FinancialPeriod(kind="quarterly", fiscal_year=2025, fiscal_quarter=4),
            "MISMATCH",
        ),
        (FinancialPeriod(kind="annual", fiscal_year=2025), FinancialPeriod(kind="annual", fiscal_year=2024), "MISMATCH"),
        (FinancialPeriod(kind="unknown"), FinancialPeriod(kind="annual", fiscal_year=2025), "UNKNOWN"),
        (FinancialPeriod(kind="annual", fiscal_year=2025), FinancialPeriod(kind="unknown"), "UNKNOWN"),
        (FinancialPeriod(kind="unknown"), FinancialPeriod(kind="unknown"), "UNKNOWN"),
        (FinancialPeriod(kind="future"), FinancialPeriod(kind="annual", fiscal_year=2025), "MISMATCH"),
        (
            FinancialPeriod(kind="instant", end_date=parse_period_string("2025-01-26", statement_period_type="instant").end_date),
            FinancialPeriod(kind="instant", end_date=parse_period_string("2025-04-27", statement_period_type="instant").end_date),
            "MISMATCH",
        ),
    ],
)
def test_periods_compatible_matrix(claim_period: FinancialPeriod, evidence_period: FinancialPeriod, expected: str):
    assert periods_compatible(claim_period, evidence_period) == expected


def test_parse_period_string_prefers_explicit_annual_over_relative_phrase():
    period = parse_period_string("For fiscal 2025, revenue was $130.5 billion, up 114% from a year ago.")
    assert period is not None
    assert period.kind == "annual"
    assert period.fiscal_year == 2025


def test_parse_period_string_marks_guidance_as_future():
    period = parse_period_string("Revenue is expected to be $43.0 billion next quarter.")
    assert period is not None
    assert period.kind == "future"


def test_parse_period_string_does_not_guess_ambiguous_relative_period():
    period = parse_period_string("Revenue was $39.3 billion last quarter.")
    assert period is not None
    assert period.kind == "unknown"


def test_same_concept_same_value_wrong_period_is_not_verified():
    evidence = [_primary_evidence("Revenue", 130_497_000_000.0, period="FY2025")]
    claim = {
        "raw_value": 130_500_000_000.0,
        "sentence": "Fourth-quarter revenue was $130.5 billion.",
    }
    result = _make_result(
        raw_value=130_500_000_000.0,
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
        period_struct=FinancialPeriod(kind="quarterly", fiscal_year=2025, fiscal_quarter=4),
    )
    status, note = verify_transcript._claim_status(claim, result, metric="Revenue")
    assert status == "UNRESOLVED"
    assert "Period mismatch" in note


def test_same_concept_same_value_correct_period_is_verified():
    evidence = [_primary_evidence("Revenue", 130_497_000_000.0, period="FY2025")]
    claim = {
        "raw_value": 130_500_000_000.0,
        "sentence": "For fiscal 2025, revenue was $130.5 billion.",
    }
    result = _make_result(
        raw_value=130_500_000_000.0,
        evidence=evidence,
        metric="Revenue",
        period="FY2025",
        period_struct=FinancialPeriod(kind="annual", fiscal_year=2025),
    )
    status, note = verify_transcript._claim_status(claim, result, metric="Revenue")
    assert status == "VERIFIED"
    assert "FY2025" in note


def test_unknown_period_is_not_verified():
    evidence = [_primary_evidence("Revenue", 39_331_000_000.0, period="Q4 FY2025")]
    claim = {
        "raw_value": 39_300_000_000.0,
        "sentence": "Revenue was $39.3 billion.",
    }
    result = _make_result(raw_value=39_300_000_000.0, evidence=evidence, metric="Revenue")
    status, note = verify_transcript._claim_status(claim, result, metric="Revenue")
    assert status == "UNRESOLVED"
    assert "Period undetermined" in note


def test_quarterly_value_identical_to_annual_evidence_is_not_verified():
    evidence = [_primary_evidence("Revenue", 39_300_000_000.0, period="FY2025")]
    claim = {
        "raw_value": 39_300_000_000.0,
        "sentence": "Q4 FY2025 revenue was $39.3 billion.",
    }
    result = _make_result(
        raw_value=39_300_000_000.0,
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
        period_struct=FinancialPeriod(kind="quarterly", fiscal_year=2025, fiscal_quarter=4),
    )
    status, note = verify_transcript._claim_status(claim, result, metric="Revenue")
    assert status == "UNRESOLVED"
    assert "Period mismatch" in note


def test_guidance_value_identical_to_historical_evidence_is_not_verified():
    evidence = [_primary_evidence("Revenue", 43_000_000_000.0, period="Q1 FY2025")]
    claim = {
        "raw_value": 43_000_000_000.0,
        "sentence": "Revenue is expected to be $43.0 billion next quarter.",
    }
    result = _make_result(
        raw_value=43_000_000_000.0,
        evidence=evidence,
        metric="Revenue",
        period="future",
        period_struct=FinancialPeriod(kind="future"),
    )
    status, note = verify_transcript._claim_status(claim, result, metric="Revenue")
    assert status == "UNRESOLVED"
    assert "Period mismatch" in note


def test_explicit_annual_sentence_overrides_q4_transcript_default():
    claim = {
        "claim_type": "revenue",
        "sentence": "For fiscal 2025, revenue was $130.5 billion, up 114% from a year ago.",
        "match": "revenue was $130.5 billion",
        "raw_value": 130_500_000_000.0,
    }
    batch_claim = verify_transcript._batch_claim_from_transcript_claim(claim, "NVDA", "Q4 FY2025")
    assert batch_claim.period_struct is not None
    assert batch_claim.period_struct.kind == "annual"
    assert batch_claim.period_struct.fiscal_year == 2025
    assert batch_claim.period == "FY2025"


def test_ambiguous_relative_period_is_not_guessed():
    claim = {
        "claim_type": "revenue",
        "sentence": "Revenue was $39.3 billion last quarter.",
        "match": "Revenue was $39.3 billion",
        "raw_value": 39_300_000_000.0,
    }
    batch_claim = verify_transcript._batch_claim_from_transcript_claim(claim, "NVDA", "Q4 FY2025")
    assert batch_claim.period_struct is not None
    assert batch_claim.period_struct.kind == "unknown"


def test_real_nvda_annual_revenue_matches_annual_evidence():
    evidence = [_primary_evidence("revenue", 130_497_000_000.0, period="FY2025")]
    claim = {
        "raw_value": 130_500_000_000.0,
        "sentence": "For fiscal 2025, revenue was $130.5 billion, up 114% from a year ago.",
    }
    result = _make_result(
        raw_value=130_500_000_000.0,
        evidence=evidence,
        metric="Revenue",
        period="FY2025",
        period_struct=FinancialPeriod(kind="annual", fiscal_year=2025),
    )
    status, _ = verify_transcript._claim_status(claim, result, metric="Revenue")
    assert status == "VERIFIED"


def test_q4_revenue_does_not_verify_against_annual_evidence():
    evidence = [_primary_evidence("revenue", 130_497_000_000.0, period="FY2025")]
    claim = {
        "raw_value": 39_300_000_000.0,
        "sentence": "Revenue for the fourth quarter ended January 26, 2025, was $39.3 billion.",
    }
    result = _make_result(
        raw_value=39_300_000_000.0,
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
        period_struct=FinancialPeriod(kind="quarterly", fiscal_year=2025, fiscal_quarter=4),
    )
    status, note = verify_transcript._claim_status(claim, result, metric="Revenue")
    assert status == "UNRESOLVED"
    assert "Period mismatch" in note
