"""Deterministic numeric parsing primitives shared across the backend.

Kept as a standalone top-level package (not nested under `core`) so that
importing it from app/dvl.py cannot trigger core/__init__.py's import
graph, which itself imports back into app.dvl -- see canonicalizer.py's
module docstring for the full explanation.
"""

from .canonicalizer import (
    CanonicalizationError,
    CanonicalNumber,
    RejectReason,
    Unit,
    canonicalize,
)

__all__ = [
    "CanonicalNumber",
    "CanonicalizationError",
    "RejectReason",
    "Unit",
    "canonicalize",
]
