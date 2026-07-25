"""The single reusable FinVerify verification entry point."""

from typing import Optional

from .compiler import compile_claim
from .evidence import EvidenceRetriever
from .math_engine import MathEngine
from .models import Claim, VerificationContext, VerificationResult
from .output import build_result
from .resolvers import resolve_entity, resolve_metric, resolve_time
from .trust import score


def verify(claim: Claim | dict, *, evidence_retriever: Optional[EvidenceRetriever] = None) -> VerificationResult:
    """Compile, resolve, retrieve evidence, validate, score, and build output."""
    compiled = compile_claim(claim)
    compiled = resolve_entity(resolve_metric(resolve_time(compiled)))
    context = VerificationContext(
        claim=compiled,
        entity=compiled.entity,
        metric=compiled.metric,
        period=compiled.period,
        metadata=dict(compiled.metadata),
        current_value=compiled.raw_value,
    )
    if evidence_retriever is None:
        from providers.registry import default_registry

        evidence_retriever = EvidenceRetriever(default_registry())
    evidence = evidence_retriever.retrieve(compiled, context=context)
    math_engine = MathEngine()
    math_result = math_engine.run(compiled, context)
    verified, corrections, label, color = math_engine.to_legacy_tuple(math_result, compiled, context)
    trust = score(label, color, corrections, evidence, context=context)
    return build_result(compiled, verified, corrections, trust, evidence, context=context)
