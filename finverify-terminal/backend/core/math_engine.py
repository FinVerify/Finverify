"""Math stage backed by the existing, tested DVL implementation."""

from .models import Claim


def validate(claim: Claim) -> tuple[float | None, list[dict], str, str]:
    from app.dvl import full_verify

    if claim.raw_value is None:
        return None, [], "LOW", "#f87171"
    return full_verify(claim.question, claim.raw_value, claim.actual_value)
