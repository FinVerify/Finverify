"""Repository-level regression checks for the Run-3 candidate identity repair."""
import hashlib, json
from pathlib import Path
import pytest
from verification.eligibility.engine import load_raw_ledger

ROOT=Path(__file__).resolve().parents[1]
ENUM=ROOT/'data'/'verification'/'enumeration'
HISTORICAL={
 'raw_candidate_ledger.jsonl':'bb85d4f1513254cfde73cdd134bd5ee693428ab8b167704672c889afb1eff38e',
 'raw_candidate_ledger_run2.jsonl':'ec9532fa60225be63d5446ca2137b260255d97a74354a25e82f1b3ecd62a0093',
 'FIRST_RUN_FREEZE.json':'8422ca0b270f3d148941367e9a1e70c9dcbfd7e9afd2a696d496e5ef0ceb9d3e',
 'SECOND_RUN_FREEZE.json':'f69357c568ec256716da514999431667f3e3418ac510270035a82d28e219edce',
}

def _sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def test_historical_enumeration_artifacts_are_immutable():
    for name,digest in HISTORICAL.items(): assert _sha(ENUM/name)==digest

def test_run3_has_exact_unique_fvq2_universe():
    p=ENUM/'raw_candidate_ledger_run3.jsonl'
    rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
    ids=[r['candidate_id'] for r in rows]
    assert len(rows)==14118
    assert len(set(ids))==14118
    assert all(x.startswith('fvq2_') for x in ids)
    assert _sha(p)=='1b126257e5a0e7c25a633d4b14d9eea5739378692ad1a777b48776231f32e37d'

def test_run3_is_default_deny_without_production_authorization():
    with pytest.raises(PermissionError):
        load_raw_ledger(ENUM/'raw_candidate_ledger_run3.jsonl')

def test_run3_passes_structural_integrity_loader_when_authorized():
    records=load_raw_ledger(
        ENUM/'raw_candidate_ledger_run3.jsonl',
        allow_production=True,
        freeze_metadata_path=ENUM/'THIRD_RUN_FREEZE.json',
        implementation_commit='a' * 40,
    )
    assert len(records)==14118
    assert all(record['candidate_id'].startswith('fvq2_') for record in records)

def test_historical_run2_still_fails_duplicate_identity_after_authorization_gate(monkeypatch):
    # Bypass only the historical production-path gate to reach the known
    # duplicate-key invariant; never alter the frozen artifact itself.
    import verification.eligibility.engine as e
    monkeypatch.setattr(e, '_is_run2', lambda path: False)
    with pytest.raises(ValueError, match='duplicate candidate_id'):
        load_raw_ledger(ENUM/'raw_candidate_ledger_run2.jsonl')
