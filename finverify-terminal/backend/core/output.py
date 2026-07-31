"""Output stage for the shared verification result."""

from typing import TYPE_CHECKING, Any

from .models import Calculation, Claim, Evidence, VerificationContext, VerificationResult, TrustScore

if TYPE_CHECKING:
    from core.financial.constraints import ConstraintResult
else:
    ConstraintResult = Any


def build_result(
    claim: Claim,
    verified_value: float | None,
    corrections: list[dict],
    trust: TrustScore,
    evidence: list[Evidence],
    context: VerificationContext | None = None,
    constraint_result: ConstraintResult | None = None,
) -> VerificationResult:
    from app.dvl import format_correction_log

    formatted_corrections = format_correction_log(corrections)
    return VerificationResult(
        claim=claim,
        verified_value=verified_value,
        correction_log=formatted_corrections,
        evidence=evidence,
        calculations=[Calculation(
            name="deterministic_dvl",
            inputs={
                "raw_value": claim.raw_value,
                "provider": context.provider if context is not None else None,
                "evidence_mode": context.evidence_mode if context is not None else None,
            },
            output=verified_value,
            passed=verified_value is not None,
        )],
        trust_score=trust,
        constraint_result=constraint_result,
        verified=verified_value is not None,
    )
