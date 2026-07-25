"""Small deterministic resolvers used by the core pipeline."""

import re

from .models import Claim, Entity, Metric


_METRIC_TERMS = (
    "revenue", "income", "margin", "ratio", "growth", "shares", "eps",
    "assets", "liabilities", "cash flow", "yield", "return", "securities",
)


def resolve_entity(claim: Claim) -> Claim:
    if claim.entity is not None:
        return claim
    ticker = re.search(r"\b[A-Z]{2,5}\b", claim.question)
    if ticker:
        claim.entity = Entity(name=ticker.group(0), ticker=ticker.group(0))
    return claim


def resolve_metric(claim: Claim) -> Claim:
    if claim.metric is not None:
        return claim
    question = claim.question.lower()
    match = next((term for term in _METRIC_TERMS if term in question), None)
    if match:
        claim.metric = Metric(name=match, canonical_name=match.replace(" ", "_"))
    return claim


def resolve_time(claim: Claim) -> Claim:
    if claim.period is None:
        match = re.search(r"\b(?:Q[1-4]\s*)?20\d{2}\b", claim.question, re.IGNORECASE)
        if match:
            claim.period = match.group(0)
    return claim
