"""The single reusable FinVerify verification entry point."""

from typing import Optional

from .compiler import compile_claim
from .evidence import EvidenceRetriever
from .models import Claim, VerificationResult
from .math_engine import validate
from .output import build_result
from .resolvers import resolve_entity, resolve_metric, resolve_time
from .trust import score


def verify(claim: Claim | dict, *, evidence_retriever: Optional[EvidenceRetriever] = None) -> VerificationResult:
    """Compile, resolve, retrieve evidence, validate, score, and build output."""
    compiled = compile_claim(claim)
    compiled = resolve_entity(resolve_metric(resolve_time(compiled)))
    if evidence_retriever is None:
        from providers.registry import default_registry

        evidence_retriever = EvidenceRetriever(default_registry())
    evidence = evidence_retriever.retrieve(compiled)
    verified, corrections, label, color = validate(compiled)
    trust = score(label, color, corrections, evidence)
    return build_result(compiled, verified, corrections, trust, evidence)
