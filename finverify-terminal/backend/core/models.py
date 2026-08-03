"""Shared domain contracts for all FinVerify consumers."""

from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field
from core.financial.document import FinancialPeriod

if TYPE_CHECKING:
    from core.financial.constraints import ConstraintResult
else:
    ConstraintResult = Any


class Entity(BaseModel):
    name: str
    ticker: Optional[str] = None
    cik: Optional[str] = None
    lei: Optional[str] = None


class Metric(BaseModel):
    name: str
    canonical_name: Optional[str] = None
    unit: Optional[str] = None


class Source(BaseModel):
    name: str
    kind: str = "unknown"
    authority: float = Field(0.0, ge=0.0, le=1.0)
    url: Optional[str] = None
    retrieved_at: Optional[str] = None


class Evidence(BaseModel):
    source: Source
    claim: str
    value: Optional[float] = None
    excerpt: Optional[str] = None
    period: Optional[str] = None
    locator: Optional[str] = None


class Calculation(BaseModel):
    name: str
    expression: Optional[str] = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    output: Optional[float] = None
    passed: bool = True
    details: Optional[str] = None


class EvidenceTier(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MODEL = "model"
    USER = "user"


class CorrectionSeverity(str, Enum):
    NONE = "none"
    SCALE_ONLY = "scale_only"
    SIGN_ONLY = "sign_only"
    MAGNITUDE_ONLY = "magnitude_only"
    MULTIPLE = "multiple"


class Ambiguity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Consistency(str, Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"


class RuleEvidence(str, Enum):
    NONE = "none"
    SINGLE = "single_rule"
    MULTIPLE_AGREE = "multiple_agree"
    CONFLICTING = "conflicting"


class TrustFindings(BaseModel):
    evidence_tier: EvidenceTier
    correction_severity: CorrectionSeverity
    ambiguity: Ambiguity
    consistency: Consistency
    rule_evidence: RuleEvidence


class TrustScore(BaseModel):
    label: str = "LOW"
    score: float = Field(0.0, ge=0.0, le=1.0)
    color: str = "#f87171"
    reasons: list[str] = Field(default_factory=list)
    findings: Optional[TrustFindings] = Field(default=None, exclude=True)

    @property
    def colour(self) -> str:
        return self.color


class Claim(BaseModel):
    question: str
    raw_value: Optional[float] = None
    raw_text: Optional[str] = None
    actual_value: Optional[float] = None
    entity: Optional[Entity] = None
    metric: Optional[Metric] = None
    period: Optional[str] = None
    period_struct: Optional[FinancialPeriod] = None
    model_source: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchClaim(BaseModel):
    """A single claim in a batch verification request."""

    question: str
    raw_value: float
    metric: Optional[str] = None
    entity: Optional[str] = None
    ticker: Optional[str] = None
    cik: Optional[str] = None
    period: Optional[str] = None
    period_struct: Optional[FinancialPeriod] = None
    actual_value: Optional[float] = None


class BatchVerifyRequest(BaseModel):
    """Batch verification request."""

    claims: list[BatchClaim] = Field(default_factory=list)
    include_constraints: bool = True
    tolerance: Optional[float] = 1e-6


class VerificationContext(BaseModel):
    """Shared state that flows through compile, retrieval, math, and trust."""

    claim: Claim
    entity: Optional[Entity] = None
    metric: Optional[Metric] = None
    period: Optional[str] = None
    period_struct: Optional[FinancialPeriod] = None
    provider: Optional[str] = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_mode: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    current_value: Optional[float] = None
    ambiguous_scale: bool = False


class Correction(BaseModel):
    rule: str
    before: float
    after: float
    description: Optional[str] = None


class RuleResult(BaseModel):
    applied: bool = False
    corrected_value: Optional[float] = None
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuleTrace(BaseModel):
    results: list[RuleResult] = Field(default_factory=list)


class MathResult(BaseModel):
    verified_value: Optional[float] = None
    corrections: list[Correction] = Field(default_factory=list)
    rule_trace: RuleTrace = Field(default_factory=RuleTrace)
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class VerificationResult(BaseModel):
    claim: Claim
    verified_value: Optional[float] = None
    correction_log: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    calculations: list[Calculation] = Field(default_factory=list)
    trust_score: TrustScore
    constraint_result: Optional[ConstraintResult] = None
    mode: str = "numerical"
    verified: bool = False

    @property
    def question(self) -> str:
        return self.claim.question


class BatchVerifyResponse(BaseModel):
    """Batch verification response."""

    results: list[VerificationResult] = Field(default_factory=list)
    constraint_result: Optional[ConstraintResult] = None
