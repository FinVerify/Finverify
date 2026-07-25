"""Output stage for the shared verification result."""

from .models import Calculation, Claim, Evidence, VerificationResult, TrustScore


def build_result(
    claim: Claim,
    verified_value: float | None,
    corrections: list[dict],
    trust: TrustScore,
    evidence: list[Evidence],
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
            inputs={"raw_value": claim.raw_value},
            output=verified_value,
            passed=verified_value is not None,
        )],
        trust_score=trust,
        verified=verified_value is not None,
    )
