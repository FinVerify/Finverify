"""
finverify.models — Typed response models
==========================================
Design note: the SDK uses ``dataclasses`` rather than Pydantic for
response models. This matches the convention already established in
this repository's embedded SDK (``finverify-terminal/sdk-legacy/finverify/client.py``,
``dvl.py``) and keeps the core package dependency-free — the backend
itself uses Pydantic, but that is an internal implementation detail of
the FastAPI service, not something a client of the service needs.
Every model exposes ``.from_dict()`` for parsing and a ``.to_dict()``
for round-tripping, so nothing in the public API is a raw ``dict``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


def _get(data: dict, *names: str, default: Any = None) -> Any:
    """Fetch the first present key — lets us tolerate the API's few
    naming aliases (e.g. ``/verify`` uses ``raw_number`` while
    ``/v1/verify`` uses ``raw_value``) without duplicating models."""
    for name in names:
        if name in data:
            return data[name]
    return default


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

@dataclass
class CorrectionEntry:
    """One row of the DVL's audit log."""

    rule: str
    before: float
    after: float
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "CorrectionEntry":
        return cls(
            rule=data.get("rule", ""),
            before=data.get("before", 0.0),
            after=data.get("after", 0.0),
            description=data.get("description", ""),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VerifyResult:
    """Result of a call to ``POST /v1/verify``.

    This is the primary object returned by :meth:`FinVerify.verify`.
    """

    question: str
    raw_value: float
    verified_value: float
    trust_score: str  # HIGH | MEDIUM | LOW
    trust_color: str  # hex color, for direct use in UI
    delta_pct: float = 0.0
    correction_applied: Optional[str] = None
    dvl_version: str = "unknown"
    timestamp: str = ""
    request_id: Optional[str] = None

    @property
    def was_corrected(self) -> bool:
        return self.correction_applied is not None

    @property
    def is_high_trust(self) -> bool:
        return self.trust_score == "HIGH"

    @classmethod
    def from_dict(cls, data: dict, *, request_id: Optional[str] = None) -> "VerifyResult":
        return cls(
            question=data["question"],
            raw_value=_get(data, "raw_value", "raw_number"),
            verified_value=_get(data, "verified_value", "verified_number"),
            trust_score=data.get("trust_score", "HIGH"),
            trust_color=data.get("trust_color", "#00ff88"),
            delta_pct=data.get("delta_pct", 0.0),
            correction_applied=data.get("correction_applied"),
            dvl_version=data.get("dvl_version", "unknown"),
            timestamp=data.get("timestamp", ""),
            request_id=request_id,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BatchVerifyResult:
    """Result of :meth:`FinVerify.verify_batch`.

    The backend does not (yet) expose a native batch endpoint — see
    the SDK README's roadmap section — so this fans requests out
    concurrently and collects successes/failures positionally.
    """

    results: list[Optional[VerifyResult]]
    errors: list[Optional[BaseException]]

    @property
    def succeeded(self) -> list[VerifyResult]:
        return [r for r in self.results if r is not None]

    @property
    def failed_count(self) -> int:
        return sum(1 for e in self.errors if e is not None)

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self):
        return iter(self.results)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@dataclass
class HealthStatus:
    status: str
    dvl: str
    llm: str
    model: str

    @classmethod
    def from_dict(cls, data: dict) -> "HealthStatus":
        return cls(
            status=data.get("status", "unknown"),
            dvl=data.get("dvl", "unknown"),
            llm=data.get("llm", "unknown"),
            model=data.get("model", "unknown"),
        )

    @property
    def is_healthy(self) -> bool:
        return self.status == "ok"


# ---------------------------------------------------------------------------
# Fundamentals / earnings
# ---------------------------------------------------------------------------

@dataclass
class FundamentalsResult:
    ticker: str
    source: str
    metrics_count: int
    metrics: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "FundamentalsResult":
        return cls(
            ticker=data.get("ticker", ""),
            source=data.get("source", ""),
            metrics_count=data.get("metrics_count", 0),
            metrics=data.get("metrics", {}),
        )


@dataclass
class EarningsReport:
    """Raw pass-through for ``/v1/earnings/{ticker}``.

    The backend's earnings-verification report shape is intentionally
    open-ended (it varies with how many claims a transcript yields), so
    this model keeps the full parsed payload under ``.raw`` while
    surfacing the ticker for convenience.
    """

    ticker: str
    raw: dict

    @classmethod
    def from_dict(cls, data: dict) -> "EarningsReport":
        return cls(ticker=data.get("ticker", ""), raw=data)


# ---------------------------------------------------------------------------
# Financial Constraint Graph (FCG)
# ---------------------------------------------------------------------------

@dataclass
class FCGVerifyResult:
    input_count: int
    normalized_count: int
    constraint_result: dict
    normalization_map: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "FCGVerifyResult":
        return cls(
            input_count=data.get("input_count", 0),
            normalized_count=data.get("normalized_count", 0),
            constraint_result=data.get("constraint_result", {}),
            normalization_map=data.get("normalization_map", {}),
        )


@dataclass
class NormalizeResult:
    mapped: dict
    unmapped: list
    supported_metrics: list

    @classmethod
    def from_dict(cls, data: dict) -> "NormalizeResult":
        return cls(
            mapped=data.get("mapped", {}),
            unmapped=data.get("unmapped", []),
            supported_metrics=data.get("supported_metrics", []),
        )


@dataclass
class Constraint:
    id: str
    name: str
    description: str
    requires: list
    tolerance_pct: float
    severity: str

    @classmethod
    def from_dict(cls, data: dict) -> "Constraint":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            requires=data.get("requires", []),
            tolerance_pct=data.get("tolerance_pct", 0.0),
            severity=data.get("severity", ""),
        )


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

@dataclass
class SampleQuery:
    question: str
    actual: Optional[float]
    category: Optional[str]

    @classmethod
    def from_dict(cls, data: dict) -> "SampleQuery":
        return cls(
            question=data.get("question", ""),
            actual=data.get("actual"),
            category=data.get("category"),
        )


# ---------------------------------------------------------------------------
# Query history
# ---------------------------------------------------------------------------

@dataclass
class HistoryEntry:
    id: Optional[str]
    user_id: str
    question: str
    raw_value: Optional[float]
    verified_value: Optional[float]
    trust: str
    display_value: Optional[str]
    correction_log: list
    timestamp: Optional[str]

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            question=data.get("question", ""),
            raw_value=data.get("raw_value"),
            verified_value=data.get("verified_value"),
            trust=data.get("trust", "HIGH"),
            display_value=data.get("display_value"),
            correction_log=data.get("correction_log", []),
            timestamp=data.get("timestamp"),
        )


__all__ = [
    "CorrectionEntry",
    "VerifyResult",
    "BatchVerifyResult",
    "HealthStatus",
    "FundamentalsResult",
    "EarningsReport",
    "FCGVerifyResult",
    "NormalizeResult",
    "Constraint",
    "SampleQuery",
    "HistoryEntry",
]
