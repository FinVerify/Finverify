#!/usr/bin/env python3
"""
FinVerify Demo — Earnings Transcript Verification (Phase 7A)
==============================================================

Extends FinVerify's real-data pipeline beyond SEC XBRL filings to real
earnings-call transcript text.

    transcript text
        -> ingestion.transcripts.extract_claims()      (existing, reused)
        -> thin adapter (this file)                    (BatchClaim)
        -> core.engine.verify_batch()                  (existing, reused)
        -> report

This script performs no verification, constraint evaluation, numeric
canonicalization, or trust scoring itself. All of that already exists:
    - ingestion.transcripts.extract_claims() / build_question_from_claim()
    - core.engine.verify_batch()
    - core.financial.concepts.ConceptRegistry (config/concepts.yaml)

The only new logic here is:
    1. _map_claim_to_metric(): a conservative, low-confidence-averse map
       from an extracted transcript claim to a canonical FinVerify concept
       name (or None, left unmapped, if not confident).
    2. _claim_status(): an HONEST report-layer verification state. This
       exists because core.engine.verify()'s own `verified` field is true
       whenever a numeric value survived DVL formatting -- it does NOT mean
       the number was checked against real evidence (the math engine never
       compares evidence.value to the claim's value; only ConstraintVerifier
       cross-checks metrics against each other, and evidence-tier only
       reflects "did SOME primary source respond for this ticker", not "does
       it match THIS claim"). Per Phase 7A scope rules, this script must not
       call something VERIFIED just because verify_batch() ran cleanly or
       trust_score happened to be HIGH -- so it does the evidence-value
       comparison itself, using only existing fields (Evidence.locator,
       Evidence.source.kind, Evidence.value), and reports UNRESOLVED /
       EVIDENCE_UNAVAILABLE / UNMAPPED whenever that check can't be made.

Usage:
    python -m scripts.verify_transcript --file transcript.txt --ticker NVDA
    python -m scripts.verify_transcript --file transcript.txt --ticker NVDA --period "Q4 FY2025"

No automatic ticker-only fetch mode is provided: the repository does not
contain a reliable transcript fetcher (only six hardcoded SAMPLE_TRANSCRIPTS
strings), and Phase 7A explicitly scopes out building a scraper. Local-file
input is the supported real-data path.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.engine import verify_batch  # noqa: E402
from core.models import BatchClaim, BatchVerifyRequest, BatchVerifyResponse, VerificationResult  # noqa: E402
from ingestion.transcripts import build_question_from_claim, extract_claims  # noqa: E402

REPORTS_DIR = Path(__file__).parent.parent / "reports" / "transcripts"

# ---------------------------------------------------------------------------
# Claim -> canonical concept mapping (conservative; see module docstring)
# ---------------------------------------------------------------------------

# Segment/geography/product qualifiers that, when they appear immediately
# before the word "revenue" in a sentence, mean the claim is about a
# component of revenue rather than consolidated company revenue. Consolidated
# "Revenue" in config/concepts.yaml has no segment breakdown, so these are
# deliberately left unmapped rather than misapplied to the whole-company
# concept.
_SEGMENT_REVENUE_QUALIFIERS = (
    "data center", "gaming", "automotive", "professional visualization",
    "services", "iphone", "mac", "ipad", "greater china",
    "intelligent cloud", "more personal computing",
    "productivity and business processes", "linkedin",
    "investment banking", "trading", "consumer banking", "commercial banking",
    "asset and wealth management", "global banking and markets",
    "advisory", "equities", "management and other fees",
    "net interest income",
)

_GROSS_MARGIN_RE = re.compile(r"gross margin", re.IGNORECASE)
_OPERATING_MARGIN_RE = re.compile(r"operating margin", re.IGNORECASE)
_PER_DILUTED_SHARE_RE = re.compile(r"per diluted share", re.IGNORECASE)
_PER_BASIC_SHARE_RE = re.compile(r"per basic share", re.IGNORECASE)


def _map_claim_to_metric(claim: dict) -> Optional[str]:
    """Map a single extract_claims() dict to a canonical concept name from
    config/concepts.yaml, or None if not confidently mappable.

    Deliberately conservative: only a subset of claim_types are ever mapped,
    and only when the surrounding sentence text disambiguates which concept
    is meant. Everything else -- percentages, growth/decline rates, basis
    points, share counts, ratios, return metrics, and any revenue/EPS claim
    whose sentence is ambiguous -- stays unmapped by design. See Phase 7A
    task doc Step 4: "Do not invent metric mappings when confidence is low."
    """
    claim_type = claim["claim_type"]
    sentence = claim.get("sentence", "")
    sentence_lower = sentence.lower()

    if claim_type == "revenue":
        # extract_claims' 'revenue' pattern always starts its match at the
        # literal word "revenue"; check the text immediately preceding it
        # in the sentence for a segment/geo/product qualifier.
        match_start = sentence_lower.find(claim["match"].lower())
        # Scan the ENTIRE sentence prefix before the match, not a fixed-width
        # window: a fixed ~40-char window missed qualifiers in phrasing like
        # "Professional Visualization fourth-quarter revenue was $511
        # million" (found via real-data validation -- the filler words
        # "fourth-quarter " pushed "professional visualization" just outside
        # a 40-char lookback). Segment names never appear this far from
        # "revenue" in these transcripts' fixed phrasing, so scanning the
        # whole prefix does not risk pulling in an unrelated qualifier from
        # elsewhere in the sentence.
        preceding = sentence_lower[:match_start] if match_start >= 0 else sentence_lower
        if any(qualifier in preceding for qualifier in _SEGMENT_REVENUE_QUALIFIERS):
            return None
        return "Revenue"

    if claim_type == "margin":
        if _GROSS_MARGIN_RE.search(sentence):
            return "GrossMargin"
        if _OPERATING_MARGIN_RE.search(sentence):
            return "OperatingMargin"
        return None

    if claim_type in ("currency_raw", "eps"):
        # Real earnings-release prose often spells this out as "earnings
        # per diluted/basic share" rather than the literal token "EPS" that
        # the 'eps' CLAIM_PATTERNS regex looks for (a genuine extraction
        # coverage gap -- see Known Limitations in the deliverable, not
        # fixed here to avoid tuning regexes to one document). Either way,
        # only map when the sentence explicitly says which EPS concept is
        # meant.
        if _PER_DILUTED_SHARE_RE.search(sentence):
            return "EarningsPerShareDiluted"
        if _PER_BASIC_SHARE_RE.search(sentence):
            return "EarningsPerShareBasic"
        return None

    # currency, percentage, growth_pct, decline_pct, bps, shares, ratio,
    # return_metric: no canonical concept in config/concepts.yaml maps
    # confidently from claim_type + sentence alone. Left unmapped.
    return None


# ---------------------------------------------------------------------------
# Adapter: transcript claim dict -> BatchClaim
# ---------------------------------------------------------------------------


def _batch_claim_from_transcript_claim(
    claim: dict,
    ticker: str,
    period: Optional[str],
) -> BatchClaim:
    """Thin adapter. Reuses build_question_from_claim() (existing,
    ingestion/transcripts.py) for the question text so DVL's RATIO_KEYWORDS
    safety logic is exercised identically to the demo path."""
    return BatchClaim(
        question=build_question_from_claim(claim),
        raw_value=claim["raw_value"],
        metric=_map_claim_to_metric(claim),
        entity=ticker,
        ticker=ticker,
        period=period,
    )


# ---------------------------------------------------------------------------
# Honest per-claim verification status (see module docstring)
# ---------------------------------------------------------------------------


def _evidence_mode(result: VerificationResult) -> Optional[str]:
    for calc in result.calculations:
        if calc.name == "deterministic_dvl":
            return calc.inputs.get("evidence_mode")
    return None


def _primary_evidence_values(result: VerificationResult, metric: str) -> list[float]:
    values: list[float] = []
    for item in result.evidence:
        if item.source.kind != "primary_filing":
            continue
        locator = (item.locator or "").strip().lower()
        if locator == metric.strip().lower() and item.value is not None:
            values.append(item.value)
    return values


def _claim_status(claim: dict, result: VerificationResult, metric: Optional[str]) -> tuple[str, str]:
    """Return (status, note). Status is one of:
        VERIFIED             - matches a real primary-source value for this metric
        UNRESOLVED            - mapped and evidence retrieved, but no matching
                                 primary value found (or value doesn't match --
                                 Phase 7A does not implement period-aware
                                 matching, so a mismatch may just mean a
                                 different period, not a wrong extraction)
        EVIDENCE_UNAVAILABLE   - mapped, but no primary-source evidence exists
                                 locally for this ticker at all
        UNMAPPED               - claim_type/context not confidently mapped to
                                 a canonical concept; nothing to verify against
    """
    if metric is None:
        return "UNMAPPED", "Not confidently mapped to a canonical FinVerify concept"

    mode = _evidence_mode(result)
    if mode != "retrieved":
        return (
            "EVIDENCE_UNAVAILABLE",
            "No primary-source (SEC) evidence available locally for this ticker",
        )

    evidence_values = _primary_evidence_values(result, metric)
    if not evidence_values:
        return (
            "UNRESOLVED",
            f"Evidence retrieved for this ticker, but none tagged for metric '{metric}'",
        )

    claim_value = result.verified_value if result.verified_value is not None else claim["raw_value"]
    for evidence_value in evidence_values:
        if evidence_value == 0:
            continue
        if abs(claim_value - evidence_value) / abs(evidence_value) <= 0.01:
            return "VERIFIED", f"Matches primary-source value {evidence_value:,.4g} for {metric}"

    return (
        "UNRESOLVED",
        f"No known primary-source value for '{metric}' matches this claim within tolerance "
        "(may be a different fiscal period; Phase 7A does not implement period-aware matching)",
    )


# ---------------------------------------------------------------------------
# Report building
# ---------------------------------------------------------------------------


def build_report(
    ticker: str,
    period: Optional[str],
    source: str,
    claims: list[dict],
    response: BatchVerifyResponse,
) -> dict:
    claim_reports = []
    counts = {"detected": len(claims), "mapped": 0, "verified": 0, "corrected": 0, "unresolved": 0, "skipped": 0}
    status_breakdown: dict[str, int] = {}

    for claim, result in zip(claims, response.results):
        # NOTE: deliberately NOT `result.claim.metric` here. core.engine.verify()
        # runs resolve_metric() (core/resolvers.py) internally, which does its
        # own generic keyword search over the *question text* against a fixed
        # term list (including bare "revenue") whenever BatchClaim.metric was
        # None -- completely independent of, and much lower-confidence than,
        # this script's _map_claim_to_metric(). Because build_question_from_claim
        # embeds the raw sentence excerpt for growth_pct/decline_pct claims, a
        # claim like "grew 78%" in a sentence about revenue gets silently
        # tagged metric="revenue" by the engine even though the claim itself
        # was deliberately left unmapped. Using our own mapping decision here
        # keeps "mapped" counts and per-claim metric labels honest.
        metric = _map_claim_to_metric(claim)
        status, note = _claim_status(claim, result, metric)
        status_breakdown[status] = status_breakdown.get(status, 0) + 1

        corrected = bool(result.correction_log)
        if metric is not None:
            counts["mapped"] += 1
        if status == "VERIFIED":
            counts["verified"] += 1
        else:
            counts["unresolved"] += 1
        if corrected:
            counts["corrected"] += 1

        claim_reports.append({
            "sentence": claim.get("sentence"),
            "match": claim.get("match"),
            "claim_type": claim.get("claim_type"),
            "metric": metric,
            "unit": claim.get("unit"),
            "currency": claim.get("currency"),
            "raw_value": claim.get("raw_value"),
            "verified_value": result.verified_value,
            "corrected": corrected,
            "trust_label": result.trust_score.label,
            "status": status,
            "note": note,
        })

    return {
        "ticker": ticker,
        "period": period,
        "source": source,
        "counts": counts,
        "status_breakdown": status_breakdown,
        "claims": claim_reports,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def print_report(report: dict) -> None:
    print("=" * 60)
    print("FinVerify -- Earnings Transcript Verification")
    print("=" * 60)
    print(f"Company:  {report['ticker']}")
    print(f"Period:   {report['period'] or 'unspecified'}")
    print(f"Source:   {report['source']}")
    print("-" * 60)
    counts = report["counts"]
    print(f"Claims detected:    {counts['detected']}")
    print(f"Claims mapped:      {counts['mapped']}")
    print(f"Claims verified:    {counts['verified']}")
    print(f"Claims corrected:   {counts['corrected']}")
    print(f"Claims unresolved:  {counts['unresolved']}")
    print(f"Claims skipped:     {counts['skipped']}")
    print("-" * 60)
    for i, claim in enumerate(report["claims"][:10], start=1):
        print(f"[{i}] \"{claim['sentence'][:90]}\"")
        print(f"    Metric: {claim['metric'] or '(unmapped)'}")
        print(f"    Value:  {claim['raw_value']}")
        print(f"    Status: {claim['status']} -- {claim['note']}")
        print()
    if len(report["claims"]) > 10:
        print(f"... ({len(report['claims']) - 10} more claims in the JSON report)")
    print("=" * 60)


def export_json_report(report: dict, ticker: str, period: Optional[str]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    period_slug = (period or "unspecified").replace(" ", "_").replace("/", "-")
    output_path = REPORTS_DIR / f"{ticker.upper()}_{period_slug}.json"
    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(file_path: str, ticker: str, period: Optional[str]) -> Path:
    ticker = ticker.upper()
    text = Path(file_path).read_text(encoding="utf-8")

    claims = extract_claims(text)
    if not claims:
        print(f"No numeric claims extracted from {file_path}", file=sys.stderr)

    batch_claims = [_batch_claim_from_transcript_claim(c, ticker, period) for c in claims]
    request = BatchVerifyRequest(claims=batch_claims, include_constraints=True)
    response = verify_batch(request)

    report = build_report(ticker, period, file_path, claims, response)
    print_report(report)
    output_path = export_json_report(report, ticker, period)
    print(f"\nJSON report written to: {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a real earnings transcript against FinVerify")
    parser.add_argument("--file", required=True, help="Path to a transcript text file")
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. NVDA")
    parser.add_argument("--period", default=None, help='Fiscal period label, e.g. "Q4 FY2025"')
    args = parser.parse_args()
    run(args.file, args.ticker, args.period)


if __name__ == "__main__":
    main()
