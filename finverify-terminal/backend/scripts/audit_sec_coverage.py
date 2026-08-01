#!/usr/bin/env python3
"""Read-only SEC coverage audit for FinVerify financial filings."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.evidence import EvidenceRetriever
from core.financial.claim_extractor import extract_claims
from core.financial.concepts import ConceptRegistry
from core.financial.document import FinancialDocument, FinancialPeriod
from core.financial.document_verifier import verify_document
from core.financial.service import FinancialDocumentService
from core.models import BatchVerifyResponse
from ingestion.sec_edgar import fetch_company_facts


BACKEND_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = BACKEND_ROOT / "config" / "concepts.yaml"
AUDITABLE_CONCEPTS = (
    "Revenue",
    "CostOfGoodsSold",
    "GrossProfit",
    "OperatingIncome",
    "NetIncome",
    "OperatingCashFlow",
)
NOT_OBSERVABLE_EQUATIONS = "NOT OBSERVABLE (ConstraintResult does not expose skipped equations)"
NOT_OBSERVABLE_EVIDENCE = "NOT OBSERVABLE"


def audit_ticker(ticker: str) -> dict[str, Any]:
    """Collect read-only SEC coverage metrics for a single ticker."""
    normalized_ticker = ticker.upper()
    registry = ConceptRegistry(CONFIG_PATH)
    service = FinancialDocumentService(CONFIG_PATH)
    facts = fetch_company_facts(normalized_ticker)
    if not facts:
        raise RuntimeError(f"Could not fetch SEC CompanyFacts for {normalized_ticker}")

    document = service.load_document(normalized_ticker)
    claims = extract_claims(document)
    response = verify_document(document, evidence_retriever=EvidenceRetriever())

    raw_summary, tag_stats = _summarize_raw_xbrl(facts)
    resolution_summary, concept_tags = _summarize_resolution(tag_stats, registry)
    concept_mappings = _summarize_concept_mappings(document, concept_tags)
    statement_summary = _summarize_statement_items(document)
    claims_summary = _summarize_claims(claims)
    constraints_summary = _summarize_constraints(registry, claims, response)
    constraint_result = _summarize_constraint_result(response)
    trust_summary = _summarize_trust(response)
    duplicate_analysis = _summarize_raw_duplicates(tag_stats, registry)

    return {
        "ticker": normalized_ticker,
        "timestamp": _utc_now(),
        "raw_xbrl": raw_summary,
        "concept_resolution": resolution_summary,
        "concept_mappings": concept_mappings,
        "statement_items": statement_summary,
        "claims": claims_summary,
        "constraints": constraints_summary,
        "constraint_result": constraint_result,
        "trust": trust_summary,
        "duplicate_analysis": duplicate_analysis,
    }


def audit_tickers(tickers: list[str]) -> list[dict[str, Any]]:
    """Audit multiple tickers, preserving per-ticker failures in the result set."""
    results: list[dict[str, Any]] = []
    for ticker in tickers:
        try:
            results.append(audit_ticker(ticker))
        except Exception as exc:
            results.append(
                {
                    "ticker": ticker.upper(),
                    "timestamp": _utc_now(),
                    "error": str(exc),
                }
            )
    return results


def build_output_payload(results: list[dict[str, Any]]) -> dict[str, Any] | list[dict[str, Any]]:
    if len(results) == 1:
        return results[0]
    return {
        "generated_at": _utc_now(),
        "results": results,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit SEC filing coverage for one or more tickers")
    parser.add_argument("tickers", nargs="+", help="Ticker symbols to audit")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit machine-readable JSON")
    parser.add_argument("--output", type=Path, help="Optional output file path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = audit_tickers(args.tickers)
    payload = build_output_payload(results)

    if args.json_output:
        rendered = json.dumps(payload, indent=2, default=str)
    else:
        rendered = render_text_report(results)

    print(rendered)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + ("\n" if not rendered.endswith("\n") else ""), encoding="utf-8")

    return 1 if any("error" in result for result in results) else 0


def render_text_report(results: list[dict[str, Any]]) -> str:
    sections = [_render_single_report(result) for result in results]
    return "\n\n".join(sections)


def _render_single_report(result: dict[str, Any]) -> str:
    lines = [
        "=" * 72,
        f"FinVerify SEC Coverage Audit | {result['ticker']}",
        "=" * 72,
        f"Timestamp: {result['timestamp']}",
    ]
    if "error" in result:
        lines.append(f"ERROR: {result['error']}")
        return "\n".join(lines)

    raw_xbrl = result["raw_xbrl"]
    resolution = result["concept_resolution"]
    statement_items = result["statement_items"]
    claims = result["claims"]
    constraints = result["constraints"]
    constraint_result = result["constraint_result"]
    trust = result["trust"]
    duplicate_analysis = result["duplicate_analysis"]

    lines.extend(
        [
            "",
            "Raw XBRL Coverage",
            f"  us-gaap numeric observations: {raw_xbrl['total_tags']}",
            f"  us-gaap unique tags:          {raw_xbrl['unique_tags']}",
            f"  other taxonomies:             {', '.join(raw_xbrl['other_taxonomies']) if raw_xbrl['other_taxonomies'] else '(none)'}",
            "",
            "Concept Resolution",
            f"  resolved unique tags:         {resolution['resolved']}",
            f"  unresolved unique tags:       {resolution['unresolved']}",
            f"  resolution percent:           {resolution['resolution_percent']:.1f}%",
        ]
    )
    if resolution["top_unresolved_tags"]:
        lines.append("  top unresolved tags:")
        for row in resolution["top_unresolved_tags"]:
            lines.append(
                f"    - {row['tag']} | frequency={row['frequency']} | observations={row['observations']}"
            )
    else:
        lines.append("  top unresolved tags:          (none)")

    lines.extend(
        [
            "",
            "Concept Mappings",
        ]
    )
    for concept in AUDITABLE_CONCEPTS:
        mapping = result["concept_mappings"][concept]
        lines.append(
            f"  {concept}: found={mapping['found']} | xbrl_tags={_join_or_none(mapping['xbrl_tags'])} | "
            f"selected_tags={_join_or_none(mapping['selected_xbrl_tags'])}"
        )

    lines.extend(
        [
            "",
            "Statement Items",
        ]
    )
    for statement_name, count in statement_items["statements"].items():
        lines.append(f"  {statement_name}: {count}")
    lines.extend(
        [
            f"  total: {statement_items['total']}",
            f"  duplicate (concept, period) groups: {statement_items['duplicate_concept_periods']}",
        ]
    )
    if statement_items["duplicates_list"]:
        for duplicate in statement_items["duplicates_list"]:
            lines.append(
                f"    - {duplicate['concept']} @ {duplicate['period_key']} | count={duplicate['count']} | "
                f"statements={_join_or_none(duplicate['statement_names'])}"
            )

    lines.extend(
        [
            "",
            "Claims",
            f"  total: {claims['total']}",
        ]
    )
    if claims["items"]:
        for item in claims["items"]:
            lines.append(f"    - {item['metric']} | {item['period']}")

    lines.extend(
        [
            "",
            "Constraints",
            f"  equations loaded:             {constraints['equations_loaded']}",
            f"  equations target present:     {constraints['equations_target_present']}",
            f"  equations indeterminate:      {constraints['equations_indeterminate']}",
            f"  equations violated:           {constraints['equations_violated']}",
            f"  equations evaluated:          {constraints['equations_evaluated']}",
            "",
            "Constraint Result",
            f"  consistent:                   {constraint_result['consistent']}",
            f"  violations:                   {constraint_result['violations_count']}",
            f"  indeterminate:                {constraint_result['indeterminate_count']}",
        ]
    )
    if constraint_result["violations"]:
        for violation in constraint_result["violations"]:
            lines.append(
                f"    - {violation['metric']} | expected={violation['expected']} | "
                f"actual={violation['actual']} | formula={violation['formula']}"
            )

    lines.extend(
        [
            "",
            "Trust Distribution",
            f"  HIGH:                         {trust['HIGH']}",
            f"  MEDIUM:                       {trust['MEDIUM']}",
            f"  LOW:                          {trust['LOW']}",
            f"  evidence_tier:                {trust['evidence_tier']}",
            f"  provider:                     {trust['provider']}",
            "",
            "Duplicate Analysis",
            f"  possible multi-filing duplicates: {duplicate_analysis['possible_multi_filing_duplicates']}",
        ]
    )
    if duplicate_analysis["findings"]:
        for finding in duplicate_analysis["findings"]:
            lines.append(
                f"    - {finding['concept']} @ {finding['period_key']} | filings={finding['filing_count']} | "
                f"observations={finding['observations']}"
            )
    else:
        lines.append("    - none")

    return "\n".join(lines)


def _summarize_raw_xbrl(facts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    taxonomy_map = facts.get("facts", {})
    us_gaap = taxonomy_map.get("us-gaap", {})
    tag_stats: dict[str, dict[str, Any]] = {}
    total_observations = 0

    for raw_tag, payload in us_gaap.items():
        stats = _tag_fact_stats(payload)
        prefixed_tag = _prefixed_tag(raw_tag)
        tag_stats[prefixed_tag] = stats
        total_observations += stats["observations"]

    other_taxonomies = sorted(name for name, payload in taxonomy_map.items() if name != "us-gaap" and payload)
    return (
        {
            "total_tags": total_observations,
            "unique_tags": len(us_gaap),
            "other_taxonomies": other_taxonomies,
        },
        tag_stats,
    )


def _summarize_resolution(
    tag_stats: dict[str, dict[str, Any]],
    registry: ConceptRegistry,
) -> tuple[dict[str, Any], dict[str, set[str]]]:
    resolved = 0
    unresolved = 0
    concept_tags: dict[str, set[str]] = defaultdict(set)
    unresolved_rows: list[dict[str, Any]] = []

    for prefixed_tag, stats in tag_stats.items():
        concept_name = registry.resolve_xbrl_tag(prefixed_tag)
        if concept_name is None:
            unresolved += 1
            unresolved_rows.append(
                {
                    "tag": prefixed_tag,
                    "frequency": stats["frequency"],
                    "observations": stats["observations"],
                }
            )
            continue
        resolved += 1
        concept_tags[concept_name].add(prefixed_tag)

    total_unique = resolved + unresolved
    unresolved_rows.sort(key=lambda row: (-row["observations"], -row["frequency"], row["tag"]))

    return (
        {
            "resolved": resolved,
            "unresolved": unresolved,
            "resolution_percent": round((resolved / total_unique) * 100, 1) if total_unique else 0.0,
            "top_unresolved_tags": unresolved_rows[:20],
        },
        concept_tags,
    )


def _summarize_concept_mappings(
    document: FinancialDocument,
    concept_tags: dict[str, set[str]],
) -> dict[str, dict[str, Any]]:
    selected_tags: dict[str, set[str]] = defaultdict(set)
    selected_counts: Counter[str] = Counter()

    for statement in document.statements.values():
        for item in statement.items:
            selected_counts[item.concept] += 1
            if item.xbrl_tag:
                selected_tags[item.concept].add(item.xbrl_tag)

    summary: dict[str, dict[str, Any]] = {}
    for concept in AUDITABLE_CONCEPTS:
        summary[concept] = {
            "xbrl_tags": sorted(concept_tags.get(concept, set())),
            "found": selected_counts[concept] > 0,
            "selected_xbrl_tags": sorted(selected_tags.get(concept, set())),
            "selected_item_count": selected_counts[concept],
        }
    return summary


def _summarize_statement_items(document: FinancialDocument) -> dict[str, Any]:
    statement_counts = {name: len(statement.items) for name, statement in document.statements.items()}
    duplicates: dict[tuple[str, str], dict[str, Any]] = {}

    for statement_name, statement in document.statements.items():
        for item in statement.items:
            key = (item.concept, _period_key(item.period))
            bucket = duplicates.setdefault(
                key,
                {
                    "concept": item.concept,
                    "period_key": key[1],
                    "count": 0,
                    "statement_names": set(),
                    "xbrl_tags": set(),
                    "source_refs": set(),
                },
            )
            bucket["count"] += 1
            bucket["statement_names"].add(statement_name)
            if item.xbrl_tag:
                bucket["xbrl_tags"].add(item.xbrl_tag)
            bucket["source_refs"].add(item.source_ref)

    duplicates_list = [
        {
            "concept": bucket["concept"],
            "period_key": bucket["period_key"],
            "count": bucket["count"],
            "statement_names": sorted(bucket["statement_names"]),
            "xbrl_tags": sorted(bucket["xbrl_tags"]),
            "source_refs": sorted(bucket["source_refs"]),
        }
        for bucket in duplicates.values()
        if bucket["count"] > 1
    ]
    duplicates_list.sort(key=lambda item: (-item["count"], item["concept"], item["period_key"]))

    return {
        "statements": statement_counts,
        "total": sum(statement_counts.values()),
        "duplicate_concept_periods": len(duplicates_list),
        "duplicates_list": duplicates_list,
    }


def _summarize_claims(claims: list[Any]) -> dict[str, Any]:
    return {
        "total": len(claims),
        "items": [
            {
                "metric": _claim_metric_name(claim),
                "period": claim.period,
            }
            for claim in claims
        ],
    }


def _summarize_constraints(
    registry: ConceptRegistry,
    claims: list[Any],
    response: BatchVerifyResponse,
) -> dict[str, Any]:
    equations = registry.load_equations()
    claim_metrics = {
        _claim_metric_name(claim)
        for claim in claims
        if _claim_metric_name(claim) is not None
    }
    constraint_result = response.constraint_result
    return {
        "equations_loaded": len(equations),
        "equations_target_present": sum(1 for equation in equations if equation.target.name in claim_metrics),
        "equations_indeterminate": len(constraint_result.indeterminate) if constraint_result is not None else 0,
        "equations_violated": len(constraint_result.violations) if constraint_result is not None else 0,
        "equations_evaluated": NOT_OBSERVABLE_EQUATIONS,
    }


def _summarize_constraint_result(response: BatchVerifyResponse) -> dict[str, Any]:
    constraint_result = response.constraint_result
    violations = []
    indeterminate_reasons: dict[str, str] = {}
    consistent: bool | None = None

    if constraint_result is not None:
        consistent = constraint_result.consistent
        indeterminate_reasons = dict(constraint_result.indeterminate_reasons)
        for violation in constraint_result.violations:
            violations.append(
                {
                    "metric": violation.metric,
                    "expected": violation.expected,
                    "actual": violation.actual,
                    "formula": violation.formula,
                }
            )

    return {
        "consistent": consistent,
        "violations_count": len(violations),
        "indeterminate_count": len(constraint_result.indeterminate) if constraint_result is not None else 0,
        "violations": violations,
        "indeterminate": list(constraint_result.indeterminate) if constraint_result is not None else [],
        "indeterminate_reasons": indeterminate_reasons,
    }


def _summarize_trust(response: BatchVerifyResponse) -> dict[str, Any]:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    other_labels: Counter[str] = Counter()

    for result in response.results:
        label = str(result.trust_score.label or "").upper()
        if label in counts:
            counts[label] += 1
        else:
            other_labels[label] += 1

    summary: dict[str, Any] = {
        **counts,
        "evidence_tier": NOT_OBSERVABLE_EVIDENCE,
        "provider": NOT_OBSERVABLE_EVIDENCE,
    }
    if other_labels:
        summary["other_labels"] = dict(other_labels)
    return summary


def _summarize_raw_duplicates(
    tag_stats: dict[str, dict[str, Any]],
    registry: ConceptRegistry,
) -> dict[str, Any]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}

    for prefixed_tag, stats in tag_stats.items():
        concept_name = registry.resolve_xbrl_tag(prefixed_tag) or prefixed_tag
        for observation in stats["entries"]:
            key = (concept_name, observation["period_key"])
            bucket = grouped.setdefault(
                key,
                {
                    "concept": concept_name,
                    "period_key": observation["period_key"],
                    "observations": 0,
                    "filings": set(),
                    "accession_numbers": set(),
                    "forms": set(),
                    "filing_dates": set(),
                    "xbrl_tags": set(),
                },
            )
            bucket["observations"] += 1
            bucket["filings"].add(observation["filing_key"])
            if observation["accn"]:
                bucket["accession_numbers"].add(observation["accn"])
            if observation["form"]:
                bucket["forms"].add(observation["form"])
            if observation["filed"]:
                bucket["filing_dates"].add(observation["filed"])
            bucket["xbrl_tags"].add(prefixed_tag)

    findings = [
        {
            "concept": bucket["concept"],
            "period_key": bucket["period_key"],
            "filing_count": len(bucket["filings"]),
            "observations": bucket["observations"],
            "accession_numbers": sorted(bucket["accession_numbers"]),
            "forms": sorted(bucket["forms"]),
            "filing_dates": sorted(bucket["filing_dates"]),
            "xbrl_tags": sorted(bucket["xbrl_tags"]),
        }
        for bucket in grouped.values()
        if len(bucket["filings"]) > 1
    ]
    findings.sort(key=lambda item: (-item["filing_count"], -item["observations"], item["concept"], item["period_key"]))

    return {
        "possible_multi_filing_duplicates": len(findings),
        "findings": findings[:20],
    }


def _tag_fact_stats(payload: dict[str, Any]) -> dict[str, Any]:
    entries: list[dict[str, str]] = []
    filing_keys: set[str] = set()

    for unit_name, raw_entries in payload.get("units", {}).items():
        for entry in raw_entries:
            if _coerce_number(entry.get("val")) is None:
                continue
            filing_key = _filing_key(entry, unit_name)
            filing_keys.add(filing_key)
            entries.append(
                {
                    "accn": str(entry.get("accn") or ""),
                    "filed": str(entry.get("filed") or ""),
                    "form": str(entry.get("form") or ""),
                    "unit": unit_name,
                    "period_key": _raw_period_key(entry),
                    "filing_key": filing_key,
                }
            )

    return {
        "observations": len(entries),
        "frequency": len(filing_keys),
        "entries": entries,
    }


def _claim_metric_name(claim: Any) -> str | None:
    metric = getattr(claim, "metric", None)
    if metric is None:
        return None
    return metric.canonical_name or metric.name


def _period_key(period: FinancialPeriod) -> str:
    quarter = f"Q{period.fiscal_quarter}" if period.fiscal_quarter else "FY"
    return f"{period.start_date.isoformat()}|{period.end_date.isoformat()}|{period.fiscal_year}|{quarter}"


def _raw_period_key(entry: dict[str, Any]) -> str:
    start = str(entry.get("start") or entry.get("end") or "")
    end = str(entry.get("end") or "")
    fiscal_year = str(entry.get("fy") or "")
    fiscal_period = str(entry.get("fp") or "FY")
    return f"{start}|{end}|{fiscal_year}|{fiscal_period}"


def _filing_key(entry: dict[str, Any], unit_name: str) -> str:
    return "|".join(
        [
            str(entry.get("form") or ""),
            str(entry.get("filed") or ""),
            str(entry.get("accn") or ""),
            unit_name,
        ]
    )


def _coerce_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prefixed_tag(raw_tag: str) -> str:
    return raw_tag if ":" in raw_tag else f"us-gaap:{raw_tag}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _join_or_none(values: list[str]) -> str:
    return ", ".join(values) if values else "(none)"


if __name__ == "__main__":
    raise SystemExit(main())
