"""Deterministic Section-7 evidence materialization for frozen raw candidates.

This module reconstructs only context exposed by the frozen enumeration
parsers.  It deliberately does not infer sentence boundaries, table semantics,
issuer/reporting-event metadata, or dependency context that the parser did not
record.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from verification.enumeration.html_parser import parse_html
from verification.enumeration.mhtml_parser import parse_mhtml
from verification.enumeration.pdf_parser import parse_pdf
from verification.enumeration.models import StructuralBlock



@dataclass(frozen=True)
class EvidencePackage:
    candidate_id: str
    evidence_type: str
    evidence_text: str
    target_raw_text: str
    target_start: int
    target_end: int
    source_id: str
    source_sha256: str
    source_format: str
    source_locator: str
    parser_metadata: Dict[str, Any]
    applicable_heading: Optional[str]
    issuer: Optional[str]
    reporting_event: Optional[str]
    structural_context: Dict[str, Any]
    dependency_log: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["dependency_log"] = list(self.dependency_log)
        return value


def _parse(source_format: str, data: bytes) -> List[StructuralBlock]:
    if source_format == "html":
        return parse_html(data)
    if source_format == "mhtml":
        return parse_mhtml(data)
    if source_format == "pdf":
        blocks, issues = parse_pdf(data)
        if issues:
            raise ValueError("deterministic PDF reconstruction produced parse issues")
        return blocks
    raise ValueError("unsupported source_format for evidence reconstruction: %r" % source_format)


@lru_cache(maxsize=64)
def _load_source_blocks(source_path: str, source_format: str, expected_sha256: str) -> tuple[str, tuple[StructuralBlock, ...]]:
    data = Path(source_path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ValueError("source SHA-256 mismatch")
    return digest, tuple(_parse(source_format, data))


def _resolve_source(repo_root: Path, relative_path: str) -> Path:
    root = Path(repo_root).resolve()
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("candidate relative_path escapes repository root") from exc
    if not path.is_file():
        raise FileNotFoundError("frozen source artifact is missing: %s" % path)
    return path


def reconstruct_evidence(candidate: Mapping[str, Any], repo_root: Path) -> EvidencePackage:
    """Reconstruct one candidate's deterministic evidence, failing closed.

    ``evidence_text`` remains the frozen enumerated span.  The containing
    StructuralBlock is retained in ``structural_context`` for auditability; it
    is not promoted to a complete sentence or semantically expanded.
    """
    required = {
        "candidate_id", "source_id", "source_sha256", "relative_path",
        "source_format", "source_locator", "raw_source_span", "target_raw_text",
        "target_start", "target_end", "parser_metadata",
    }
    missing = required - set(candidate)
    if missing:
        raise ValueError("candidate is missing required evidence fields: %s" % sorted(missing))

    source_path = _resolve_source(Path(repo_root), str(candidate["relative_path"]))
    digest, blocks = _load_source_blocks(
        str(source_path), str(candidate["source_format"]), str(candidate["source_sha256"])
    )

    matches = [b for b in blocks if b.locator == candidate["source_locator"]]
    if len(matches) != 1:
        raise ValueError("source locator must resolve exactly once for %s; got %d" %
                         (candidate["candidate_id"], len(matches)))
    block = matches[0]
    span = str(candidate["raw_source_span"])
    start = candidate["target_start"]
    end = candidate["target_end"]
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
        raise ValueError("invalid target offsets for %s" % candidate["candidate_id"])
    if span[start:end] != candidate["target_raw_text"]:
        raise ValueError("target offset/text mismatch for %s" % candidate["candidate_id"])

    # The raw ledger freezes segmented prose spans.  Tables are unsegmented in
    # enumeration; prose spans must be present verbatim in their uniquely
    # resolved deterministic block.  We do not recreate/invent segmentation.
    if block.kind == "table":
        if block.text != span:
            raise ValueError("table raw_source_span mismatch for %s" % candidate["candidate_id"])
    elif span not in block.text:
        raise ValueError("raw_source_span is not contained in reconstructed block for %s" % candidate["candidate_id"])

    frozen_meta = dict(candidate["parser_metadata"])
    block_meta = dict(block.metadata)
    for key, value in block_meta.items():
        if key in frozen_meta and frozen_meta[key] != value:
            raise ValueError("parser metadata mismatch for %s field %s" % (candidate["candidate_id"], key))

    heading = block_meta.get("heading_context")
    if heading is not None and not isinstance(heading, str):
        raise ValueError("non-string deterministic heading context")

    return EvidencePackage(
        candidate_id=str(candidate["candidate_id"]),
        evidence_type=block.kind,
        evidence_text=span,
        target_raw_text=str(candidate["target_raw_text"]),
        target_start=start,
        target_end=end,
        source_id=str(candidate["source_id"]),
        source_sha256=digest,
        source_format=str(candidate["source_format"]),
        source_locator=str(candidate["source_locator"]),
        parser_metadata=frozen_meta,
        applicable_heading=heading,
        issuer=None,
        reporting_event=None,
        structural_context={"kind": block.kind, "block_text": block.text, "block_metadata": block_meta},
        dependency_log=(),
    )


def build_evidence_packages(raw_records: Sequence[Mapping[str, Any]], repo_root: Path) -> List[EvidencePackage]:
    from .run2_integrity import validate_exact_candidate_universe
    packages = [reconstruct_evidence(record, repo_root) for record in raw_records]
    validate_exact_candidate_universe(
        [item.candidate_id for item in packages],
        sorted(str(record["candidate_id"]) for record in raw_records),
        context="Section-7 evidence packages",
    )
    return sorted(packages, key=lambda item: item.candidate_id)
