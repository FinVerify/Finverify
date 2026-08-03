"""The single reusable FinVerify verification entry point."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .compiler import compile_claim
from .evidence import EvidenceRetriever
from .math_engine import MathEngine
from .models import (
    BatchClaim,
    BatchVerifyRequest,
    BatchVerifyResponse,
    Claim,
    Entity,
    Metric,
    VerificationContext,
    VerificationResult,
)
from .output import build_result
from .resolvers import resolve_entity, resolve_metric, resolve_time
from .trust_engine import compute_trust

if TYPE_CHECKING:
    from .financial.concepts import ConceptRegistry
    from .financial.constraints import ConstraintResult

logger = logging.getLogger(__name__)


def verify(claim: Claim | dict, *, evidence_retriever: Optional[EvidenceRetriever] = None) -> VerificationResult:
    """Compile, resolve, retrieve evidence, validate, score, and build output."""
    compiled = compile_claim(claim)
    compiled = resolve_entity(resolve_metric(resolve_time(compiled)))
    context = VerificationContext(
        claim=compiled,
        entity=compiled.entity,
        metric=compiled.metric,
        period=compiled.period,
        period_struct=compiled.period_struct,
        metadata=dict(compiled.metadata),
        current_value=compiled.raw_value,
    )
    if evidence_retriever is None:
        from providers.registry import default_registry

        evidence_retriever = EvidenceRetriever(default_registry())
    evidence = evidence_retriever.retrieve(compiled, context=context)
    math_engine = MathEngine()
    math_result = math_engine.run(compiled, context)
    corrections = [
        {"rule": correction.rule, "before": correction.before, "after": correction.after}
        for correction in math_result.corrections
    ]
    constraint_result = _run_constraint_verification(context, evidence, math_result.verified_value)
    trust = compute_trust(context, math_result, evidence)
    return build_result(
        compiled,
        math_result.verified_value,
        corrections,
        trust,
        evidence,
        context=context,
        constraint_result=constraint_result,
    )


def verify_batch(
    request: BatchVerifyRequest,
    *,
    evidence_retriever: Optional[EvidenceRetriever] = None,
) -> BatchVerifyResponse:
    """
    Verify multiple claims in a single batch.

    Each claim is processed through the existing single-claim pipeline, then the
    shared constraint engine evaluates the verified batch as a whole.
    """
    results: list[VerificationResult] = []
    for batch_claim in request.claims:
        result = verify(_build_batch_claim(batch_claim), evidence_retriever=evidence_retriever)
        results.append(_clear_constraint_result(result))

    constraint_result = None
    if request.include_constraints and len(results) >= 2:
        constraint_result = _run_batch_constraint_verification(results, tolerance=request.tolerance)

    return BatchVerifyResponse(results=results, constraint_result=constraint_result)


def _run_constraint_verification(
    context: VerificationContext,
    evidence: list,
    verified_value: float | None,
) -> "ConstraintResult" | None:
    try:
        from .financial.constraints import ConstraintVerifier

        registry = _load_constraint_registry()
        equations = registry.load_equations()
        if not equations:
            return None
        claims_map = build_claims_map(context, evidence, verified_value, registry=registry)
        if len(claims_map) < 2:
            return None
        return ConstraintVerifier(equations).verify(claims_map)
    except Exception as exc:
        logger.warning("Constraint verification failed for %r: %s", context.claim.question, exc)
        return None


def _run_batch_constraint_verification(
    results: list[VerificationResult],
    *,
    tolerance: float | None,
) -> "ConstraintResult" | None:
    try:
        from .financial.constraints import ConstraintVerifier

        registry = _load_constraint_registry()
        equations = registry.load_equations()
        if not equations:
            return None
        claims_map = _build_batch_claims_map(results, registry=registry)
        if len(claims_map) < 2:
            return None
        rel_tol = 1e-6 if tolerance is None else float(tolerance)
        return ConstraintVerifier(equations, rel_tol=rel_tol).verify(claims_map)
    except Exception as exc:
        logger.warning("Batch constraint verification failed: %s", exc)
        return None


def build_claims_map(
    context: VerificationContext,
    evidence: list,
    verified_value: float | None,
    *,
    registry: "ConceptRegistry" | None = None,
) -> dict[str, float | dict[str, object]]:
    """Build a constraint-ready metric map from the verified claim, metadata, and evidence."""
    registry = registry or _load_constraint_registry()
    claims_map: dict[str, float | dict[str, object]] = {}

    metric_name = _resolve_constraint_metric(context.metric, registry)
    if metric_name is not None and verified_value is not None:
        claims_map[metric_name] = _build_claim_entry(verified_value, unit=context.metric.unit if context.metric else None)

    for raw_claim in context.metadata.get("related_claims", []):
        if not isinstance(raw_claim, dict):
            continue
        related_metric = _resolve_constraint_metric(raw_claim.get("metric"), registry)
        related_value = raw_claim.get("verified_value", raw_claim.get("value"))
        if related_metric is None or related_value is None:
            continue
        claims_map[related_metric] = _build_claim_entry(
            related_value,
            unit=raw_claim.get("unit"),
            dimension=raw_claim.get("dimension"),
        )

    for item in evidence:
        evidence_metric = _resolve_constraint_metric(getattr(item, "metric", None), registry)
        evidence_value = getattr(item, "value", None)
        if evidence_metric is None or evidence_value is None or evidence_metric in claims_map:
            continue
        claims_map[evidence_metric] = _build_claim_entry(
            evidence_value,
            unit=getattr(item, "unit", None),
            dimension=getattr(item, "dimension", None),
        )

    return claims_map


def _build_batch_claims_map(
    results: list[VerificationResult],
    *,
    registry: "ConceptRegistry" | None = None,
) -> dict[str, float | dict[str, object]]:
    registry = registry or _load_constraint_registry()
    claims_map: dict[str, float | dict[str, object]] = {}

    for result in results:
        if result.verified_value is None:
            continue
        metric_name = _resolve_result_metric(result, registry)
        if metric_name is None:
            continue
        concept = registry.get_concept(metric_name)
        unit = result.claim.metric.unit if result.claim.metric is not None else None
        claims_map[metric_name] = _build_claim_entry(
            result.verified_value,
            unit=unit or concept.get("unit"),
            dimension=concept.get("dimension"),
        )

    return claims_map


@lru_cache(maxsize=1)
def _load_constraint_registry() -> "ConceptRegistry":
    from .financial.concepts import ConceptRegistry

    config_path = Path(__file__).resolve().parents[1] / "config" / "concepts.yaml"
    return ConceptRegistry(config_path)


def _resolve_constraint_metric(metric: Metric | str | object | None, registry: "ConceptRegistry") -> str | None:
    candidates: list[str] = []
    if isinstance(metric, Metric):
        candidates.extend([metric.canonical_name or "", metric.name])
    elif isinstance(metric, str):
        candidates.append(metric)

    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized:
            continue
        if normalized in registry.concepts:
            return normalized
        resolved = registry.resolve_alias(normalized)
        if resolved is not None:
            return resolved
        resolved = registry.resolve_alias(normalized.replace("_", " "))
        if resolved is not None:
            return resolved
    return None


def _resolve_result_metric(result: VerificationResult, registry: "ConceptRegistry") -> str | None:
    resolved = _resolve_constraint_metric(result.claim.metric, registry)
    if resolved is not None:
        return resolved
    return _resolve_constraint_metric(result.claim.question, registry)


def _build_batch_claim(batch_claim: BatchClaim) -> Claim:
    metric = Metric(name=batch_claim.metric, canonical_name=batch_claim.metric) if batch_claim.metric else None
    entity = (
        Entity(
            name=batch_claim.entity,
            ticker=batch_claim.ticker,
            cik=batch_claim.cik,
        )
        if batch_claim.entity
        else None
    )
    return Claim(
        question=batch_claim.question,
        raw_value=batch_claim.raw_value,
        actual_value=batch_claim.actual_value,
        metric=metric,
        entity=entity,
        period=batch_claim.period,
        period_struct=batch_claim.period_struct,
    )


def _clear_constraint_result(result: VerificationResult) -> VerificationResult:
    if result.constraint_result is None:
        return result
    if hasattr(result, "model_copy"):
        return result.model_copy(update={"constraint_result": None})
    return result.copy(update={"constraint_result": None})


def _build_claim_entry(
    value: float,
    *,
    unit: str | None = None,
    dimension: str | None = None,
) -> float | dict[str, object]:
    if unit is None and dimension is None:
        return float(value)

    entry: dict[str, object] = {"value": float(value)}
    if unit is not None:
        entry["unit"] = unit
    if dimension is not None:
        entry["dimension"] = dimension
    return entry
