from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verification.eligibility import evidence_package as ep


def candidate(data: bytes, **updates):
    base = {
        "candidate_id": "fvq2_test", "source_id": "S1",
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "relative_path": "data/verification/sources/x.html", "source_format": "html",
        "source_locator": "block/0", "raw_source_span": "Revenue was 10 million.",
        "target_raw_text": "10", "target_start": 12, "target_end": 14,
        "parser_metadata": {"segment_index": 0, "structural_kind": "prose"},
    }
    base.update(updates)
    return base


def write_source(tmp_path: Path, data: bytes) -> Path:
    path = tmp_path / "data/verification/sources/x.html"
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    return path


def test_successful_reconstruction(tmp_path):
    data = b"<p>Revenue was 10 million.</p>"
    write_source(tmp_path, data)
    item = ep.reconstruct_evidence(candidate(data), tmp_path)
    assert item.evidence_text == "Revenue was 10 million."
    assert item.target_raw_text == "10"
    assert item.issuer is None and item.reporting_event is None
    assert item.dependency_log == ()


def test_source_sha_mismatch(tmp_path):
    data = b"<p>Revenue was 10 million.</p>"
    write_source(tmp_path, data)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        ep.reconstruct_evidence(candidate(data, source_sha256="0" * 64), tmp_path)


def test_missing_locator(tmp_path):
    data = b"<p>Revenue was 10 million.</p>"
    write_source(tmp_path, data)
    with pytest.raises(ValueError, match="exactly once"):
        ep.reconstruct_evidence(candidate(data, source_locator="block/99"), tmp_path)


def test_duplicate_locator_fails_closed(tmp_path, monkeypatch):
    data = b"x"; write_source(tmp_path, data)
    block = ep.StructuralBlock("Revenue was 10 million.", "block/0", "prose", {})
    monkeypatch.setattr(ep, "_parse", lambda fmt, raw: [block, block])
    with pytest.raises(ValueError, match="exactly once"):
        ep.reconstruct_evidence(candidate(data), tmp_path)


def test_raw_span_mismatch(tmp_path):
    data = b"<p>Revenue was 10 million.</p>"; write_source(tmp_path, data)
    with pytest.raises(ValueError, match="not contained"):
        ep.reconstruct_evidence(candidate(data, raw_source_span="Revenue was 10 billion."), tmp_path)


def test_target_offset_text_mismatch(tmp_path):
    data = b"<p>Revenue was 10 million.</p>"; write_source(tmp_path, data)
    with pytest.raises(ValueError, match="target offset/text mismatch"):
        ep.reconstruct_evidence(candidate(data, target_start=0, target_end=2), tmp_path)
