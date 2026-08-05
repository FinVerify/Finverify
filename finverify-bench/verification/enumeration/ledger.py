"""Manifest-backed deterministic candidate ledger construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .html_parser import parse_html
from .manifest import ManifestError, is_canonical_production_manifest, load_manifest, manifest_artifacts, resolve_artifact
from .mhtml_parser import parse_mhtml
from .models import ENUMERATION_SCHEMA_VERSION, ParseIssue, RawCandidate, SourceArtifact, StructuralBlock
from .numeric import find_targets
from .pdf_parser import parse_pdf
from .segmentation import segment_prose


SUPPORTED_FORMATS = {"html", "mhtml", "pdf"}


class EnumerationError(RuntimeError):
    pass


def candidate_id(source_id: str, source_locator: str, segment_index: int, target_start: int, target_end: int, target_raw_text: str) -> str:
    """Return the versioned identity of one enumerated quantitative occurrence.

    ``target_start``/``target_end`` are span-relative, so segment identity is
    mandatory.  There is deliberately no default: callers must supply it.
    """
    if not isinstance(segment_index, int) or segment_index < 0:
        raise EnumerationError("segment_index must be an explicit non-negative integer")
    payload = "\n".join((
        ENUMERATION_SCHEMA_VERSION, source_id, source_locator, str(segment_index),
        str(target_start), str(target_end), target_raw_text,
    ))
    return "fvq2_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_blocks(artifact: SourceArtifact, data: bytes) -> Tuple[List[StructuralBlock], List[ParseIssue]]:
    if artifact.source_format == "html":
        return parse_html(data), []
    if artifact.source_format == "mhtml":
        return parse_mhtml(data), []
    if artifact.source_format == "pdf":
        blocks, issues = parse_pdf(data)
        return blocks, [ParseIssue(artifact.source_id, issue.locator, issue.issue_type, issue.description) for issue in issues]
    raise EnumerationError("unsupported required source format: %s" % artifact.source_format)


def _candidate_from_target(artifact: SourceArtifact, block: StructuralBlock, span: str, segment_index: int, target) -> RawCandidate:
    metadata = dict(block.metadata)
    metadata.update({"structural_kind": block.kind})
    return RawCandidate(
        candidate_id=candidate_id(artifact.source_id, block.locator, segment_index, target.start, target.end, target.raw_text),
        source_id=artifact.source_id,
        source_sha256=artifact.sha256,
        relative_path=artifact.relative_path,
        source_format=artifact.source_format,
        source_locator=block.locator,
        raw_source_span=span,
        target_raw_text=target.raw_text,
        target_start=target.start,
        target_end=target.end,
        numeric_kind=target.numeric_kind,
        normalized_value=target.normalized_value,
        normalized_unit=target.normalized_unit,
        scale=target.scale,
        parser_metadata=metadata,
    )


def enumerate_artifact(artifact: SourceArtifact, data: bytes) -> Tuple[List[RawCandidate], List[ParseIssue]]:
    blocks, issues = _parse_blocks(artifact, data)
    candidates: List[RawCandidate] = []
    for block in blocks:
        spans = [block.text] if block.kind == "table" else segment_prose(block.text)
        for span_index, span in enumerate(spans):
            for target in find_targets(span):
                metadata = dict(block.metadata)
                metadata["segment_index"] = span_index
                candidate = _candidate_from_target(artifact, block, span, span_index, target)
                candidate = RawCandidate(**dict(candidate.__dict__, parser_metadata=metadata))
                if span[target.start:target.end] != target.raw_text:
                    raise EnumerationError("target offset invariant failed for %s" % artifact.source_id)
                candidates.append(candidate)
    return candidates, issues


def enumerate_manifest(
    manifest_path: Path,
    *,
    source_root: Optional[Path] = None,
    source_ids: Optional[List[str]] = None,
    allow_production: bool = False,
) -> Tuple[List[RawCandidate], List[ParseIssue]]:
    manifest = load_manifest(manifest_path)
    if is_canonical_production_manifest(manifest_path, manifest) and not allow_production:
        raise EnumerationError("production Phase 9B corpus enumeration is blocked before freeze")
    artifacts = manifest_artifacts(manifest)
    wanted = set(source_ids) if source_ids else None
    if wanted:
        artifacts = [artifact for artifact in artifacts if artifact.source_id in wanted]
        missing = wanted - {artifact.source_id for artifact in artifacts}
        if missing:
            raise ManifestError("unknown source IDs: %s" % sorted(missing))
    if source_root is None:
        resolved_manifest = manifest_path.resolve()
        root = resolved_manifest.parents[2] if resolved_manifest.parent.name == "verification" and resolved_manifest.parent.parent.name == "data" else resolved_manifest.parent
    else:
        root = source_root
    all_candidates: List[RawCandidate] = []
    all_issues: List[ParseIssue] = []
    for artifact in artifacts:
        if artifact.source_format not in SUPPORTED_FORMATS:
            raise EnumerationError("unsupported required source format: %s" % artifact.source_format)
        data = resolve_artifact(manifest_path, artifact, root)
        candidates, issues = enumerate_artifact(artifact, data)
        all_candidates.extend(candidates)
        all_issues.extend(issues)
    all_candidates.sort(key=lambda item: (item.source_id, item.source_locator, item.target_start, item.target_end, item.candidate_id))
    return all_candidates, all_issues


def _stable_json_line(value: Dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_candidate_ledger(path: Path, candidates: List[RawCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_stable_json_line(candidate.to_dict()) + "\n" for candidate in candidates), encoding="utf-8")


def write_issue_ledger(path: Path, issues: List[ParseIssue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_stable_json_line(issue.to_dict()) + "\n" for issue in issues), encoding="utf-8")
