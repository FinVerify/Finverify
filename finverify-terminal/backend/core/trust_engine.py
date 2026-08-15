"""Deterministic findings-based trust scoring for verification results."""

from typing import Any

from providers.base import resolve_provider_tier

from .identity_verification import EvidenceValueComparison
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
    VerificationStatus,
    VerificationContext,
)

# PHASE 3A: sentinel distinguishing "caller did not opt into the claim-value
# comparison gate" from "the gate was attempted but no comparison could be
# made" (which is a legitimate `None`). Only callers that explicitly pass
# `value_comparison` (currently core.engine.verify(), the live verification
# entry point) get the new, stricter VERIFIED/CONTRADICTED gating below.
# Existing callers that construct trust scores directly (e.g.
# core.financial.reasoning.ReasoningEngine, and every pre-Phase-3A test that
# calls compute_trust with its original 3-argument signature) keep their
# exact previous behavior -- this is an additive, backward-compatible wiring
# of the existing identity/value comparison machinery into the live pipeline,
# not a rebuild of trust scoring itself.
_VALUE_COMPARISON_NOT_SUPPLIED = object()


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
    score: float | None,
    colour: str,
    reason: str,
    status: VerificationStatus = VerificationStatus.VERIFIED,
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
        status=status,
        findings=findings,
    )


def compute_trust(
    context: VerificationContext,
    math_result: MathResult,
    evidence: list[Evidence],
    value_comparison: "EvidenceValueComparison | None" = _VALUE_COMPARISON_NOT_SUPPLIED,
) -> TrustScore:
    """Compute deterministic trust metadata from context, math, and evidence.

    `value_comparison` is the result of running the existing
    identity/value comparison machinery (core.identity_verification) for
    this claim, or None if that comparison could not be attempted (e.g. no
    canonical metric was resolved). When a caller supplies it -- which the
    live core.engine.verify() pipeline now does -- independent evidence
    (PRIMARY/SECONDARY tier) is no longer sufficient on its own for
    VERIFIED: the claimed value must actually match the evidence value in a
    compatible period. Callers that omit the argument entirely keep the
    prior behavior unchanged.
    """
    findings = compute_findings(context, math_result, evidence)
    if findings.evidence_tier is EvidenceTier.USER and context.claim.raw_value is not None:
        return build_trust(
            findings,
            "N/A",
            None,
            "#888888",
            "No independent evidence available",
            status=VerificationStatus.UNVERIFIED,
        )

    label, score, colour, reason = derive_label(findings)

    gated_tiers = (EvidenceTier.PRIMARY, EvidenceTier.SECONDARY)
    if value_comparison is not _VALUE_COMPARISON_NOT_SUPPLIED and findings.evidence_tier in gated_tiers:
        if value_comparison is not None and value_comparison.matched:
            status = VerificationStatus.VERIFIED
        elif value_comparison is not None and value_comparison.saw_period_match:
            # Compatible entity/metric/period evidence exists, but the
            # claimed value itself does not match it within tolerance.
            status = VerificationStatus.CONTRADICTED
            label, score, colour = "LOW", 0.0, DEFAULT_COLOUR
            reason = "Claim value contradicts the matched primary-source evidence"
        else:
            # Independent evidence exists, but it could not be positively
            # tied to this claim (wrong/unresolved metric or period). Stay
            # conservative rather than claiming VERIFIED on tier alone.
            status = VerificationStatus.UNVERIFIED
            label, score, colour = "N/A", None, "#888888"
            reason = "Independent evidence available, but it could not be matched to this claim"
        return build_trust(findings, label, score, colour, reason, status=status)

    status = (
        VerificationStatus.CONTRADICTED
        if findings.consistency is Consistency.FAIL or findings.rule_evidence is RuleEvidence.CONFLICTING
        else VerificationStatus.VERIFIED
    )
    return build_trust(findings, label, score, colour, reason, status=status)
