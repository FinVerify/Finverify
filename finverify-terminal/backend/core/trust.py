"""Trust stage translating legacy DVL labels into a reusable score contract."""

from .models import Evidence, TrustScore


_SCORES = {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.25}
_COLORS = {"HIGH": "#00ff88", "MEDIUM": "#fbbf24", "LOW": "#f87171"}


def score(label: str, color: str, corrections: list[dict], evidence: list[Evidence]) -> TrustScore:
    reasons = []
    if corrections:
        reasons.append(f"{len(corrections)} deterministic correction(s) applied")
    if evidence:
        best = max(item.source.authority for item in evidence)
        if best >= 0.8:
            reasons.append("supported by an authoritative source")
        elif best <= 0.2:
            reasons.append("source is model-provided input")
    return TrustScore(
        label=label,
        score=_SCORES.get(label, 0.0),
        color=_COLORS.get(label, color),
        reasons=reasons,
    )
