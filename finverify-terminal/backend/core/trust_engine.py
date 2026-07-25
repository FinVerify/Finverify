"""Deterministic findings-based trust scoring for verification results."""

from typing import Any

from providers.base import resolve_provider_tier

from .models import (
    Ambiguity,
    Consistency,
    CorrectionSeverity,
    Evidence,
    EvidenceTier,
    MathResult,
    RuleEvidence,
    TrustFindings,
    TrustScore,
    VerificationContext,
)


TRUST_RULES: list[dict[str, Any]] = [
    {
        "match": (EvidenceTier.PRIMARY, CorrectionSeverity.NONE, Ambiguity.LOW, Consistency.PASS),
        "label": "HIGH",
        "score": 0.90,
        "colour": "#00ff88",
        "reason": "Primary source, no corrections, low ambiguity",
    },
    {
        "match": (EvidenceTier.PRIMARY, CorrectionSeverity.SCALE_ONLY, Ambiguity.LOW, Consistency.PASS),
        "label": "HIGH",
        "score": 0.90,
        "colour": "#00ff88",
        "reason": "Primary source, scale correction only",
    },
    {
        "match": (EvidenceTier.SECONDARY, CorrectionSeverity.NONE, Ambiguity.LOW, Consistency.PASS),
        "label": "HIGH",
        "score": 0.85,
        "colour": "#00ff88",
        "reason": "Secondary source, no corrections",
    },
    {
        "match": (EvidenceTier.SECONDARY, CorrectionSeverity.SCALE_ONLY, Ambiguity.LOW, Consistency.PASS),
        "label": "MEDIUM",
        "score": 0.65,
        "colour": "#fbbf24",
        "reason": "Secondary source, scale correction",
    },
    {
        "match": (EvidenceTier.PRIMARY, CorrectionSeverity.MULTIPLE, Ambiguity.MEDIUM, Consistency.PASS),
        "label": "MEDIUM",
        "score": 0.60,
        "colour": "#fbbf24",
        "reason": "Primary source, multiple corrections, medium ambiguity",
    },
    {
        "match": (EvidenceTier.PRIMARY, CorrectionSeverity.NONE, None, Consistency.PASS),
        "label": "HIGH",
        "score": 0.88,
        "colour": "#00ff88",
        "reason": "Primary source with passing consistency",
    },
]

DEFAULT_LABEL = "LOW"
DEFAULT_SCORE = 0.25
DEFAULT_COLOUR = "#f87171"
DEFAULT_REASON = "Default fallback"


def _rule_names(math_result: MathResult) -> set[str]:
    return {correction.rule for correction in math_result.corrections}


def _assess_correction_severity(rule_names: set[str]) -> CorrectionSeverity:
    if not rule_names:
        return CorrectionSeverity.NONE

    categories = {
        "scale" if rule_name.startswith("scale_")
        else "sign" if rule_name.startswith("sign_")
        else "magnitude" if rule_name.startswith("magnitude_")
        else "other"
        for rule_name in rule_names
    }
    if len(categories) > 1 or "other" in categories:
        return CorrectionSeverity.MULTIPLE
    if "scale" in categories:
        return CorrectionSeverity.SCALE_ONLY
    if "sign" in categories:
        return CorrectionSeverity.SIGN_ONLY
    if "magnitude" in categories:
        return CorrectionSeverity.MAGNITUDE_ONLY
    return CorrectionSeverity.MULTIPLE


def _assess_ambiguity(rule_names: set[str]) -> Ambiguity:
    if any(rule_name.startswith("sign_") for rule_name in rule_names):
        return Ambiguity.HIGH
    if any(rule_name.startswith("magnitude_") for rule_name in rule_names):
        return Ambiguity.MEDIUM
    return Ambiguity.LOW


def _assess_rule_evidence(rule_names: set[str]) -> RuleEvidence:
    if not rule_names:
        return RuleEvidence.NONE
    if len(rule_names) == 1:
        return RuleEvidence.SINGLE
    return RuleEvidence.MULTIPLE_AGREE


def compute_findings(
    context: VerificationContext,
    math_result: MathResult,
    evidence: list[Evidence],
) -> TrustFindings:
    """Observe evidence and math facts without referencing trust labels."""
    provider_name = context.provider
    if provider_name is None and evidence:
        provider_name = evidence[0].source.name

    rule_names = _rule_names(math_result)
    return TrustFindings(
        evidence_tier=resolve_provider_tier(provider_name, context.provider_metadata),
        correction_severity=_assess_correction_severity(rule_names),
        ambiguity=_assess_ambiguity(rule_names),
        consistency=Consistency.PASS,
        rule_evidence=_assess_rule_evidence(rule_names),
    )


def derive_label(findings: TrustFindings) -> tuple[str, float, str, str]:
    for rule in TRUST_RULES:
        match = rule["match"]
        if (
            (match[0] is None or match[0] == findings.evidence_tier)
            and (match[1] is None or match[1] == findings.correction_severity)
            and (match[2] is None or match[2] == findings.ambiguity)
            and (match[3] is None or match[3] == findings.consistency)
        ):
            return rule["label"], rule["score"], rule["colour"], rule["reason"]
    return DEFAULT_LABEL, DEFAULT_SCORE, DEFAULT_COLOUR, DEFAULT_REASON


def build_trust(
    findings: TrustFindings,
    label: str,
    score: float,
    colour: str,
    reason: str,
) -> TrustScore:
    """Build the public trust payload without exposing internal findings."""
    reasons = [
        reason,
        f"Evidence tier: {findings.evidence_tier.value}",
        f"Corrections: {findings.correction_severity.value}",
        f"Ambiguity: {findings.ambiguity.value}",
        f"Consistency: {findings.consistency.value}",
        f"Rule evidence: {findings.rule_evidence.value}",
    ]
    return TrustScore(
        label=label,
        score=score,
        color=colour,
        reasons=reasons,
        findings=findings,
    )


def compute_trust(
    context: VerificationContext,
    math_result: MathResult,
    evidence: list[Evidence],
) -> TrustScore:
    """Compute deterministic trust metadata from context, math, and evidence."""
    findings = compute_findings(context, math_result, evidence)
    label, score, colour, reason = derive_label(findings)
    return build_trust(findings, label, score, colour, reason)
