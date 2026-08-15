"""Small deterministic resolvers used by the core pipeline."""

import re
from functools import lru_cache
from pathlib import Path

from .financial.company import resolve_company
from .financial.concepts import ConceptRegistry
from .financial.period import parse_period_string
from .models import Claim, Entity, Metric


_METRIC_TERMS = (
    "revenue", "income", "margin", "ratio", "growth", "shares", "eps",
    "assets", "liabilities", "cash flow", "yield", "return", "securities",
)


@lru_cache(maxsize=1)
def _concept_registry() -> ConceptRegistry:
    return ConceptRegistry(Path(__file__).resolve().parents[1] / "config" / "concepts.yaml")


def _context_text(claim: Claim) -> str:
    return " ".join(part for part in (claim.context_text, claim.raw_text, claim.entity_hint, claim.metric_hint, claim.period_hint, claim.question) if part)


def _resolve_concept(value: str | None) -> str | None:
    if not value:
        return None
    registry = _concept_registry()
    direct = registry.resolve_alias(value.strip()) or registry.resolve_alias(value.strip().replace("_", " "))
    if direct:
        return direct
    candidates: list[tuple[int, str]] = []
    needle = value.lower().replace("_", " ")
    for alias, concept in registry.alias_map.items():
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", needle):
            candidates.append((len(alias), concept))
    return max(candidates, default=(0, None))[1]


def resolve_entity(claim: Claim) -> Claim:
    if claim.entity is not None:
        return claim
    company = resolve_company(_context_text(claim))
    if company:
        claim.entity = Entity(name=company.matched_text, ticker=company.ticker, cik=company.cik)
    return claim


def resolve_metric(claim: Claim) -> Claim:
    if claim.metric is not None:
        return claim
    resolved = _resolve_concept(claim.metric_hint)
    if resolved is None:
        resolved = _resolve_concept(_context_text(claim))
    if resolved:
        concept = _concept_registry().get_concept(resolved)
        display_name = resolved if claim.metric_hint else resolved.lower()
        claim.metric = Metric(name=display_name, canonical_name=display_name, unit=concept.get("unit"))
        return claim
    question = _context_text(claim).lower()
    match = next((term for term in _METRIC_TERMS if term in question), None)
    if match:
        claim.metric = Metric(name=match, canonical_name=match.replace(" ", "_"))
    return claim


def resolve_time(claim: Claim) -> Claim:
    if claim.period is None:
        source = _context_text(claim)
        candidate = claim.period_hint or source
        parsed = parse_period_string(candidate)
        match = re.search(r"\b(?:Q[1-4]\s*(?:FY\s*)?|FY\s*)?20\d{2}\b", candidate, re.IGNORECASE)
        if match:
            claim.period = claim.period_hint or match.group(0)
        if parsed is not None:
            claim.period_struct = parsed
    return claim
