"""Deterministic JSON/JSONL and freeze-manifest serialization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def jsonl_bytes(records: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(json_bytes(record) for record in records)


def write_new(path: Path, data: bytes) -> str:
    if path.exists():
        raise FileExistsError("frozen output already exists: %s" % path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
