"""Extract verification-ready Claim objects from a FinancialDocument.

This module has a single responsibility: transformation. It does not fetch
data (that's `FinancialDocumentService`) and it does not normalize SEC vs.
canonical concept names (that's `StatementMapper` / `ConceptRegistry` — by
the time a `FinancialStatementItem` exists, its `concept` field is already
the canonical name resolved via the registry, so nothing here renames
anything).
"""

from __future__ import annotations

from core.models import Claim, Entity, Metric

from .document import FinancialDocument, FinancialPeriod, FinancialStatementItem


def extract_claims(document: FinancialDocument) -> list[Claim]:
    """Convert every statement item in a FinancialDocument into a Claim.

    One Claim is produced per `FinancialStatementItem`, across every
    `FinancialStatement` in `document.statements`. Order follows
    `document.statements` insertion order, then each statement's own
    (already period/concept-sorted) `items` order.
    """
    claims: list[Claim] = []
    for statement_name, statement in document.statements.items():
        for item in statement.items:
            claims.append(_build_claim(document, statement_name, item))
    return claims


def _build_claim(document: FinancialDocument, statement_name: str, item: FinancialStatementItem) -> Claim:
    period_label = _format_period_label(item.period)
    question = f"What is {item.concept} for {document.company_name} ({period_label})?"

    entity = Entity(name=document.company_name, ticker=document.ticker, cik=document.cik)
    metric = Metric(name=item.concept, canonical_name=item.concept, unit=item.unit)

    metadata: dict[str, object] = {
        "source": item.source_ref,
        "statement": statement_name,
        "filing_type": document.filing_type,
        "filing_date": document.filing_date.isoformat(),
    }
    if item.xbrl_tag is not None:
        metadata["xbrl_tag"] = item.xbrl_tag
    if document.source_url is not None:
        metadata["source_url"] = document.source_url

    return Claim(
        question=question,
        raw_value=item.value,
        metric=metric,
        entity=entity,
        period=_format_period_value(item.period),
        metadata=metadata,
    )


def _format_period_label(period: FinancialPeriod) -> str:
    """Human-readable period for the question string, e.g. 'Q2 2024' or 'FY2024'."""
    if period.fiscal_quarter:
        return f"Q{period.fiscal_quarter} {period.fiscal_year}"
    return f"FY{period.fiscal_year}"


def _format_period_value(period: FinancialPeriod) -> str:
    """Compact machine-oriented value for Claim.period, e.g. 'Q2 2024' or '2024'."""
    if period.fiscal_quarter:
        return f"Q{period.fiscal_quarter} {period.fiscal_year}"
    return str(period.fiscal_year)
