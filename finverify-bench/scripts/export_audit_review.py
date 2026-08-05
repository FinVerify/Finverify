#!/usr/bin/env python3
"""Export the blinded human-audit review package and a private candidate mapping.

Gate 2 (audit release) must already be authorized before this is run against
production data; see verification.eligibility.amendment2_freeze.authorize_audit_release.
This script itself only performs the blinding transform — it does not check
the gate, since callers may want to inspect a synthetic export without
touching production authorization at all.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verification.eligibility.review_package import export_blinded_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-candidates", type=Path, required=True,
                         help="JSONL of raw-ledger-plus-evidence records restricted to the selected audit sample")
    parser.add_argument("--shuffle-seed-source", required=True,
                         help="string combined with a fixed domain tag to derive the presentation-order seed")
    parser.add_argument("--output-rows", type=Path, required=True)
    parser.add_argument("--output-mapping", type=Path, required=True)
    args = parser.parse_args()

    candidates = [json.loads(line) for line in args.selected_candidates.read_text(encoding="utf-8").splitlines() if line.strip()]
    shuffle_seed_hex = hashlib.sha256(("finverify-phase9c-audit-shuffle-v1\n" + args.shuffle_seed_source).encode("utf-8")).hexdigest()
    rows, mapping = export_blinded_audit(candidates, shuffle_seed_hex=shuffle_seed_hex)

    with args.output_rows.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    with args.output_mapping.open("w", encoding="utf-8") as handle:
        json.dump(mapping, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("exported %d blinded audit rows" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
