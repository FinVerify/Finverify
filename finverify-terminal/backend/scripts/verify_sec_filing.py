#!/usr/bin/env python3
"""
FinVerify Demo — SEC Filing Verification
=========================================

Fetches the latest SEC filing for a ticker, verifies every extracted claim,
prints a human-readable report, and exports a JSON report to
`reports/{ticker}_{filing_date}.json`.

This script performs no verification, constraint evaluation, or normalization
itself — it is orchestration only, reusing:
    - core.financial.service.FinancialDocumentService.load_document()
    - core.financial.claim_extractor.extract_claims()   (for the "total extracted" count)
    - core.financial.document_verifier.verify_document()

Usage:
    python -m scripts.verify_sec_filing AAPL
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.financial.claim_extractor import extract_claims
from core.financial.document import FinancialDocument
from core.financial.document_verifier import verify_document
from core.financial.service import FinancialDocumentService
from core.models import BatchVerifyResponse


REPORTS_DIR = Path(__file__).parent.parent / "reports"


def _period_label(document: FinancialDocument) -> str:
    """Human-readable period for the most recent period in the document."""
    if not document.periods:
        return "unknown"
    period = document.periods[0]
    if period.fiscal_quarter:
        return f"Q{period.fiscal_quarter} FY{period.fiscal_year}"
    return f"FY{period.fiscal_year}"


def _constraint_result_to_dict(constraint_result) -> dict | None:
    """ConstraintResult (and its Violation entries) are plain dataclasses, not
    pydantic models, so they need dataclasses.asdict() rather than
    model_dump()."""
    if constraint_result is None:
        return None
    if is_dataclass(constraint_result):
        return asdict(constraint_result)
    return constraint_result  # already a plain dict/None — defensive fallback


def _trust_summary(response: BatchVerifyResponse) -> dict[str, int]:
    """Count of results per trust label. There is no single batch-level trust
    score on BatchVerifyResponse (it doesn't have that field), so this is a
    report-only aggregate built from each result's own trust_score.label."""
    counts: dict[str, int] = {}
    for result in response.results:
        label = result.trust_score.label
        counts[label] = counts.get(label, 0) + 1
    return counts


def build_report(
    ticker: str,
    document: FinancialDocument,
    total_extracted: int,
    response: BatchVerifyResponse,
) -> dict:
    verified_count = len(response.results)
    skipped_count = total_extracted - verified_count
    constraint_result = response.constraint_result
    constraint_dict = _constraint_result_to_dict(constraint_result)

    claims_summary = [
        {
            "question": result.claim.question,
            "metric": (result.claim.metric.canonical_name or result.claim.metric.name) if result.claim.metric else None,
            "entity": result.claim.entity.name if result.claim.entity else None,
            "period": result.claim.period,
            "raw_value": result.claim.raw_value,
            "verified_value": result.verified_value,
            "corrected": bool(result.correction_log),
            "trust_label": result.trust_score.label,
        }
        for result in response.results
    ]

    return {
        "ticker": ticker,
        "company_name": document.company_name,
        "filing_type": document.filing_type,
        "filing_date": document.filing_date.isoformat(),
        "period": _period_label(document),
        "source_url": document.source_url,
        "total_claims_extracted": total_extracted,
        "skipped_claims": {
            "count": skipped_count,
            "reason": "missing raw_value (BatchClaim.raw_value is required)" if skipped_count else None,
        },
        "verified_claims_count": verified_count,
        "claims": claims_summary,
        "consistent": constraint_result.consistent if constraint_result is not None else None,
        "violations": constraint_dict.get("violations", []) if constraint_dict else [],
        "indeterminate": constraint_dict.get("indeterminate", []) if constraint_dict else [],
        "trust_summary": _trust_summary(response),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def print_report(report: dict) -> None:
    print("=" * 60)
    print("FinVerify — SEC Filing Verification Report")
    print("=" * 60)
    print(f"Ticker:       {report['ticker']}")
    print(f"Company:      {report['company_name']}")
    print(f"Filing Type:  {report['filing_type']}")
    print(f"Period:       {report['period']}")
    print(f"Filed:        {report['filing_date']}")
    print("-" * 60)
    print(f"Claims extracted: {report['total_claims_extracted']}")
    print(f"Claims verified:  {report['verified_claims_count']}")
    skipped = report["skipped_claims"]
    print(f"Claims skipped:   {skipped['count']}" + (f" ({skipped['reason']})" if skipped["reason"] else ""))
    print("-" * 60)
    if report["consistent"] is None:
        print("Consistency: NOT EVALUATED (fewer than 2 verifiable claims, or constraints disabled)")
    elif report["consistent"]:
        print("Consistency: CONSISTENT")
    else:
        print("Consistency: INCONSISTENT")
    violations = report["violations"]
    if violations:
        print(f"Violations ({len(violations)}):")
        for violation in violations:
            print(
                f"  - {violation['metric']}: expected={violation['expected']:.4g} "
                f"actual={violation['actual']:.4g} formula='{violation['formula']}'"
            )
    else:
        print("Violations: none")
    if report["indeterminate"]:
        print(f"Indeterminate (missing dependencies): {', '.join(report['indeterminate'])}")
    print("-" * 60)
    print("Trust score summary:")
    if report["trust_summary"]:
        for label, count in sorted(report["trust_summary"].items()):
            print(f"  {label}: {count}")
    else:
        print("  (no claims verified)")
    print("=" * 60)


def export_json_report(report: dict, ticker: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filing_date = report["filing_date"]
    output_path = REPORTS_DIR / f"{ticker.upper()}_{filing_date}.json"
    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return output_path


def run(ticker: str) -> Path:
    ticker = ticker.upper()

    try:
        document = FinancialDocumentService().load_document(ticker)
    except Exception as exc:
        print(f"ERROR: failed to load SEC filing for {ticker}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        total_extracted = len(extract_claims(document))
        response = verify_document(document)
    except Exception as exc:
        print(f"ERROR: failed to verify SEC filing for {ticker}: {exc}", file=sys.stderr)
        sys.exit(1)

    report = build_report(ticker, document, total_extracted, response)
    print_report(report)
    output_path = export_json_report(report, ticker)
    print(f"\nJSON report written to: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.verify_sec_filing TICKER")
        sys.exit(1)
    run(sys.argv[1])
