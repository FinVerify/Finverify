"""Manifest identity, hash validation, and the mandatory production guard."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .models import SourceArtifact


class ManifestError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> Dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            manifest = json.load(handle)
    except FileNotFoundError as exc:
        raise ManifestError("manifest missing: %s" % path) from exc
    if not isinstance(manifest.get("artifacts"), list) or not manifest["artifacts"]:
        raise ManifestError("manifest must contain non-empty artifacts")
    return manifest


def manifest_artifacts(manifest: Dict[str, Any]) -> List[SourceArtifact]:
    artifacts: List[SourceArtifact] = []
    for entry in manifest["artifacts"]:
        try:
            artifact = SourceArtifact(
                source_id=entry["source_id"],
                relative_path=entry["relative_path"].replace("\\", "/"),
                source_format=entry["file_format"].lower(),
                sha256=entry["sha256"].lower(),
                metadata={key: value for key, value in entry.items() if key not in {"source_id", "relative_path", "file_format", "sha256"}},
            )
        except (KeyError, AttributeError) as exc:
            raise ManifestError("malformed manifest artifact") from exc
        artifacts.append(artifact)
    return artifacts


def _identity_signature(artifacts: Iterable[SourceArtifact]) -> set:
    return {(item.source_id, item.relative_path, item.sha256) for item in artifacts}


def is_canonical_production_manifest(path: Path, manifest: Dict[str, Any], *, repository_root: Optional[Path] = None) -> bool:
    """Return true for the canonical path or the exact frozen corpus identity."""
    resolved = path.resolve()
    if resolved.as_posix().endswith("/data/verification/source_manifest.json"):
        return True
    root = repository_root or Path(__file__).resolve().parents[2]
    canonical_path = root / "data" / "verification" / "source_manifest.json"
    if not canonical_path.exists() or resolved == canonical_path.resolve():
        return resolved == canonical_path.resolve()
    try:
        canonical = manifest_artifacts(load_manifest(canonical_path))
        candidate = manifest_artifacts(manifest)
    except ManifestError:
        return False
    return _identity_signature(candidate) == _identity_signature(canonical)


def resolve_artifact(path: Path, artifact: SourceArtifact, source_root: Path) -> bytes:
    source_path = (source_root / artifact.relative_path).resolve()
    try:
        source_path.relative_to(source_root.resolve())
    except ValueError as exc:
        raise ManifestError("artifact path escapes source root: %s" % artifact.relative_path) from exc
    if not source_path.exists():
        raise ManifestError("source artifact missing: %s" % artifact.relative_path)
    actual = sha256_file(source_path)
    if actual != artifact.sha256:
        raise ManifestError("SHA-256 mismatch for %s: expected %s, got %s" % (artifact.source_id, artifact.sha256, actual))
    return source_path.read_bytes()
