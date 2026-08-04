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
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.engine import verify_batch  # noqa: E402
from core.financial.concepts import ConceptRegistry  # noqa: E402
from core.financial.document import FinancialPeriod  # noqa: E402
from core.financial.period import parse_period_string, periods_compatible  # noqa: E402
from core.models import BatchClaim, BatchVerifyRequest, BatchVerifyResponse, VerificationResult  # noqa: E402
from ingestion.transcripts import build_question_from_claim, compute_scope, extract_claims  # noqa: E402

REPORTS_DIR = Path(__file__).parent.parent / "reports" / "transcripts"

# ---------------------------------------------------------------------------
# Claim -> canonical concept mapping (conservative; see module docstring)
# ---------------------------------------------------------------------------

# PHASE 7F: the segment/geography/product qualifier scan that used to live
# here as a private, revenue-only tuple has moved to
# ingestion.transcripts.compute_scope() (and its _SEGMENT_QUALIFIERS /
# _COMPANY_LEVEL_SCOPE_WORDS tables), so extraction and mapping can never
# disagree about a claim's scope, and so the "fail closed on an
# unrecognized qualifier" hardening (see that module) applies here too.
# Kept as a re-exported alias purely for backward compatibility with any
# external code that imported the old name directly.
from ingestion.transcripts import _SEGMENT_QUALIFIERS as _SEGMENT_REVENUE_QUALIFIERS  # noqa: E402,F401

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
        # PHASE 7F: use the shared, hardened scope classifier
        # (ingestion.transcripts.compute_scope) instead of a local,
        # revenue-only re-scan. Prefer a scope already computed at
        # extraction time (claim["scope"], present on every claim
        # extract_claims() produces); fall back to computing it fresh from
        # `sentence`/`match` for callers that hand-build a claim dict
        # without that key (e.g. this module's own test suite), which
        # preserves this function's pre-7F behavior exactly for those
        # callers.
        #
        # scope == "segment"  -> a component of revenue, not consolidated
        #                        company revenue (config/concepts.yaml's
        #                        "Revenue" has no segment breakdown).
        # scope == "unknown"  -> an unrecognized qualifier precedes the
        #                        claim (Phase 7F hardening: previously this
        #                        silently fell through to "Revenue";
        #                        proven wrong on GS's "FICC revenue" before
        #                        FICC was added to the known segment list --
        #                        an as-yet-unlisted qualifier deserves the
        #                        same conservative treatment, not a guess).
        # scope == "company"  -> may map normally.
        scope = claim.get("scope")
        if scope is None:
            scope = compute_scope(sentence, claim.get("match", ""))
        if scope != "company":
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


@dataclass(frozen=True)
class MatchedEvidence:
    value: float
    locator: Optional[str]
    period: Optional[str]
    period_struct: Optional[FinancialPeriod]


def _statement_period_type(metric: Optional[str]) -> Optional[str]:
    if not metric:
        return None
    concept = _concept_registry().get_concept(metric)
    statement = concept.get("statement")
    if statement == "BalanceSheet":
        return "instant"
    if statement in {"IncomeStatement", "CashFlowStatement"}:
        return "duration"
    return None


def _merge_period_hint(primary: Optional[FinancialPeriod], fallback: Optional[FinancialPeriod]) -> Optional[FinancialPeriod]:
    if primary is None:
        return fallback
    if fallback is None or primary.kind in {"future", "unknown"}:
        return primary

    merged = primary.model_copy(deep=True) if hasattr(primary, "model_copy") else primary.copy(deep=True)
    if merged.fiscal_year is None:
        merged.fiscal_year = fallback.fiscal_year
    if merged.kind == "quarterly" and merged.fiscal_quarter is None:
        merged.fiscal_quarter = fallback.fiscal_quarter
    if merged.kind == "instant":
        if merged.end_date is None:
            merged.end_date = fallback.end_date
        if merged.start_date is None:
            merged.start_date = fallback.start_date
    return merged


def _format_period(period: Optional[FinancialPeriod]) -> Optional[str]:
    if period is None:
        return None
    if period.kind == "future":
        return "future"
    if period.kind == "quarterly" and period.fiscal_year is not None and period.fiscal_quarter is not None:
        return f"Q{period.fiscal_quarter} FY{period.fiscal_year}"
    if period.kind == "annual" and period.fiscal_year is not None:
        return f"FY{period.fiscal_year}"
    if period.kind == "instant" and period.end_date is not None:
        return period.end_date.isoformat()
    return None


def _serialize_period(period: Optional[FinancialPeriod]) -> Optional[dict]:
    if period is None:
        return None
    return {
        "kind": period.kind,
        "fiscal_year": period.fiscal_year,
        "fiscal_quarter": period.fiscal_quarter,
        "start_date": period.start_date.isoformat() if period.start_date is not None else None,
        "end_date": period.end_date.isoformat() if period.end_date is not None else None,
    }


def _claim_period_struct(claim: dict, metric: Optional[str], transcript_period: Optional[str]) -> Optional[FinancialPeriod]:
    statement_period_type = _statement_period_type(metric)
    sentence_period = parse_period_string(claim.get("sentence"), statement_period_type=statement_period_type)
    fallback_period = parse_period_string(transcript_period, statement_period_type=statement_period_type)

    if sentence_period is not None:
        if sentence_period.kind not in {"unknown"}:
            return _merge_period_hint(sentence_period, fallback_period)
        return sentence_period
    if fallback_period is not None:
        return fallback_period
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
    metric = _map_claim_to_metric(claim)
    period_struct = _claim_period_struct(claim, metric, period)
    return BatchClaim(
        question=build_question_from_claim(claim),
        raw_value=claim["raw_value"],
        metric=metric,
        entity=ticker,
        ticker=ticker,
        period=_format_period(period_struct) or period,
        period_struct=period_struct,
        # PHASE 7F: carry the structured claim-identity tags computed at
        # extraction time (ingestion.transcripts.extract_claims()) through
        # to BatchClaim, so they are not thrown away here the way sentence/
        # basis/scope/role context used to be. `.get(...)` defaults to None
        # for any claim dict that predates this phase (e.g. hand-built in
        # tests) -- additive, no existing caller breaks.
        accounting_basis=claim.get("accounting_basis"),
        scope=claim.get("scope"),
        value_role=claim.get("value_role"),
        temporal_frame=claim.get("temporal_frame"),
    )


# ---------------------------------------------------------------------------
# Honest per-claim verification status (see module docstring)
# ---------------------------------------------------------------------------


def _evidence_mode(result: VerificationResult) -> Optional[str]:
    for calc in result.calculations:
        if calc.name == "deterministic_dvl":
            return calc.inputs.get("evidence_mode")
    return None


@lru_cache(maxsize=1)
def _concept_registry() -> ConceptRegistry:
    """Shared ConceptRegistry instance, loaded from the same config/concepts.yaml
    used everywhere else (core.engine._load_constraint_registry(),
    core.financial.service.FinancialDocumentService). This is the repository's
    existing canonical-concept-identity mechanism (concept name + declared
    aliases + XBRL tags -> one canonical name via ConceptRegistry.resolve_alias);
    Phase 7C reuses it rather than inventing a second, transcript-local alias
    table."""
    config_path = Path(__file__).parent.parent / "config" / "concepts.yaml"
    return ConceptRegistry(config_path)


def _canonical_concept(name: Optional[str], registry: ConceptRegistry) -> Optional[str]:
    """Resolve a metric/locator string to its canonical concept name via the
    registry's alias index, or None if it isn't a recognized concept or alias
    at all. Deterministic dict lookup only -- no fuzzy or substring matching,
    so an unrecognized identifier stays unresolved rather than being guessed
    at."""
    if not name:
        return None
    return registry.resolve_alias(name)


def _primary_evidence_matches(result: VerificationResult, metric: str) -> list[MatchedEvidence]:
    """Collect canonical-metric-matching primary evidence with parsed periods."""
    registry = _concept_registry()
    canonical_metric = _canonical_concept(metric, registry)
    if canonical_metric is None:
        return []

    statement_period_type = _statement_period_type(metric)
    matches: list[MatchedEvidence] = []
    for item in result.evidence:
        if item.source.kind != "primary_filing":
            continue
        canonical_locator = _canonical_concept(item.locator, registry)
        if canonical_locator is not None and canonical_locator == canonical_metric and item.value is not None:
            matches.append(
                MatchedEvidence(
                    value=item.value,
                    locator=item.locator,
                    period=item.period,
                    period_struct=parse_period_string(item.period, statement_period_type=statement_period_type),
                )
            )
    return matches


def _primary_evidence_values(result: VerificationResult, metric: str) -> list[float]:
    """Collect primary-filing evidence values whose concept identity matches
    `metric`.

    PHASE 7C: this used to compare `Evidence.locator` and `metric` as raw,
    lower-cased strings. That only ever worked for Revenue by coincidence --
    the transcript side's canonical name ("Revenue") and the SEC ingestion
    side's ad hoc metric_name key ("revenue") happen to be identical up to
    case. Every other concept legitimately fails: SEC ingestion's
    XBRL_METRICS (ingestion/sec_edgar.py) stores snake_case keys like
    "eps_diluted" / "operating_income" / "net_income", which never
    string-equals a canonical concept name like "EarningsPerShareDiluted" /
    "OperatingIncome" / "NetIncome" -- even though real matching evidence
    exists. Both sides are now canonicalized through the same
    ConceptRegistry.resolve_alias() index (config/concepts.yaml) before
    comparison, so a real concept match no longer depends on the two
    identifier vocabularies agreeing by accident. The snake_case ingestion
    keys are declared as aliases in concepts.yaml precisely so this
    resolves; concepts with no such alias (e.g. an unrecognized locator)
    resolve to None and never match, so this stays exactly as conservative
    as before for anything not explicitly declared equivalent.
    """
    return [match.value for match in _primary_evidence_matches(result, metric)]


def _resolved_claim_period(claim: dict, result: VerificationResult, metric: str) -> Optional[FinancialPeriod]:
    statement_period_type = _statement_period_type(metric)
    if result.claim.period_struct is not None:
        return result.claim.period_struct
    if claim.get("period_struct") is not None:
        return claim["period_struct"]

    sentence_period = parse_period_string(claim.get("sentence"), statement_period_type=statement_period_type)
    fallback_period = parse_period_string(result.claim.period or claim.get("period"), statement_period_type=statement_period_type)
    if sentence_period is not None:
        if sentence_period.kind not in {"unknown"}:
            return _merge_period_hint(sentence_period, fallback_period)
        return sentence_period
    if fallback_period is not None:
        return fallback_period
    return None


def _value_matches_evidence(
    value: float,
    evidence_matches: list[MatchedEvidence],
    claim_period: Optional[FinancialPeriod],
) -> tuple[bool, Optional[MatchedEvidence], bool, list[str], list[str]]:
    """Check a single numeric value against period-compatible evidence within
    the existing +/-1% tolerance.

    PHASE 7E: extracted, unmodified, from what used to be the single
    comparison loop inside `_claim_status()`. Pure value+period comparison
    logic lives here so that the raw-value check and the corrected-value
    check (see `_claim_status()`) always share identical tolerance and
    period-compatibility semantics -- neither check may drift from the
    other, and no threshold changes were made while extracting this.

    Returns (matched, matched_evidence, saw_period_match, mismatched_periods,
    unresolved_periods).
    """
    saw_period_match = False
    mismatched_periods: list[str] = []
    unresolved_periods: list[str] = []

    for evidence_match in evidence_matches:
        compatibility = periods_compatible(claim_period, evidence_match.period_struct)
        evidence_period_label = evidence_match.period or _format_period(evidence_match.period_struct) or "unknown"

        if compatibility == "MISMATCH":
            mismatched_periods.append(evidence_period_label)
            continue
        if compatibility == "UNKNOWN":
            unresolved_periods.append(evidence_period_label)
            continue

        saw_period_match = True
        evidence_value = evidence_match.value
        if evidence_value == 0:
            continue
        if abs(value - evidence_value) / abs(evidence_value) <= 0.01:
            return True, evidence_match, saw_period_match, mismatched_periods, unresolved_periods

    return False, None, saw_period_match, mismatched_periods, unresolved_periods


def _claim_status(claim: dict, result: VerificationResult, metric: Optional[str]) -> tuple[str, str]:
    """Return (status, note). Status is one of:
        VERIFIED                 - the ORIGINAL (raw) claim value, independently,
                                    matches a real primary-source value for this
                                    metric in a compatible period. PHASE 7E: only
                                    raw_value may ever earn this status. Plain
                                    VERIFIED answers "was the claim as originally
                                    stated correct?" -- it must never mean "did
                                    FinVerify silently rewrite the number into
                                    something that happened to match evidence?"
                                    (that case is VERIFIED_WITH_CORRECTION,
                                    below). A raw-value match takes precedence
                                    over anything DVL does afterward: a
                                    legitimately-correct original claim stays
                                    VERIFIED even if DVL later applies an
                                    unrelated or wrong correction to it.
        VERIFIED_WITH_CORRECTION - the raw value does NOT independently match
                                    evidence, but a real DVL correction occurred
                                    (result.correction_log is non-empty -- never
                                    inferred merely from verified_value being
                                    present or different) and the corrected value
                                    matches the SAME concept- and period-matched
                                    evidence, within the same tolerance used for
                                    the raw check.
        UNRESOLVED                - mapped and evidence retrieved, but neither the
                                     original nor (if a correction occurred) the
                                     corrected value matches a primary value
                                     within tolerance in a compatible period.
        EVIDENCE_UNAVAILABLE       - mapped, but no primary-source evidence exists
                                     locally for this ticker at all
        UNMAPPED                   - claim_type/context not confidently mapped to
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

    evidence_matches = _primary_evidence_matches(result, metric)
    if not evidence_matches:
        return (
            "UNRESOLVED",
            f"Evidence retrieved for this ticker, but none tagged for metric '{metric}'",
        )

    claim_period = _resolved_claim_period(claim, result, metric)
    raw_value = claim["raw_value"]

    # Raw-value check first, and it takes precedence over any correction
    # (Phase 7E threat-matrix Case D): a claim that was correct as originally
    # stated must verify even if DVL's correction pipeline later mangles it.
    (
        raw_matched,
        raw_evidence,
        raw_saw_period_match,
        raw_mismatched_periods,
        raw_unresolved_periods,
    ) = _value_matches_evidence(raw_value, evidence_matches, claim_period)

    if raw_matched:
        period_label = _format_period(claim_period) or result.claim.period or claim.get("period") or "matched period"
        return "VERIFIED", f"Matches primary-source value {raw_evidence.value:,.4g} for {metric} in {period_label}"

    # A corrected value may only earn VERIFIED_WITH_CORRECTION when a real
    # DVL correction actually happened. This is read from correction_log
    # (existing provenance), never inferred from verified_value alone --
    # verified_value equals raw_value whenever no rule fired, and even when
    # it differs, correction_log is the authoritative "a rule actually
    # applied" signal (Phase 7E requirement; see module docstring on why
    # core.engine.verify()'s own `verified` flag can't be trusted for this).
    correction_occurred = bool(result.correction_log)
    corr_saw_period_match = False
    corr_mismatched_periods: list[str] = []
    corr_unresolved_periods: list[str] = []

    if correction_occurred and result.verified_value is not None:
        (
            corr_matched,
            corr_evidence,
            corr_saw_period_match,
            corr_mismatched_periods,
            corr_unresolved_periods,
        ) = _value_matches_evidence(result.verified_value, evidence_matches, claim_period)
        if corr_matched:
            period_label = _format_period(claim_period) or result.claim.period or claim.get("period") or "matched period"
            return (
                "VERIFIED_WITH_CORRECTION",
                f"Original value did not match evidence, but a DVL correction produced "
                f"{result.verified_value:,.4g}, which matches primary-source value "
                f"{corr_evidence.value:,.4g} for {metric} in {period_label}",
            )

    saw_period_match = raw_saw_period_match or corr_saw_period_match
    mismatched_periods = raw_mismatched_periods + corr_mismatched_periods
    unresolved_periods = raw_unresolved_periods + corr_unresolved_periods

    if saw_period_match:
        return (
            "UNRESOLVED",
            f"No known primary-source value for '{metric}' matches this claim within tolerance in the matched period",
        )

    if unresolved_periods:
        claim_period_label = _format_period(claim_period) or result.claim.period or claim.get("period") or "unknown"
        evidence_summary = ", ".join(sorted(set(unresolved_periods)))
        return (
            "UNRESOLVED",
            f"Period undetermined for '{metric}' (claim={claim_period_label}, evidence={evidence_summary})",
        )

    if mismatched_periods:
        claim_period_label = _format_period(claim_period) or result.claim.period or claim.get("period") or "unknown"
        evidence_summary = ", ".join(sorted(set(mismatched_periods)))
        return (
            "UNRESOLVED",
            f"Period mismatch for '{metric}' (claim={claim_period_label}, evidence={evidence_summary})",
        )

    return (
        "UNRESOLVED",
        f"No known primary-source value for '{metric}' matches this claim within tolerance",
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
    counts = {
        "detected": len(claims),
        "mapped": 0,
        "verified": 0,
        "verified_with_correction": 0,
        "corrected": 0,
        "unresolved": 0,
        "skipped": 0,
    }
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
        # NOTE: VERIFIED_WITH_CORRECTION (Phase 7E) is deliberately its own
        # bucket -- never folded into plain "verified" (that would silently
        # reintroduce the Phase 7E bug into the report counts) and never
        # folded into "unresolved" (a correction that DID independently
        # verify against evidence is a materially different outcome from a
        # claim nothing could be resolved against). "corrected" below
        # continues to mean "a DVL correction occurred" -- a separate fact
        # from whether that correction was itself evidence-verified; the
        # per-status breakdown below distinguishes UNMAPPED/EVIDENCE_UNAVAILABLE/
        # UNRESOLVED/VERIFIED/VERIFIED_WITH_CORRECTION precisely.
        if status == "VERIFIED":
            counts["verified"] += 1
        elif status == "VERIFIED_WITH_CORRECTION":
            counts["verified_with_correction"] += 1
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
            "claim_period": result.claim.period,
            "claim_period_struct": _serialize_period(result.claim.period_struct),
            "evidence_periods": [
                {
                    "locator": item.locator,
                    "value": item.value,
                    "period": item.period,
                    "source_kind": item.source.kind,
                }
                for item in result.evidence
            ],
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
    print(f"Verified w/ correction: {counts['verified_with_correction']}")
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
