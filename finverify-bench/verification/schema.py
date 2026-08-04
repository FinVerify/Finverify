"""Serializable schema for the FinVerifyBench-Verify track.

The schema stores gold identity metadata for later oracle-vs-extracted work,
but does not encode a system prediction or expected gate outcome.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "verify-v1"


class _ValueEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class PairLabel(_ValueEnum):
    SUPPORT = "SUPPORT"
    REJECT = "REJECT"
    INSUFFICIENT = "INSUFFICIENT"


class PairType(_ValueEnum):
    NATURAL = "natural"
    MATCHED_CONTROL = "matched_control"
    CONTROLLED_PERTURBATION = "controlled_perturbation"


class ShiftDimension(_ValueEnum):
    ENTITY = "entity"
    CONCEPT = "concept"
    PERIOD = "period"
    SCOPE = "scope"
    ACCOUNTING_BASIS = "accounting_basis"
    TEMPORAL_FRAME = "temporal_frame"
    VALUE_ROLE = "value_role"


IDENTITY_FIELDS = (
    "entity",
    "concept",
    "period",
    "scope",
    "accounting_basis",
    "temporal_frame",
    "value_role",
)
ALLOWED_SPLITS = {None, "dev", "test"}
ALLOWED_BASIS = {None, "GAAP", "non_GAAP", "unknown"}
ALLOWED_SCOPE = {None, "company", "segment", "unknown"}
ALLOWED_FRAME = {None, "actual", "guidance", "unknown"}
ALLOWED_ROLE = {None, "current", "comparison", "unknown"}


@dataclass
class ClaimEvidence:
    text: str
    value: float
    entity: Optional[str] = None
    concept: Optional[str] = None
    period: Optional[str] = None
    accounting_basis: Optional[str] = None
    scope: Optional[str] = None
    temporal_frame: Optional[str] = None
    value_role: Optional[str] = None

    def identity(self) -> Dict[str, Any]:
        return {name: getattr(self, name) for name in IDENTITY_FIELDS}


@dataclass
class SourceProvenance:
    document_id: str
    document_hash: str
    source_claim_id: str
    ticker: Optional[str] = None
    document_type: Optional[str] = None
    uri: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class VerificationPair:
    id: str
    source_group_id: str
    claim: ClaimEvidence
    evidence: ClaimEvidence
    label: PairLabel
    pair_type: PairType
    source: SourceProvenance
    split: Optional[str] = None
    shift_dimension: Optional[ShiftDimension] = None
    parent_pair_id: Optional[str] = None
    mutation_side: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["label"] = self.label.value
        data["pair_type"] = self.pair_type.value
        data["shift_dimension"] = self.shift_dimension.value if self.shift_dimension else None
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationPair":
        claim = ClaimEvidence(**data["claim"])
        evidence = ClaimEvidence(**data["evidence"])
        source = SourceProvenance(**data["source"])
        return cls(
            id=data["id"],
            source_group_id=data["source_group_id"],
            claim=claim,
            evidence=evidence,
            label=PairLabel(data["label"]),
            pair_type=PairType(data["pair_type"]),
            source=source,
            split=data.get("split"),
            shift_dimension=ShiftDimension(data["shift_dimension"]) if data.get("shift_dimension") else None,
            parent_pair_id=data.get("parent_pair_id"),
            mutation_side=data.get("mutation_side"),
            metadata=dict(data.get("metadata") or {}),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )


@dataclass
class Annotation:
    annotation_id: str
    example_id: str
    annotator_id: str
    decision: PairLabel
    reason_fields: List[str] = field(default_factory=list)
    timestamp: Optional[str] = None
    batch_id: Optional[str] = None
    comments: Optional[str] = None
    validity_status: str = "valid"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.value
        return data


def pairs_to_jsonl(pairs: List[VerificationPair]) -> str:
    return "\n".join(pair.to_json() for pair in pairs) + ("\n" if pairs else "")


def pairs_from_jsonl(text: str) -> List[VerificationPair]:
    return [VerificationPair.from_dict(json.loads(line)) for line in text.splitlines() if line.strip()]


def validate_pair_shape(pair: VerificationPair) -> List[str]:
    """Validate local schema/category rules; cross-pair checks live in validators."""
    errors: List[str] = []
    if pair.schema_version != SCHEMA_VERSION:
        errors.append("unsupported schema_version: %r" % pair.schema_version)
    for field_name, value in (("id", pair.id), ("source_group_id", pair.source_group_id)):
        if not isinstance(value, str) or not value.strip():
            errors.append("%s is required" % field_name)
    for side, record in (("claim", pair.claim), ("evidence", pair.evidence)):
        if not isinstance(record.text, str) or not record.text.strip():
            errors.append("%s.text is required" % side)
        if isinstance(record.value, bool) or not isinstance(record.value, (int, float)) or not math.isfinite(record.value):
            errors.append("%s.value must be a finite number" % side)
        if record.accounting_basis not in ALLOWED_BASIS:
            errors.append("invalid %s.accounting_basis" % side)
        if record.scope not in ALLOWED_SCOPE:
            errors.append("invalid %s.scope" % side)
        if record.temporal_frame not in ALLOWED_FRAME:
            errors.append("invalid %s.temporal_frame" % side)
        if record.value_role not in ALLOWED_ROLE:
            errors.append("invalid %s.value_role" % side)
    if pair.split not in ALLOWED_SPLITS:
        errors.append("split must be null, dev, or test")
    if pair.pair_type == PairType.CONTROLLED_PERTURBATION:
        if pair.shift_dimension is None:
            errors.append("controlled perturbation requires shift_dimension")
        if not pair.parent_pair_id:
            errors.append("controlled perturbation requires parent_pair_id")
        if pair.mutation_side not in {"claim", "evidence"}:
            errors.append("controlled perturbation requires mutation_side claim/evidence")
    elif pair.shift_dimension is not None:
        errors.append("shift_dimension is only valid for controlled perturbations")
    if not pair.source.document_id or not pair.source.document_hash or not pair.source.source_claim_id:
        errors.append("source document_id, document_hash, and source_claim_id are required")
    return errors
