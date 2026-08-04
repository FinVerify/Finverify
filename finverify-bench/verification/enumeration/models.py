"""Common structural and raw-candidate representations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


ENUMERATION_SCHEMA_VERSION = "fvq1-raw-v1"


@dataclass(frozen=True)
class SourceArtifact:
    source_id: str
    relative_path: str
    source_format: str
    sha256: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructuralBlock:
    text: str
    locator: str
    kind: str = "prose"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParseIssue:
    source_id: str
    locator: str
    issue_type: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NumericTarget:
    start: int
    end: int
    raw_text: str
    numeric_kind: str
    normalized_value: float
    normalized_unit: str
    scale: float
    parser_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawCandidate:
    candidate_id: str
    source_id: str
    source_sha256: str
    relative_path: str
    source_format: str
    source_locator: str
    raw_source_span: str
    target_raw_text: str
    target_start: int
    target_end: int
    numeric_kind: str
    normalized_value: float
    normalized_unit: str
    scale: float
    parser_metadata: Dict[str, Any] = field(default_factory=dict)
    enumeration_status: str = "ENUMERATED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
