"""Blinded annotation export/import with immutable raw responses."""

from __future__ import annotations

import csv
import random
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .schema import Annotation, PairLabel, VerificationPair


ANNOTATION_REASONS = (
    "ENTITY", "CONCEPT", "PERIOD", "SCOPE", "ACCOUNTING_BASIS",
    "TEMPORAL_FRAME", "VALUE_ROLE", "VALUE", "PROVENANCE", "OTHER", "NONE",
)


def export_annotation_rows(
    pairs: Sequence[VerificationPair], *, seed: int = 20260805, batch_size: int = 10
) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
    indexed = [
        ("ann_%06d" % (index + 1), pair)
        for index, pair in enumerate(pairs)
    ]
    random.Random(seed).shuffle(indexed)
    rows = [
        {
            "annotation_item_id": item_id,
            "claim_text": pair.claim.text,
            "evidence_text": pair.evidence.text,
            "allowed_decisions": "SUPPORT|REJECT|INSUFFICIENT",
            "allowed_reasons": "|".join(ANNOTATION_REASONS),
            "batch_id": "batch_%04d" % ((index // batch_size) + 1),
        }
        for index, (item_id, pair) in enumerate(indexed)
    ]
    mapping = {item_id: pair.id for item_id, pair in indexed}
    return rows, mapping


def write_annotation_csv(path: Union[str, Path], rows: Sequence[Dict[str, str]], *, overwrite: bool = False) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError("refusing to overwrite annotation export: %s" % target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fields = ["annotation_item_id", "claim_text", "evidence_text", "allowed_decisions", "allowed_reasons", "batch_id"]
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def import_annotations(
    path: Union[str, Path],
    *,
    item_ids: Iterable[str],
    raw_output: Optional[Union[str, Path]] = None,
) -> List[Annotation]:
    allowed_ids = set(item_ids)
    annotations: List[Annotation] = []
    seen = set()
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            item_id = row.get("annotation_item_id", "").strip()
            annotator = row.get("annotator_id", row.get("annotator_id_anonymized", "")).strip()
            decision = row.get("decision", "").strip().upper()
            reasons = [value.strip().upper() for value in row.get("reason_fields", "").split("|") if value.strip()]
            key = (item_id, annotator)
            if item_id not in allowed_ids:
                raise ValueError("row %d: unknown annotation item %s" % (row_number, item_id))
            if key in seen:
                raise ValueError("row %d: duplicate response for annotator/item" % row_number)
            if decision not in {label.value for label in PairLabel}:
                raise ValueError("row %d: invalid decision %s" % (row_number, decision))
            invalid_reasons = set(reasons) - set(ANNOTATION_REASONS)
            if invalid_reasons:
                raise ValueError("row %d: invalid reasons %s" % (row_number, sorted(invalid_reasons)))
            seen.add(key)
            annotations.append(Annotation(
                annotation_id=row.get("annotation_id", "raw_%06d" % row_number),
                example_id=item_id,
                annotator_id=annotator,
                decision=PairLabel(decision),
                reason_fields=reasons,
                timestamp=row.get("timestamp") or None,
                batch_id=row.get("batch_id") or None,
                comments=row.get("comments") or None,
            ))
    if raw_output is not None:
        target = Path(raw_output)
        if target.exists():
            raise FileExistsError("refusing to overwrite raw annotations: %s" % target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(__import__("json").dumps(item.to_dict(), sort_keys=True) for item in annotations) + "\n", encoding="utf-8")
    return annotations
