"""Unit tests for the deterministic TrustEngine."""

import core.trust_engine as trust_engine
from core.engine import verify
from core.models import (
    Ambiguity,
    Claim,
    Consistency,
    Correction,
    CorrectionSeverity,
    Evidence,
    EvidenceTier,
    MathResult,
    RuleEvidence,
    Source,
    TrustFindings,
    VerificationContext,
)
from providers.base import ProviderRegistry, resolve_provider_tier


def make_context(
    *,
    provider: str | None = "sec_edgar",
    provider_metadata: dict | None = None,
    raw_value: float | None = 10.0,
) -> VerificationContext:
    claim = Claim(question="What was the metric?", raw_value=raw_value)
    return VerificationContext(
        claim=claim,
        entity=claim.entity,
        metric=claim.metric,
        period=claim.period,
        provider=provider,
        provider_metadata=provider_metadata or {},
        metadata=dict(claim.metadata),
        current_value=raw_value,
    )


def make_math_result(*rule_names: str, verified_value: float | None = 10.0) -> MathResult:
    corrections = [
        Correction(rule=rule_name, before=10.0, after=11.0 + index)
        for index, rule_name in enumerate(rule_names)
    ]
    return MathResult(verified_value=verified_value, corrections=corrections)


def test_primary_no_correction_low_ambiguity_pass():
    findings = TrustFindings(
        evidence_tier=EvidenceTier.PRIMARY,
        correction_severity=CorrectionSeverity.NONE,
        ambiguity=Ambiguity.LOW,
        consistency=Consistency.PASS,
        rule_evidence=RuleEvidence.SINGLE,
    )
    label, score, colour, _ = trust_engine.derive_label(findings)
    assert label == "HIGH"
    assert score == 0.90
    assert colour == "#00ff88"


def test_default_fallback_for_unmatched_combination():
    findings = TrustFindings(
        evidence_tier=EvidenceTier.MODEL,
        correction_severity=CorrectionSeverity.MULTIPLE,
        ambiguity=Ambiguity.HIGH,
        consistency=Consistency.FAIL,
        rule_evidence=RuleEvidence.MULTIPLE_AGREE,
    )
    label, score, colour, reason = trust_engine.derive_label(findings)
    assert label == "LOW"
    assert score == 0.25
    assert colour == "#f87171"
    assert reason == "Default fallback"


def test_wildcard_rule_matches_when_exact_rule_does_not():
    findings = TrustFindings(
        evidence_tier=EvidenceTier.PRIMARY,
        correction_severity=CorrectionSeverity.NONE,
        ambiguity=Ambiguity.MEDIUM,
        consistency=Consistency.PASS,
        rule_evidence=RuleEvidence.NONE,
    )
    label, score, colour, reason = trust_engine.derive_label(findings)
    assert label == "HIGH"
    assert score == 0.88
    assert colour == "#00ff88"
    assert reason == "Primary source with passing consistency"


def test_rule_ordering_uses_first_match(monkeypatch):
    first_rule = {
        "match": (EvidenceTier.PRIMARY, CorrectionSeverity.NONE, None, Consistency.PASS),
        "label": "MEDIUM",
        "score": 0.55,
        "colour": "#fbbf24",
        "reason": "First match wins",
    }
    monkeypatch.setattr(trust_engine, "TRUST_RULES", [first_rule, *trust_engine.TRUST_RULES])

    findings = TrustFindings(
        evidence_tier=EvidenceTier.PRIMARY,
        correction_severity=CorrectionSeverity.NONE,
        ambiguity=Ambiguity.LOW,
        consistency=Consistency.PASS,
        rule_evidence=RuleEvidence.NONE,
    )
    label, score, colour, reason = trust_engine.derive_label(findings)
    assert label == "MEDIUM"
    assert score == 0.55
    assert colour == "#fbbf24"
    assert reason == "First match wins"


def test_compute_findings_classifies_scale_only_correction():
    findings = trust_engine.compute_findings(
        make_context(provider="sec_edgar", provider_metadata={"tier": "primary"}),
        make_math_result("scale_mul100"),
        [],
    )
    assert findings.evidence_tier is EvidenceTier.PRIMARY
    assert findings.correction_severity is CorrectionSeverity.SCALE_ONLY
    assert findings.ambiguity is Ambiguity.LOW
    assert findings.consistency is Consistency.PASS
    assert findings.rule_evidence is RuleEvidence.SINGLE


def test_compute_findings_sign_correction_sets_high_ambiguity():
    findings = trust_engine.compute_findings(
        make_context(provider="model_input", provider_metadata={"tier": "model"}),
        make_math_result("sign_corrected"),
        [],
    )
    assert findings.evidence_tier is EvidenceTier.MODEL
    assert findings.correction_severity is CorrectionSeverity.SIGN_ONLY
    assert findings.ambiguity is Ambiguity.HIGH
    assert findings.rule_evidence is RuleEvidence.SINGLE


def test_compute_findings_multiple_rules_mark_multiple_agree():
    findings = trust_engine.compute_findings(
        make_context(provider="SEC EDGAR", provider_metadata={"tier": "primary"}),
        make_math_result("scale_mul100", "magnitude_x10"),
        [],
    )
    assert findings.correction_severity is CorrectionSeverity.MULTIPLE
    assert findings.ambiguity is Ambiguity.MEDIUM
    assert findings.rule_evidence is RuleEvidence.MULTIPLE_AGREE


def test_provider_tier_resolution_prefers_metadata():
    assert resolve_provider_tier("unknown_provider", {"tier": "secondary"}) is EvidenceTier.SECONDARY


def test_provider_tier_resolution_uses_name_fallbacks():
    assert resolve_provider_tier("SEC EDGAR") is EvidenceTier.PRIMARY
    assert resolve_provider_tier("fred_api") is EvidenceTier.SECONDARY
    assert resolve_provider_tier("model_input") is EvidenceTier.MODEL
    assert resolve_provider_tier("custom_upload") is EvidenceTier.USER


def test_registry_resolution_uses_registered_provider_metadata():
    class FakeProvider:
        name = "custom_primary"
        metadata = {"tier": "primary"}

        def can_handle(self, claim: Claim) -> bool:
            return True

        def retrieve(self, claim: Claim) -> list[Evidence]:
            return []

    registry = ProviderRegistry([FakeProvider()])
    assert registry.resolve_evidence_tier("custom_primary") is EvidenceTier.PRIMARY


def test_build_trust_keeps_findings_internal():
    findings = TrustFindings(
        evidence_tier=EvidenceTier.PRIMARY,
        correction_severity=CorrectionSeverity.NONE,
        ambiguity=Ambiguity.LOW,
        consistency=Consistency.PASS,
        rule_evidence=RuleEvidence.NONE,
    )
    trust = trust_engine.build_trust(findings, "HIGH", 0.90, "#00ff88", "Primary source")
    dumped = trust.model_dump()
    assert dumped["label"] == "HIGH"
    assert dumped["color"] == "#00ff88"
    assert "findings" not in dumped
    assert "Evidence tier: primary" in trust.reasons


def test_compute_findings_can_fall_back_to_evidence_source_name():
    findings = trust_engine.compute_findings(
        make_context(provider=None, provider_metadata={}),
        make_math_result(),
        [
            Evidence(
                source=Source(name="SEC EDGAR", authority=1.0),
                claim="What was revenue?",
                value=10.0,
            ),
        ],
    )
    assert findings.evidence_tier is EvidenceTier.PRIMARY


def test_core_verify_uses_new_trust_engine_without_mutating_math_outputs():
    claim = Claim(
        question="What was the percentage decrease in HTM securities?",
        raw_value=-34.11,
        actual_value=0.34146,
    )
    result = verify(claim)
    assert result.verified_value == 0.3411
    assert [entry["rule"] for entry in result.correction_log] == ["scale_div100", "sign_corrected"]
    assert result.trust_score.label == "LOW"
    assert result.trust_score.color == "#f87171"
