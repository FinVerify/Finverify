"""Deterministic artifact hashing and write-once ledger plumbing.

This module deliberately does not resolve or populate model/dataset hashes.
Those values belong to the pre-execution provenance lock and require the
separately logged acquisition step.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Literal, Mapping


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def jsonl_bytes(records: Iterable[Mapping[str, object]]) -> bytes:
    return b"".join(canonical_json_bytes(record) for record in records)


def write_once(path: str | Path, data: bytes) -> str:
    """Write an artifact only when absent; return its SHA-256."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = target.read_bytes()
        if existing != data:
            raise FileExistsError(f"refusing to overwrite immutable artifact: {target}")
        return sha256_bytes(existing)
    target.write_bytes(data)
    return sha256_bytes(data)


def artifact_paths(root: str | Path, dataset: str) -> dict[str, Path]:
    base = Path(root)
    return {
        "raw": base / f"{dataset}_dev_raw_ledger.jsonl",
        "gold": base / f"{dataset}_dev_gold.jsonl",
        "intervention": base / f"{dataset}_dev_intervention_ledger.jsonl",
        "hashes": base / f"{dataset}_dev_hashes.json",
    }


def assert_lock_ready(lock_path: str | Path, *, dataset: Literal["finqa", "tatqa"]) -> None:
    """Validate shared gates plus provenance for the executing dataset."""
    if dataset not in ("finqa", "tatqa"):
        raise ValueError(f"unsupported execution dataset: {dataset}")
    target = Path(lock_path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    missing: list[str] = []

    def require(path: str, value: object) -> None:
        if value is None or value == "" or (isinstance(value, str) and value.startswith("<")):
            missing.append(path)

    if payload.get("metadata", {}).get("frozen") is not True:
        missing.append("metadata.frozen")
    protocol = payload.get("protocol", {})
    require("protocol.file", protocol.get("file"))
    require("protocol.sha256", protocol.get("sha256"))
    protocol_path = target.parent / str(protocol.get("file", ""))
    if protocol_path.is_file() and sha256_file(protocol_path).lower() != str(protocol.get("sha256", "")).lower():
        raise RuntimeError("protocol SHA-256 does not match the provenance lock")

    required = {
        dataset: ("repository", "revision", "dev_file", "sha256", "raw_examples", "eligible_examples"),
        "model": ("base_model", "revision", "tokenizer_revision"),
        "adapter": ("repository", "revision"),
        "implementation": ("branch", "commit", "codex_completed", "implementation_sha256"),
    }
    for section, fields in required.items():
        values = payload.get(section, {})
        for field in fields:
            require(f"{section}.{field}", values.get(field))
    if payload.get("implementation", {}).get("codex_completed") is not True:
        missing.append("implementation.codex_completed")
    for field in ("python", "torch", "transformers", "peft", "bitsandbytes", "cuda", "gpu", "platform", "operating_system"):
        require(f"environment.{field}", payload.get("environment", {}).get(field))

    digest = str(payload.get(dataset, {}).get("sha256", ""))
    if digest and (len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest)):
        raise RuntimeError(f"{dataset}.sha256 is not a SHA-256 digest")
    implementation_digest = str(payload.get("implementation", {}).get("implementation_sha256", ""))
    if implementation_digest and (len(implementation_digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in implementation_digest)):
        raise RuntimeError("implementation.implementation_sha256 is not a SHA-256 digest")
    execution = payload.get("execution", {})
    if execution.get("status") != "PRE_EXECUTION":
        raise RuntimeError("provenance lock execution.status must be PRE_EXECUTION before ledger generation")
    if execution.get("raw_ledger_generated") is not False:
        raise RuntimeError("provenance lock raw_ledger_generated must be false before ledger generation")
    if missing:
        raise RuntimeError("incomplete pre-execution provenance lock: " + ", ".join(missing))
