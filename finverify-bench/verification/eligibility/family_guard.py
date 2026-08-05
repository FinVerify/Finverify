"""Amendment 2 Section 4: annotation/evaluation model-family disjointness guard.

Kept separate from ``annotation_config`` so the same guard can be reapplied
later, when an evaluation/baseline roster is proposed or extended, without
re-touching the frozen annotation configuration. Per Section 4: "If a family
is later wanted for both roles, the evaluation design is amended first; the
annotation ensemble is never adjusted to preserve a previously-chosen
evaluation roster."
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable


class FamilyDisjointnessViolation(ValueError):
    """Raised when the annotation and evaluation rosters share a model family."""


@dataclass(frozen=True)
class FrozenRosters:
    """Both rosters, fixed and published before either run begins."""

    annotation_families: FrozenSet[str]
    evaluation_families: FrozenSet[str]

    def __post_init__(self) -> None:
        if not self.annotation_families:
            raise ValueError("annotation roster must be non-empty")
        overlap = self.annotation_families & self.evaluation_families
        if overlap:
            raise FamilyDisjointnessViolation(
                "model family used in both annotation and evaluation rosters: %s" % sorted(overlap)
            )


def freeze_rosters(annotation_families: Iterable[str], evaluation_families: Iterable[str]) -> FrozenRosters:
    return FrozenRosters(frozenset(annotation_families), frozenset(evaluation_families))


def check_new_evaluation_family(rosters: FrozenRosters, candidate_family: str) -> None:
    """Guard applied when a new family is proposed for the evaluation/baseline roster.

    Never adjusts the annotation ensemble; only rejects the proposed
    evaluation-roster addition if it collides with the frozen annotation
    ensemble's families.
    """
    if candidate_family in rosters.annotation_families:
        raise FamilyDisjointnessViolation(
            "cannot add %r to the evaluation/baseline roster: already used by the frozen "
            "annotation ensemble; the annotation ensemble is never adjusted to preserve "
            "a previously-chosen evaluation roster (Amendment 2 Section 4)" % candidate_family
        )


def check_new_annotation_family(rosters: FrozenRosters, candidate_family: str) -> None:
    """Symmetric guard if a new annotator family is proposed after evaluation roster exists.

    Note: Section 3 already freezes the annotation roster before the
    annotation run begins ("No element ... may be modified after the
    annotation run begins"); this guard exists for the pre-freeze design
    stage only, where the evaluation roster was fixed first.
    """
    if candidate_family in rosters.evaluation_families:
        raise FamilyDisjointnessViolation(
            "cannot add %r to the annotation ensemble: already used by the frozen "
            "evaluation/baseline roster" % candidate_family
        )
