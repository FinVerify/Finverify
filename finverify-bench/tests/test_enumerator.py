"""Synthetic-only tests for the Phase 9C-E candidate enumerator."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from verification.enumeration.ledger import EnumerationError, candidate_id, enumerate_manifest, write_candidate_ledger
from verification.enumeration.manifest import ManifestError
from verification.enumeration.numeric import find_targets


def _write_manifest(tmp_path, entries):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    artifacts = []
    for source_id, filename, file_format, data in entries:
        target = source_root / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        artifacts.append({
            "source_id": source_id,
            "relative_path": filename.replace("\\", "/"),
            "file_format": file_format,
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"manifest_version": "synthetic", "artifacts": artifacts}), encoding="utf-8")
    return manifest, source_root


def _pdf(*pages):
    objects = []
    for index, text in enumerate(pages, start=1):
        objects.append("%d 0 obj << /Type /Page >>\nstream\nBT\n(%s) Tj\nET\nendstream\nendobj" % (index, text))
    return ("%PDF-1.4\n" + "\n".join(objects)).encode("utf-8")


@pytest.mark.parametrize(
    ("text", "raw", "kind"),
    [
        ("$39.3 billion", "$39.3 billion", "currency"),
        ("$39.3B", "$39.3B", "currency"),
        ("$39,300M", "$39,300M", "currency"),
        ("12%", "12%", "percentage"),
        ("-12%", "-12%", "percentage"),
        ("50 basis points", "50 basis points", "basis_points"),
        ("50 bps", "50 bps", "basis_points"),
        ("$2.10 per diluted share", "$2.10", "per_share_numeric"),
        ("1.5x", "1.5x", "ratio"),
        ("($2.1B)", "($2.1B)", "currency"),
    ],
)
def test_frozen_numeric_grammar(text, raw, kind):
    targets = find_targets(text)
    assert len(targets) == 1
    assert targets[0].raw_text == raw
    assert targets[0].numeric_kind == kind


def test_ranges_multiple_quantities_and_no_researcher_arithmetic():
    text = "Revenue increased from $10B to $12B; the source also states 20%."
    targets = find_targets(text)
    assert [target.raw_text for target in targets] == ["$10B", "$12B", "20%"]
    assert all(target.raw_text not in {"$2B", "20"} for target in targets)


def test_malformed_grouping_and_precedence_do_not_create_nested_targets():
    assert find_targets("Malformed 12,34 and 1,2,3") == []
    targets = find_targets("One value: $39.3B")
    assert [target.raw_text for target in targets] == ["$39.3B"]
    assert targets[0].start == 11
    assert targets[0].end == 17


def test_dates_counts_and_multiple_targets_remain_raw_candidates():
    targets = find_targets("FY2025 had 12 employees, 78% growth and $3M revenue.")
    assert [target.raw_text for target in targets] == ["2025", "12", "78%", "$3M"]
    assert len({(target.start, target.end) for target in targets}) == 4
    assert len({candidate_id("S", "block/0", target.start, target.end, target.raw_text) for target in targets}) == 4


def test_html_table_provenance_and_raw_span(tmp_path):
    html = b"<html><body><h1>Fictional Results</h1><p>Revenue was $4M.</p><table><tr><th>Year</th><th>Value</th></tr><tr><td>2025</td><td>$5M</td></tr></table></body></html>"
    manifest, source_root = _write_manifest(tmp_path, [("S-HTML", "doc.html", "html", html)])
    candidates, issues = enumerate_manifest(manifest, source_root=source_root)
    assert not issues
    table = [candidate for candidate in candidates if candidate.target_raw_text == "$5M"][0]
    assert table.source_locator == "table/0/row/1/cell/1"
    assert table.raw_source_span == "$5M"
    assert table.raw_source_span[table.target_start:table.target_end] == table.target_raw_text


def test_mhtml_uses_local_primary_html_only(tmp_path):
    mhtml = b"MIME-Version: 1.0\nContent-Type: multipart/related; boundary=xyz\n\n--xyz\nContent-Type: text/html\n\n<html><body><p>Fictional sales were $7M.</p></body></html>\n--xyz\nContent-Type: image/png\n\nignored 99M\n--xyz--\n"
    manifest, source_root = _write_manifest(tmp_path, [("S-MHTML", "doc.mhtml", "mhtml", mhtml)])
    candidates, issues = enumerate_manifest(manifest, source_root=source_root)
    assert not issues
    assert [candidate.target_raw_text for candidate in candidates] == ["$7M"]


def test_pdf_page_provenance_and_multiple_values(tmp_path):
    pdf = _pdf("Fictional page one $10M and 5%.", "Fictional page two 20 bps.")
    manifest, source_root = _write_manifest(tmp_path, [("S-PDF", "doc.pdf", "pdf", pdf)])
    candidates, issues = enumerate_manifest(manifest, source_root=source_root)
    assert not issues
    assert [candidate.source_locator for candidate in candidates] == ["page/0/block/0", "page/0/block/0", "page/1/block/0"]
    assert candidates[0].parser_metadata["page_number"] == 1
    assert candidates[-1].parser_metadata["page_number"] == 2


def test_manifest_hash_success_mismatch_and_missing_artifact(tmp_path):
    manifest, source_root = _write_manifest(tmp_path, [("S-HASH", "doc.html", "html", b"<p>Fictional $8M.</p>")])
    candidates, _ = enumerate_manifest(manifest, source_root=source_root)
    assert candidates[0].source_sha256 == hashlib.sha256(b"<p>Fictional $8M.</p>").hexdigest()
    source_file = source_root / "doc.html"
    source_file.write_bytes(b"<p>tampered $9M.</p>")
    with pytest.raises(ManifestError, match="SHA-256 mismatch"):
        enumerate_manifest(manifest, source_root=source_root)
    source_file.unlink()
    with pytest.raises(ManifestError, match="missing"):
        enumerate_manifest(manifest, source_root=source_root)


def test_unsupported_format_fails(tmp_path):
    manifest, source_root = _write_manifest(tmp_path, [("S-JSON", "doc.json", "json", b"{\"value\": 1}")])
    with pytest.raises(EnumerationError, match="unsupported"):
        enumerate_manifest(manifest, source_root=source_root)


def test_candidate_id_payload_is_exact_and_deterministic():
    source = "S-1"
    locator = "block/0"
    raw = "$1M"
    payload = "fvq1-raw-v1\nS-1\nblock/0\n2\n5\n$1M".encode("utf-8")
    expected = "fvq1_" + hashlib.sha256(payload).hexdigest()
    assert candidate_id(source, locator, 2, 5, raw) == expected


def test_repeated_output_and_manifest_order_are_byte_identical(tmp_path):
    entries = [
        ("S-B", "b.html", "html", b"<p>Fictional $2M.</p>"),
        ("S-A", "a.html", "html", b"<p>Fictional $1M.</p>"),
    ]
    manifest, source_root = _write_manifest(tmp_path, entries)
    candidates_one, _ = enumerate_manifest(manifest, source_root=source_root)
    candidates_two, _ = enumerate_manifest(manifest, source_root=source_root)
    out_one = tmp_path / "one.jsonl"
    out_two = tmp_path / "two.jsonl"
    write_candidate_ledger(out_one, candidates_one)
    write_candidate_ledger(out_two, candidates_two)
    assert out_one.read_bytes() == out_two.read_bytes()
    assert hashlib.sha256(out_one.read_bytes()).digest() == hashlib.sha256(out_two.read_bytes()).digest()
    assert [candidate.source_id for candidate in candidates_one] == ["S-A", "S-B"]


def test_non_eligibility_filtering_is_not_performed(tmp_path):
    html = b"<p>Fictional page number 3, employee count 12, and year 2025.</p>"
    manifest, source_root = _write_manifest(tmp_path, [("S-RAW", "doc.html", "html", html)])
    candidates, _ = enumerate_manifest(manifest, source_root=source_root)
    assert {candidate.target_raw_text for candidate in candidates} == {"3", "12", "2025"}
    assert {candidate.enumeration_status for candidate in candidates} == {"ENUMERATED"}


def test_production_manifest_guard_refuses_before_source_access():
    canonical = ROOT / "data" / "verification" / "source_manifest.json"
    with pytest.raises(EnumerationError, match="production Phase 9B corpus enumeration is blocked"):
        enumerate_manifest(canonical)

    output = canonical.parent / "_synthetic_guard_test_should_not_exist.jsonl"
    issues = canonical.parent / "_synthetic_guard_test_should_not_exist.issues.jsonl"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "enumerate_verification_candidates.py"), "--manifest", str(canonical), "--output", str(output), "--issues", str(issues)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert not output.exists()
    assert not issues.exists()


def test_enumerator_has_no_verifier_or_model_dependency():
    package_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "verification" / "enumeration").glob("*.py"))
    assert "core.engine" not in package_text
    assert "transformers" not in package_text
    assert "torch" not in package_text
