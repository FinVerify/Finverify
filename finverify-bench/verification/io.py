"""Small JSONL I/O helpers for verification-track files."""

import json
from pathlib import Path
from typing import Iterable, List

from .schema import VerificationPair, pairs_from_jsonl, pairs_to_jsonl


def read_pairs(path: str) -> List[VerificationPair]:
    return pairs_from_jsonl(Path(path).read_text(encoding="utf-8"))


def write_pairs(path: str, pairs: Iterable[VerificationPair], *, overwrite: bool = False) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError("refusing to overwrite existing dataset: %s" % target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(pairs_to_jsonl(list(pairs)), encoding="utf-8")
