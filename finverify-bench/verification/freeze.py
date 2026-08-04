"""Dataset freeze manifests and read-only SHA-256 hashing."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional, Union

from .schema import SCHEMA_VERSION, VerificationPair


def sha256_file(path: Union[str, Path]) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_freeze_manifest(
    files: Iterable[Union[str, Path]],
    *,
    verifier_commit: str = "f1ff63e06c0751218dfbcf2071cbb434aa8fa873",
    protocol_reference: str = "PROTOCOL.md",
    spec_reference: str = "EXPERIMENT_SPEC_v1.md",
    seed: Optional[int] = None,
    split_manifest: Optional[Dict[str, object]] = None,
    creation_command: Optional[str] = None,
) -> Dict[str, object]:
    records = []
    for raw_path in files:
        path = Path(raw_path)
        records.append({"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return {
        "schema_version": SCHEMA_VERSION,
        "creation_command": creation_command,
        "seed": seed,
        "verifier_freeze_commit": verifier_commit,
        "protocol_reference": protocol_reference,
        "spec_reference": spec_reference,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": records,
        "split": split_manifest,
    }


def write_freeze_manifest(path: Union[str, Path], manifest: Dict[str, object], *, overwrite: bool = False) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError("refusing to overwrite existing freeze manifest: %s" % target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
