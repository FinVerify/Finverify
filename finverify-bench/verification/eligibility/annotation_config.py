"""Amendment 2 / Implementation Spec Section 8A.1: locked ensemble configuration.

Builds and validates ``annotation_config.lock.json`` — the single frozen
artifact that fixes, before any Run-2 occurrence is processed: model
identities, the verbatim prompt, decoding settings, output schema,
aggregation rule, and failure handling. Nothing here executes an
annotation; it only constructs and hashes the immutable configuration.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .serialization import json_bytes

# Verbatim from ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md Section 6. Must not be
# paraphrased in any annotator prompt or human-audit interface.
RUBRIC_QUESTION = (
    "Does this explicitly enumerated occurrence represent an eligible "
    "quantitative financial fact, with sufficient permitted source context "
    "to resolve the relevant identity and evidence, without researcher-"
    "derived arithmetic?"
)

RUBRIC_CHECKLIST = (
    "explicit presence of the value",
    "financial versus purely operational scope",
    "Entity, Concept, and materially required Period",
    "recoverable Scope, Accounting Basis, Temporal Frame, and Value Role",
    "evidence sufficiency",
    "absence of researcher-derived meaning",
)

# Section 7 evidence-package boundary, referenced (not duplicated in prose)
# so the config artifact records exactly which boundary version it commits to.
EVIDENCE_BOUNDARY_REF = "ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md#7"

CONFIG_VERSION = "annotation_config_v1"
MIN_ANNOTATORS = 3


@dataclass(frozen=True)
class AnnotatorSpec:
    annotator_id: str
    model_family: str
    model_version: str
    prompt: str

    def __post_init__(self) -> None:
        if not self.annotator_id or not self.model_family or not self.model_version:
            raise ValueError("annotator_id, model_family, and model_version are required")
        if RUBRIC_QUESTION not in self.prompt:
            raise ValueError("annotator prompt must reproduce the Section 6 rubric question verbatim")
        for item in RUBRIC_CHECKLIST:
            if item not in self.prompt:
                raise ValueError("annotator prompt is missing a Section 6 checklist item: %r" % (item,))


@dataclass(frozen=True)
class DecodingSettings:
    temperature: float
    top_p: float
    max_tokens: int

    def __post_init__(self) -> None:
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("temperature out of range")
        if not (0.0 < self.top_p <= 1.0):
            raise ValueError("top_p out of range")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")


@dataclass(frozen=True)
class FailureHandling:
    timeout_seconds: int
    retry_count: int
    fallback_status: str = "ADJUDICATION_REQUIRED"

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.retry_count < 0:
            raise ValueError("invalid failure-handling settings")
        if self.fallback_status != "ADJUDICATION_REQUIRED":
            # Amendment 2 Section 3(6) / Spec 8A.2: a failure is never
            # defaulted to either substantive label.
            raise ValueError("failure fallback must be ADJUDICATION_REQUIRED, never a substantive label")


@dataclass(frozen=True)
class AnnotationConfig:
    annotators: Tuple[AnnotatorSpec, ...]
    decoding: DecodingSettings
    failure_handling: FailureHandling
    evaluation_model_families: Tuple[str, ...]
    config_version: str = CONFIG_VERSION
    implementation_commit: str = "UNRECORDED"

    def __post_init__(self) -> None:
        if len(self.annotators) < MIN_ANNOTATORS:
            raise ValueError("at least %d disjoint-family annotators are required (k >= 3)" % MIN_ANNOTATORS)
        ids = [a.annotator_id for a in self.annotators]
        if len(set(ids)) != len(ids):
            raise ValueError("annotator_id values must be unique")
        annotation_families = {a.model_family for a in self.annotators}
        if len(annotation_families) != len(self.annotators):
            raise ValueError("annotation ensemble model families must themselves be pairwise distinct")
        overlap = annotation_families & set(self.evaluation_model_families)
        if overlap:
            raise ValueError(
                "annotation ensemble is not disjoint from the evaluation/baseline roster at "
                "model-family granularity: %s" % sorted(overlap)
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_version": self.config_version,
            "implementation_commit": self.implementation_commit,
            "annotators": [
                {
                    "annotator_id": a.annotator_id,
                    "model_family": a.model_family,
                    "model_version": a.model_version,
                    "prompt": a.prompt,
                }
                for a in self.annotators
            ],
            "decoding": {
                "temperature": self.decoding.temperature,
                "top_p": self.decoding.top_p,
                "max_tokens": self.decoding.max_tokens,
            },
            "failure_handling": {
                "timeout_seconds": self.failure_handling.timeout_seconds,
                "retry_count": self.failure_handling.retry_count,
                "fallback_status": self.failure_handling.fallback_status,
            },
            "evaluation_model_families": sorted(self.evaluation_model_families),
            "aggregation_rule": "k_of_k_or_kminus1_of_k_else_split",
            "rubric_question": RUBRIC_QUESTION,
            "rubric_checklist": list(RUBRIC_CHECKLIST),
            "evidence_boundary_ref": EVIDENCE_BOUNDARY_REF,
        }

    def lock_bytes(self) -> bytes:
        return json_bytes(self.to_dict())

    def lock_sha256(self) -> str:
        return hashlib.sha256(self.lock_bytes()).hexdigest()


def build_prompt(model_role: str) -> str:
    """Assemble a verbatim-compliant annotator prompt.

    Convenience builder for callers constructing ``AnnotatorSpec`` instances;
    it reproduces the frozen rubric text unmodified and appends only
    non-substantive framing (annotator role label).
    """
    lines = [
        "You are annotator role: %s." % model_role,
        RUBRIC_QUESTION,
        "Check each of the following:",
    ]
    lines.extend("- " + item for item in RUBRIC_CHECKLIST)
    lines.append("Evidence boundary: %s (Section 7 package only; no other context).")
    return "\n".join(lines)


def validate_disjointness(annotation_families: List[str], evaluation_families: List[str]) -> None:
    """Amendment 2 Section 4: disjointness at model-family granularity.

    Raises ValueError if any family appears in both rosters. Both rosters
    must be fixed and published before either run begins; this function only
    checks the invariant, it does not adjust either roster.
    """
    overlap = set(annotation_families) & set(evaluation_families)
    if overlap:
        raise ValueError("model-family overlap between annotation ensemble and evaluation roster: %s" % sorted(overlap))
