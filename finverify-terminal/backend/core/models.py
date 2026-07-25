"""Shared domain contracts for all FinVerify consumers."""

from typing import Any, Optional

from pydantic import BaseModel, Field


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


class TrustScore(BaseModel):
    label: str = "LOW"
    score: float = Field(0.0, ge=0.0, le=1.0)
    color: str = "#f87171"
    reasons: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    question: str
    raw_value: Optional[float] = None
    raw_text: Optional[str] = None
    actual_value: Optional[float] = None
    entity: Optional[Entity] = None
    metric: Optional[Metric] = None
    period: Optional[str] = None
    model_source: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    claim: Claim
    verified_value: Optional[float] = None
    correction_log: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    calculations: list[Calculation] = Field(default_factory=list)
    trust_score: TrustScore
    mode: str = "numerical"
    verified: bool = False

    @property
    def question(self) -> str:
        return self.claim.question
