"""
Tests for Phase 7E: verification isolation (raw value vs. DVL-corrected value).

Bug being fixed (see Phase 7E audit): `_claim_status()` used to build
`claim_value` as `result.verified_value if not None else raw_value` and
compare only THAT single value against evidence. Because `verified_value`
is always the post-DVL-correction number when any rule fired, a claim whose
ORIGINAL value was wrong but got "corrected" into a number that happened to
match primary evidence was reported as plain `VERIFIED` -- identical to a
claim that was actually stated correctly. There was no way for a report
consumer to tell the two cases apart from `STATUS` alone.

Phase 7E splits this into two independent, precedence-ordered checks:
  - `VERIFIED`                 : the claim's RAW value, independently,
                                  matches concept+period-qualified evidence.
  - `VERIFIED_WITH_CORRECTION` : the raw value does NOT match, but a real
                                  DVL correction (`correction_log` non-empty)
                                  produced a value that does, against the
                                  same qualifying evidence.
  - otherwise                  : existing `UNRESOLVED` / `EVIDENCE_UNAVAILABLE`
                                  / `UNMAPPED` vocabulary, unchanged.

A raw-value match always takes precedence over a correction (Case D/E
below): a claim that was correct as originally stated must stay VERIFIED
even if DVL's correction pipeline does something unrelated or wrong to it
afterward.

This file only exercises `scripts.verify_transcript._claim_status()`
directly against constructed `VerificationResult`s (deterministic, stubbed
evidence) -- consistent with the rest of `test_transcript_verification.py`,
and per task scope: no live SEC network access is used or required.

Usage: pytest tests/test_phase7e_verification_isolation.py   (from backend/)
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
    correction_log: list | None = None,
    metric: str | None = None,
    period: str | None = None,
) -> VerificationResult:
    """Mirrors test_transcript_verification.py's `_make_result` helper.
    Duplicated here (rather than imported) so this file stands alone, per
    task instructions allowing a dedicated Phase 7E test file."""
    claim = Claim(
        question="What was the value?",
        raw_value=raw_value,
        metric=Metric(name=metric, canonical_name=metric) if metric else None,
        period=period,
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


def _revenue_evidence(value: float, period: str = "Q4 FY2025") -> list[Evidence]:
    return [
        Evidence(
            source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0),
            claim="q",
            value=value,
            locator="Revenue",
            period=period,
        )
    ]


def _claim(raw_value: float) -> dict:
    return {"raw_value": raw_value, "sentence": "Revenue was reported for the quarter."}


# ---------------------------------------------------------------------------
# A. raw == evidence, no correction -> VERIFIED
# ---------------------------------------------------------------------------


def test_a_raw_matches_evidence_no_correction_is_verified():
    evidence = _revenue_evidence(39_331_000_000.0)
    result = _make_result(
        raw_value=39_300_000_000.0,
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, note = verify_transcript._claim_status(_claim(39_300_000_000.0), result, metric="Revenue")
    assert status == "VERIFIED"
    assert "correction" not in note.lower()


# ---------------------------------------------------------------------------
# B. CENTRAL BUG: raw != evidence, corrected == evidence, real correction,
#    correct concept, period MATCH -> VERIFIED_WITH_CORRECTION, NOT VERIFIED
# ---------------------------------------------------------------------------


def test_b_central_bug_correction_matching_evidence_is_verified_with_correction_not_plain_verified():
    """The exact Phase 7E reproduction: raw=130,000,000 (wrong by 1000x),
    DVL applies magnitude_x1000 -> verified_value=130,000,000,000, which
    matches primary evidence exactly. Old behavior: plain VERIFIED
    (indistinguishable from a genuinely-correct claim). Fixed behavior:
    VERIFIED_WITH_CORRECTION."""
    evidence = _revenue_evidence(130_000_000_000.0)
    result = _make_result(
        raw_value=130_000_000.0,
        verified_value=130_000_000_000.0,
        correction_log=[{"rule": "magnitude_x1000", "before": 130_000_000.0, "after": 130_000_000_000.0}],
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, note = verify_transcript._claim_status(_claim(130_000_000.0), result, metric="Revenue")
    assert status == "VERIFIED_WITH_CORRECTION"
    assert status != "VERIFIED"
    assert "correction" in note.lower()


# ---------------------------------------------------------------------------
# C. raw != evidence, corrected != evidence -> UNRESOLVED
# ---------------------------------------------------------------------------


def test_c_neither_raw_nor_corrected_matches_is_unresolved():
    evidence = _revenue_evidence(999_000_000_000.0)
    result = _make_result(
        raw_value=130_000_000.0,
        verified_value=130_000_000_000.0,
        correction_log=[{"rule": "magnitude_x1000", "before": 130_000_000.0, "after": 130_000_000_000.0}],
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, _ = verify_transcript._claim_status(_claim(130_000_000.0), result, metric="Revenue")
    assert status == "UNRESOLVED"


# ---------------------------------------------------------------------------
# D. INVERSE BUG: raw == evidence, DVL later changes it incorrectly -> VERIFIED
# ---------------------------------------------------------------------------


def test_d_raw_correct_but_dvl_correction_is_wrong_still_verified():
    """A legitimately-correct original claim must not be falsely downgraded
    to UNRESOLVED just because an unrelated/incorrect DVL correction fired."""
    evidence = _revenue_evidence(39_331_000_000.0)
    result = _make_result(
        raw_value=39_331_000_000.0,
        verified_value=999_000_000.0,  # DVL wrongly "corrected" an already-right value
        correction_log=[{"rule": "magnitude_x0.001_bug", "before": 39_331_000_000.0, "after": 999_000_000.0}],
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, _ = verify_transcript._claim_status(_claim(39_331_000_000.0), result, metric="Revenue")
    assert status == "VERIFIED"


# ---------------------------------------------------------------------------
# E. raw and corrected both within tolerance -> VERIFIED, raw takes precedence
# ---------------------------------------------------------------------------


def test_e_raw_and_corrected_both_match_raw_takes_precedence():
    evidence = _revenue_evidence(39_331_000_000.0)
    result = _make_result(
        raw_value=39_331_000_000.0,
        verified_value=39_330_000_000.0,  # trivial correction, also within tolerance
        correction_log=[{"rule": "rounding_nudge", "before": 39_331_000_000.0, "after": 39_330_000_000.0}],
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, note = verify_transcript._claim_status(_claim(39_331_000_000.0), result, metric="Revenue")
    assert status == "VERIFIED"
    assert "correction" not in note.lower()


# ---------------------------------------------------------------------------
# F. corrected value matches numerically but period MISMATCH -> NOT VERIFIED,
#    NOT VERIFIED_WITH_CORRECTION
# ---------------------------------------------------------------------------


def test_f_corrected_value_matches_wrong_period_is_not_verified():
    evidence = _revenue_evidence(130_000_000_000.0, period="Q1 FY2025")  # different quarter
    result = _make_result(
        raw_value=130_000_000.0,
        verified_value=130_000_000_000.0,
        correction_log=[{"rule": "magnitude_x1000", "before": 130_000_000.0, "after": 130_000_000_000.0}],
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, _ = verify_transcript._claim_status(_claim(130_000_000.0), result, metric="Revenue")
    assert status not in ("VERIFIED", "VERIFIED_WITH_CORRECTION")
    assert status == "UNRESOLVED"


# ---------------------------------------------------------------------------
# G. corrected value matches wrong-concept evidence -> NOT VERIFIED_WITH_CORRECTION
# ---------------------------------------------------------------------------


def test_g_corrected_value_matches_wrong_concept_evidence_is_not_verified_with_correction():
    # Evidence is tagged NetIncome, not Revenue -- Phase 7C's canonical
    # concept gate must reject this regardless of numeric coincidence.
    evidence = [
        Evidence(
            source=Source(name="SEC EDGAR", kind="primary_filing", authority=1.0),
            claim="q",
            value=130_000_000_000.0,
            locator="NetIncome",
            period="Q4 FY2025",
        )
    ]
    result = _make_result(
        raw_value=130_000_000.0,
        verified_value=130_000_000_000.0,
        correction_log=[{"rule": "magnitude_x1000", "before": 130_000_000.0, "after": 130_000_000_000.0}],
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, _ = verify_transcript._claim_status(_claim(130_000_000.0), result, metric="Revenue")
    assert status != "VERIFIED_WITH_CORRECTION"
    assert status == "UNRESOLVED"


# ---------------------------------------------------------------------------
# H. correction exists but no primary evidence -> EVIDENCE_UNAVAILABLE
# ---------------------------------------------------------------------------


def test_h_correction_exists_but_no_primary_evidence_is_evidence_unavailable():
    result = _make_result(
        raw_value=130_000_000.0,
        verified_value=130_000_000_000.0,
        correction_log=[{"rule": "magnitude_x1000", "before": 130_000_000.0, "after": 130_000_000_000.0}],
        evidence=[],
        evidence_mode="model_input",
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, _ = verify_transcript._claim_status(_claim(130_000_000.0), result, metric="Revenue")
    assert status == "EVIDENCE_UNAVAILABLE"


# ---------------------------------------------------------------------------
# I. corrected value matches but period UNKNOWN -> NOT VERIFIED_WITH_CORRECTION
# ---------------------------------------------------------------------------


def test_i_corrected_value_matches_but_period_unknown_is_not_verified_with_correction():
    # No parseable period string on the evidence side -> periods_compatible
    # returns UNKNOWN, which must not permit either VERIFIED or
    # VERIFIED_WITH_CORRECTION (Phase 7D policy, preserved unchanged here).
    evidence = _revenue_evidence(130_000_000_000.0, period=None)  # type: ignore[arg-type]
    result = _make_result(
        raw_value=130_000_000.0,
        verified_value=130_000_000_000.0,
        correction_log=[{"rule": "magnitude_x1000", "before": 130_000_000.0, "after": 130_000_000_000.0}],
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, note = verify_transcript._claim_status(_claim(130_000_000.0), result, metric="Revenue")
    assert status != "VERIFIED_WITH_CORRECTION"
    assert status == "UNRESOLVED"
    assert "undetermined" in note.lower()


# ---------------------------------------------------------------------------
# J. correction_log remains intact
# ---------------------------------------------------------------------------


def test_j_correction_log_remains_intact_after_status_determination():
    correction_log = [{"rule": "magnitude_x1000", "before": 130_000_000.0, "after": 130_000_000_000.0}]
    evidence = _revenue_evidence(130_000_000_000.0)
    result = _make_result(
        raw_value=130_000_000.0,
        verified_value=130_000_000_000.0,
        correction_log=correction_log,
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    verify_transcript._claim_status(_claim(130_000_000.0), result, metric="Revenue")
    assert result.correction_log == correction_log


# ---------------------------------------------------------------------------
# K. Claim.raw_value remains unchanged through verification
# ---------------------------------------------------------------------------


def test_k_claim_raw_value_remains_unchanged_through_verification():
    evidence = _revenue_evidence(130_000_000_000.0)
    result = _make_result(
        raw_value=130_000_000.0,
        verified_value=130_000_000_000.0,
        correction_log=[{"rule": "magnitude_x1000", "before": 130_000_000.0, "after": 130_000_000_000.0}],
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    verify_transcript._claim_status(_claim(130_000_000.0), result, metric="Revenue")
    assert result.claim.raw_value == 130_000_000.0


# ---------------------------------------------------------------------------
# Real-fixture-shaped regressions (deterministic stubs, not live SEC access)
# ---------------------------------------------------------------------------


def test_annual_fy2025_revenue_without_correction_is_plain_verified_not_with_correction():
    """A legitimately-matching, uncorrected annual claim must stay plain
    VERIFIED -- it must NOT become VERIFIED_WITH_CORRECTION just because
    verified_value happens to equal raw_value (no correction occurred)."""
    evidence = _revenue_evidence(130_497_000_000.0, period="FY2025")
    result = _make_result(
        raw_value=130_500_000_000.0,
        evidence=evidence,
        metric="Revenue",
        period="FY2025",
    )
    status, _ = verify_transcript._claim_status(_claim(130_500_000_000.0), result, metric="Revenue")
    assert status == "VERIFIED"
    assert bool(result.correction_log) is False


def test_q4_revenue_does_not_verify_against_annual_evidence():
    """Quarterly claim must not match against an annual evidence period --
    Phase 7D's period-compatibility gate, preserved unchanged."""
    evidence = _revenue_evidence(130_497_000_000.0, period="FY2025")  # annual, not Q4
    result = _make_result(
        raw_value=39_300_000_000.0,
        evidence=evidence,
        metric="Revenue",
        period="Q4 FY2025",
    )
    status, _ = verify_transcript._claim_status(_claim(39_300_000_000.0), result, metric="Revenue")
    assert status == "UNRESOLVED"
