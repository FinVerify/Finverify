#!/usr/bin/env python3
"""Freeze the corrected Run-3 enumeration after its implementation is committed."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

EXPECTED_COUNT = 14118
RUN2_SHA256 = "ec9532fa60225be63d5446ca2137b260255d97a74354a25e82f1b3ecd62a0093"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--enumerator-commit', required=True)
    ap.add_argument('--ledger', type=Path, default=Path('data/verification/enumeration/raw_candidate_ledger_run3.jsonl'))
    ap.add_argument('--issues', type=Path, default=Path('data/verification/enumeration/parse_issues_run3.jsonl'))
    ap.add_argument('--output', type=Path, default=Path('data/verification/enumeration/THIRD_RUN_FREEZE.json'))
    a=ap.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', a.enumerator_commit):
        raise SystemExit('enumerator commit must be a 40-character lowercase git SHA')
    run2=Path('data/verification/enumeration/raw_candidate_ledger_run2.jsonl')
    if sha(run2) != RUN2_SHA256:
        raise SystemExit('historical Run-2 ledger hash mismatch')
    rows=[json.loads(x) for x in a.ledger.read_text(encoding='utf-8').splitlines() if x.strip()]
    ids=[r['candidate_id'] for r in rows]
    if len(rows) != EXPECTED_COUNT:
        raise SystemExit(f'Run-3 candidate count mismatch: {len(rows)} != {EXPECTED_COUNT}')
    if len(set(ids)) != EXPECTED_COUNT:
        raise SystemExit('Run-3 candidate IDs are not globally unique')
    if not all(cid.startswith('fvq2_') for cid in ids):
        raise SystemExit('Run-3 contains a non-fvq2 candidate ID')
    issue_count=len([x for x in a.issues.read_bytes().splitlines() if x.strip()])
    obj={
      'phase':'9C-R3',
      'artifact':'candidate_identity_collision_repair_canonical_raw_enumeration',
      'enumerator_commit':a.enumerator_commit,
      'enumeration_schema_version':'fvq2-raw-v1',
      'candidate_count':EXPECTED_COUNT,
      'unique_candidate_id_count':EXPECTED_COUNT,
      'parse_issue_count':issue_count,
      'raw_candidate_ledger':{'relative_path':'data/verification/enumeration/raw_candidate_ledger_run3.jsonl','byte_size':a.ledger.stat().st_size,'sha256':sha(a.ledger)},
      'parse_issue_ledger':{'relative_path':'data/verification/enumeration/parse_issues_run3.jsonl','byte_size':a.issues.stat().st_size,'sha256':sha(a.issues)},
      'supersedes_for_scientific_use':'SECOND_RUN_FREEZE.json',
      'supersession_reason':'Run-2 candidate identity omitted deterministic segment identity while target offsets were segment-relative, causing distinct quantitative occurrences to share candidate_id. Discovered before production annotation; source corpus, parsing, segmentation, and occurrence universe are unchanged.'
    }
    if a.output.exists():
        raise SystemExit('refusing to overwrite existing THIRD_RUN_FREEZE.json')
    a.output.write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f'frozen Run-3: {EXPECTED_COUNT} rows, {EXPECTED_COUNT} unique IDs, sha256={sha(a.ledger)}')
    return 0
if __name__=='__main__': raise SystemExit(main())
