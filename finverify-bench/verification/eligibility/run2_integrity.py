"""Shared frozen production-ledger input-integrity checks.

Minimal blocker repair only — this module adds no new scientific policy. It
binds the I4 annotation/audit production entry points to the same frozen
production-ledger contract that ``verification.eligibility.engine.load_raw_ledger``
already enforces (Run-3, as of the 9C-R3 migration), instead of letting each I4 script trust an
independently supplied path/hash/candidate list.

Single source of truth: the frozen ``RUN2_*``/``RUN3_*`` constants live only in
``engine.py``. This module always reads them from the ``engine`` module
object at call time (never copies them into a local constant) so that the
existing test convention of ``monkeypatch.setattr(eligibility_engine,
"RUN2_SHA256", ...)`` continues to work unchanged for these checks too.

Fail-closed: every function here raises ``IntegrityViolation`` (a
``ValueError``) on any mismatch. None of these functions accept a
production-side override/bypass parameter. The only way to exercise this
code with synthetic data is the same mechanism ``engine.load_raw_ledger``
already relies on: a path that does not end in the frozen Run-3 relative
path is never subject to the frozen-hash/count checks at all, exactly like
the existing ``tests/test_eligibility.py`` fixtures do. There is no
separate "test mode" flag.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from . import engine as eligibility_engine
from .engine import load_raw_ledger


class IntegrityViolation(ValueError):
    """A frozen-input integrity check failed. Always fail closed on this."""


@dataclass(frozen=True)
class ValidatedRawLedger:
    records: Tuple[Dict[str, Any], ...]
    sha256: str
    candidate_ids: Tuple[str, ...]  # canonical order: ascending, exactly as in the ledger's own de-dup check


def validate_and_load_raw_ledger(
    path: Path,
    *,
    allow_production: bool = False,
    freeze_metadata_path: Optional[Path] = None,
    implementation_commit: Optional[str] = None,
) -> ValidatedRawLedger:
    """Load the raw ledger through the same gate Phase 9C-G already trusts.

    Delegates every default-deny/hash/count/duplicate-candidate check to
    ``engine.load_raw_ledger`` (the existing frozen contract) rather than
    reimplementing it. The only addition here is packaging the result with
    its own independently-recomputed SHA-256 and the canonical candidate-ID
    set, for the I4 scripts to bind against.
    """
    path = Path(path)
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    records = load_raw_ledger(
        path,
        allow_production=allow_production,
        freeze_metadata_path=freeze_metadata_path,
        implementation_commit=implementation_commit,
    )
    candidate_ids = tuple(sorted(record["candidate_id"] for record in records))
    if len(set(candidate_ids)) != len(candidate_ids):
        # Defensive only: engine.load_raw_ledger already rejects duplicates
        # while parsing, so this should be unreachable.
        raise IntegrityViolation("duplicate candidate_id survived raw-ledger validation")
    return ValidatedRawLedger(records=tuple(records), sha256=digest, candidate_ids=candidate_ids)


def validate_exact_candidate_universe(supplied_ids: Iterable[str], canonical_ids: Sequence[str], *, context: str) -> None:
    """Fail closed unless ``supplied_ids`` is exactly ``canonical_ids`` as a set, with no duplicates.

    ``context`` is a short label (e.g. "annotation votes", "annotation
    ledger") used only in the error message, so a single shared function can
    serve every call site listed in the Phase 9C-I4-R1 blocker report.
    """
    supplied_list = list(supplied_ids)
    supplied_set = set(supplied_list)
    if len(supplied_set) != len(supplied_list):
        seen = set()
        dupes = sorted({cid for cid in supplied_list if cid in seen or seen.add(cid)})
        raise IntegrityViolation("%s: duplicate candidate_id(s): %s" % (context, dupes[:5]))
    canonical_set = set(canonical_ids)
    missing = sorted(canonical_set - supplied_set)
    extra = sorted(supplied_set - canonical_set)
    if missing:
        raise IntegrityViolation("%s: missing %d canonical candidate_id(s), e.g. %s" % (context, len(missing), missing[:5]))
    if extra:
        raise IntegrityViolation("%s: %d candidate_id(s) not in the canonical universe, e.g. %s" % (context, len(extra), extra[:5]))


def validate_provenance_hash(label: str, actual: str, expected: str) -> None:
    """Fail closed unless two hex digests are byte-identical. No fuzzy/prefix matching."""
    if actual != expected:
        raise IntegrityViolation("%s provenance mismatch: artifact was produced against a different %s" % (label, label))


PROVENANCE_PREFIX = "# "


def provenance_header_lines(fields: Mapping[str, str]) -> List[str]:
    """Deterministic ``# key=value`` header lines, one per field, insertion order preserved."""
    return [PROVENANCE_PREFIX + "%s=%s" % (key, value) for key, value in fields.items()]


def parse_provenance_header(lines: Iterable[str]) -> Dict[str, str]:
    """Parse leading ``# key=value`` lines into a dict; stops at the first non-comment line."""
    result: Dict[str, str] = {}
    for line in lines:
        if not line.startswith(PROVENANCE_PREFIX):
            break
        body = line[len(PROVENANCE_PREFIX):].rstrip("\n")
        if "=" not in body:
            break
        key, _, value = body.partition("=")
        result[key] = value
    return result
