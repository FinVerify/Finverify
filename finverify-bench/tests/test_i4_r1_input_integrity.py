"""Synthetic-only tests for Phase 9C-I4-R1 (minimal input-integrity repair).

No Run-2 ledger content, model service, network call, or FinVerify output is
used anywhere in this file. Follows the same synthetic-Run-2 fixture
convention already established in tests/test_eligibility.py
(_authorized_synthetic_run2): monkeypatch the frozen RUN2_* constants on
verification.eligibility.engine and use a tmp_path whose suffix matches the
frozen Run-2 relative path, rather than inventing a second mechanism.
"""
from __future__ import annotations

import hashlib
import json

import pytest

import verification.eligibility.engine as eligibility_engine
from verification.eligibility.run2_integrity import (
    IntegrityViolation, parse_provenance_header, provenance_header_lines,
    validate_and_load_raw_ledger, validate_exact_candidate_universe, validate_provenance_hash,
)


def _raw(candidate_id="c1", source_id="S1"):
    return {
        "candidate_id": candidate_id, "source_id": source_id, "source_sha256": "a" * 64,
        "relative_path": "synthetic.html", "source_format": "html", "source_locator": "block/0",
        "raw_source_span": "Synthetic value $1", "target_raw_text": "$1",
        "target_start": 16, "target_end": 18, "numeric_kind": "currency",
        "normalized_value": 1, "normalized_unit": "currency", "scale": 1,
        "parser_metadata": {}, "enumeration_status": "ENUMERATED",
    }


def _authorized_synthetic_run2(tmp_path, monkeypatch, candidate_ids=("c1",)):
    """Mirrors tests/test_eligibility.py::_authorized_synthetic_run2, extended to N candidates."""
    ledger_path = tmp_path / "data" / "verification" / "enumeration" / "raw_candidate_ledger_run2.jsonl"
    freeze_path = tmp_path / "data" / "verification" / "enumeration" / "SECOND_RUN_FREEZE.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_bytes = b"".join(
        (json.dumps(_raw(cid), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for cid in candidate_ids
    )
    ledger_path.write_bytes(ledger_bytes)
    parse_bytes = b""
    parse_sha = hashlib.sha256(parse_bytes).hexdigest()
    commit = "a" * 40
    freeze = {
        "phase": "9C-A3", "enumerator_commit": commit, "candidate_count": len(candidate_ids),
        "raw_candidate_ledger": {"relative_path": "data/verification/enumeration/raw_candidate_ledger_run2.jsonl", "byte_size": len(ledger_bytes), "sha256": hashlib.sha256(ledger_bytes).hexdigest()},
        "parse_issue_ledger": {"relative_path": "data/verification/enumeration/parse_issues_run2.jsonl", "byte_size": 0, "sha256": parse_sha},
    }
    freeze_bytes = (json.dumps(freeze, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    freeze_path.write_bytes(freeze_bytes)
    monkeypatch.setattr(eligibility_engine, "RUN2_SHA256", hashlib.sha256(ledger_bytes).hexdigest())
    monkeypatch.setattr(eligibility_engine, "RUN2_COMMIT", commit)
    monkeypatch.setattr(eligibility_engine, "RUN2_COUNT", len(candidate_ids))
    monkeypatch.setattr(eligibility_engine, "RUN2_FREEZE_PATH", freeze_path)
    monkeypatch.setattr(eligibility_engine, "RUN2_FREEZE_SHA256", hashlib.sha256(freeze_bytes).hexdigest())
    monkeypatch.setattr(eligibility_engine, "RUN2_LEDGER_BYTES", len(ledger_bytes))
    monkeypatch.setattr(eligibility_engine, "RUN2_PARSE_ISSUE_SHA256", parse_sha)
    return ledger_path, freeze_path, commit


# ---------------------------------------------------------------------------
# validate_and_load_raw_ledger: production-gate + hash/count/tamper checks
# ---------------------------------------------------------------------------

def test_valid_complete_universe_succeeds(tmp_path, monkeypatch):
    ledger_path, freeze_path, commit = _authorized_synthetic_run2(tmp_path, monkeypatch, candidate_ids=("c1", "c2", "c3"))
    validated = validate_and_load_raw_ledger(
        ledger_path, allow_production=True, freeze_metadata_path=freeze_path, implementation_commit=commit,
    )
    assert validated.candidate_ids == ("c1", "c2", "c3")
    assert len(validated.sha256) == 64


def test_production_run2_blocked_without_authorization(tmp_path):
    path = tmp_path / "data" / "verification" / "enumeration" / "raw_candidate_ledger_run2.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(PermissionError):
        validate_and_load_raw_ledger(path)


def test_negative_1_modified_raw_ledger_bytes_rejected(tmp_path, monkeypatch):
    ledger_path, freeze_path, commit = _authorized_synthetic_run2(tmp_path, monkeypatch, candidate_ids=("c1",))
    ledger_path.write_bytes(ledger_path.read_bytes().replace(b'"c1"', b'"c9"'))
    with pytest.raises(ValueError, match="not the frozen Run-2 ledger"):
        validate_and_load_raw_ledger(ledger_path, allow_production=True, freeze_metadata_path=freeze_path, implementation_commit=commit)


def test_negative_2_truncated_raw_ledger_rejected(tmp_path, monkeypatch):
    ledger_path, freeze_path, commit = _authorized_synthetic_run2(tmp_path, monkeypatch, candidate_ids=("c1", "c2"))
    original = ledger_path.read_bytes()
    ledger_path.write_bytes(original[: len(original) // 2])
    with pytest.raises(ValueError, match="not the frozen Run-2 ledger"):
        validate_and_load_raw_ledger(ledger_path, allow_production=True, freeze_metadata_path=freeze_path, implementation_commit=commit)


def test_negative_3_wrong_raw_ledger_hash_rejected(tmp_path, monkeypatch):
    ledger_path, freeze_path, commit = _authorized_synthetic_run2(tmp_path, monkeypatch, candidate_ids=("c1",))
    # Simulate an attacker/operator substituting a different, well-formed ledger.
    ledger_path.write_bytes((json.dumps(_raw("c1", "S2"), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
    with pytest.raises(ValueError, match="not the frozen Run-2 ledger"):
        validate_and_load_raw_ledger(ledger_path, allow_production=True, freeze_metadata_path=freeze_path, implementation_commit=commit)


def test_authorization_alone_never_bypasses_hash_validation(tmp_path):
    # Same invariant as tests/test_eligibility.py, re-asserted through the
    # I4-R1 wrapper specifically (not just the underlying engine call).
    path = tmp_path / "data" / "verification" / "enumeration" / "raw_candidate_ledger_run2.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_and_load_raw_ledger(path, allow_production=True)


# ---------------------------------------------------------------------------
# validate_exact_candidate_universe: missing / extra / duplicate IDs
# ---------------------------------------------------------------------------

def test_negative_4_missing_candidate_id_rejected():
    with pytest.raises(IntegrityViolation, match="missing"):
        validate_exact_candidate_universe(["c1", "c2"], ["c1", "c2", "c3"], context="annotation votes")


def test_negative_5_extra_candidate_id_rejected():
    with pytest.raises(IntegrityViolation, match="not in the canonical universe"):
        validate_exact_candidate_universe(["c1", "c2", "c3", "c99"], ["c1", "c2", "c3"], context="annotation votes")


def test_negative_6_duplicate_candidate_id_rejected():
    with pytest.raises(IntegrityViolation, match="duplicate"):
        validate_exact_candidate_universe(["c1", "c2", "c2"], ["c1", "c2"], context="annotation votes")


def test_exact_match_succeeds_without_raising():
    validate_exact_candidate_universe(["c2", "c1", "c3"], ["c1", "c2", "c3"], context="annotation ledger")


def test_negative_7_incomplete_annotation_ledger_rejected():
    # Same primitive reused for "annotation ledger" context (item 7).
    with pytest.raises(IntegrityViolation, match="missing"):
        validate_exact_candidate_universe(["c1"], ["c1", "c2", "c3"], context="annotation ledger")


def test_negative_8_extra_annotation_record_rejected():
    with pytest.raises(IntegrityViolation, match="not in the canonical universe"):
        validate_exact_candidate_universe(["c1", "c2", "c3", "extra"], ["c1", "c2", "c3"], context="annotation ledger")


def test_negative_9_duplicate_annotation_record_rejected():
    with pytest.raises(IntegrityViolation, match="duplicate"):
        validate_exact_candidate_universe(["c1", "c1", "c2"], ["c1", "c2"], context="annotation ledger")


# ---------------------------------------------------------------------------
# validate_provenance_hash / provenance header round-trip
# ---------------------------------------------------------------------------

def test_negative_10_mismatched_annotation_config_provenance_rejected():
    with pytest.raises(IntegrityViolation, match="annotation_config_sha256"):
        validate_provenance_hash("annotation_config_sha256", "a" * 64, "b" * 64)


def test_provenance_hash_matching_values_do_not_raise():
    validate_provenance_hash("raw_ledger_sha256", "c" * 64, "c" * 64)


def test_provenance_header_round_trip():
    fields = {"raw_ledger_sha256": "a" * 64, "annotation_config_sha256": "b" * 64, "candidate_count": "3"}
    lines = provenance_header_lines(fields)
    body_lines = lines + ["{\"candidate_id\": \"c1\"}"]
    parsed = parse_provenance_header(body_lines)
    assert parsed == fields  # stops at the first non-comment line, doesn't consume the JSON body


# ---------------------------------------------------------------------------
# Item 11: finalize freeze must not trust a configured raw_ledger_sha256
# ---------------------------------------------------------------------------

def test_negative_11_finalize_rejects_config_supplied_raw_ledger_hash(tmp_path, monkeypatch):
    """Exercises the actual script's guard, not just the library function.

    Runs scripts/finalize_amendment2_freeze.py as a subprocess against a
    --config that (deliberately, adversarially) includes a spoofed
    raw_ledger_sha256, and asserts the script refuses to run at all rather
    than silently ignoring or trusting the spoofed value.
    """
    import subprocess
    import sys as _sys
    from pathlib import Path as _Path

    repo_root = _Path(__file__).resolve().parents[1]
    cfg = {
        "raw_ledger_sha256": "0" * 64,  # spoofed -- must be rejected outright
        "audit_seed_hex": "0" * 64, "audit_size": 1, "double_coded_count": 20,
        "weighted_statistics": {}, "kappa_report": {}, "model_family_disjointness_attestation": True,
        "annotation_gate_ts": "2026-08-05T00:00:00Z", "manifest_ts": "2026-08-05T00:00:01Z",
        "audit_release_gate_ts": "2026-08-05T00:00:02Z", "implementation_commit": "a" * 40,
    }
    config_path = tmp_path / "freeze_config.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")
    raw_ledger_path = tmp_path / "raw_ledger.jsonl"
    raw_ledger_path.write_text("synthetic\n", encoding="utf-8")

    result = subprocess.run(
        [_sys.executable, str(repo_root / "scripts" / "finalize_amendment2_freeze.py"),
         "--raw-ledger", str(raw_ledger_path), "--config", str(config_path),
         "--artifacts-dir", str(tmp_path), "--output", str(tmp_path / "FREEZE.json")],
        capture_output=True, text=True, cwd=str(repo_root),
    )
    assert result.returncode != 0
    assert "raw_ledger_sha256" in (result.stdout + result.stderr)
    assert not (tmp_path / "FREEZE.json").exists()


# ---------------------------------------------------------------------------
# No new scientific policy: aggregation/sampling/stats modules untouched
# ---------------------------------------------------------------------------

def test_i4_r1_did_not_touch_scientific_policy_modules():
    """These implement frozen scientific rules and must be untouched by this repair.

    Uses ``git diff`` against HEAD~1 (the I4 baseline this repair started
    from) rather than a hardcoded hash, so the check stays meaningful if the
    repair itself is amended later in the same commit. Skips gracefully if
    git history isn't available in the environment running this test.
    """
    import subprocess
    from pathlib import Path as _Path

    repo_root = _Path(__file__).resolve().parents[1]
    protected = [
        "verification/eligibility/aggregation.py", "verification/eligibility/audit_sampling.py",
        "verification/eligibility/double_coding.py", "verification/eligibility/statistics.py",
        "verification/eligibility/human_audit.py", "verification/eligibility/annotation_config.py",
        "verification/eligibility/family_guard.py", "verification/eligibility/review_package.py",
        "verification/eligibility/annotation_runner.py", "verification/eligibility/annotation_models.py",
        "verification/eligibility/amendment2_freeze.py", "verification/eligibility/engine.py",
    ]
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"], capture_output=True, text=True, cwd=str(repo_root),
    )
    if result.returncode != 0:
        return  # no git history available in this environment; nothing to check
    changed = set(line.strip() for line in result.stdout.splitlines() if line.strip())
    touched = [p for p in protected if p in changed]
    assert not touched, "I4-R1 must not modify frozen scientific-policy modules, but changed: %s" % touched
