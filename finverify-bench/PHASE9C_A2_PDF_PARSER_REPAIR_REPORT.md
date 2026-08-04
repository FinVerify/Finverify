# Phase 9C-A2 — PDF Parser Repair Report

## Provenance

- Starting commit: `a4cb0d82edb939155d5666e6fba84dd1be2e0c49`
- A1 amendment commit: `a4cb0d82edb939155d5666e6fba84dd1be2e0c49`
- Production file changed: `finverify-bench/verification/enumeration/pdf_parser.py`
- Synthetic test file changed: `finverify-bench/tests/test_enumerator.py`

The first-run artifacts remain untouched: no ledger, parse-issues file, freeze manifest, source manifest, source hash, or scientific source artifact was modified, regenerated, normalized, or replaced.

## Confirmed root cause

The pre-repair parser scanned every PDF `stream ... endstream` payload for `BT ... ET` text operators. Binary resource streams could therefore be interpreted as visible text when arbitrary bytes contained parenthesized or hexadecimal string patterns. The A1 fixture demonstrated that this caused phantom candidate `987` to enter the raw candidate universe.

## Repair mechanism

The parser now builds a deterministic local object map, identifies `/Type /Page` objects, and extracts only streams directly owned by a page or referenced by that page's `/Contents` entry. Unrelated streams such as `/Subtype /Image` are not selected. Flate decoding remains local and deterministic; malformed compressed streams are skipped as before. The fallback that scanned the entire PDF byte buffer when no streams were found was removed, so unsupported or text-unrecoverable input preserves the explicit `pdf_text_unavailable` issue instead of exposing arbitrary bytes.

This follows the pre-existing frozen PDF requirements: deterministic local extraction, page provenance, explicit recovery issues, visible-text-only numeric enumeration, and no OCR or learned reconstruction. It is not candidate-distribution tuning because it uses PDF object/page semantics and does not inspect or target scientific counts, source IDs, filenames, pages, or observed candidate composition.

## Synthetic regression coverage

The A1 reproducer now verifies that:

- legitimate visible page text remains a structural block;
- `$123 million` remains enumerated;
- binary-resource phantom text is not a structural block;
- phantom candidate `987` is absent;
- page/block provenance remains deterministic;
- repeated enumeration produces identical candidate records;
- a PDF with no recoverable visible text retains the explicit parse issue.

Existing synthetic tests continue to cover unsupported formats, malformed/hash-guard behavior, page provenance, numeric grammar, and repeated JSONL determinism.

## Test results

- Focused PDF tests: **3 passed**.
- Focused enumerator test file: **37 passed**.
- Existing FinVerifyBench test suite: **63 passed**.
- Frozen Phase 7H identity/provenance tests: **7 passed**.
- Backend regression suite: **553 passed, 1 warning** (an existing `PendingDeprecationWarning` from `starlette.formparsers`).

The scientific corpus was not enumerated. No additional scientific candidates were inspected. No FinVerify, verifier, model, baseline, or LLM outcomes were used.

## Known limitations

This remains a minimal structural extractor rather than a complete PDF implementation. It relies on the existing deterministic object syntax and does not add OCR, table inference, researcher arithmetic, or a third-party parser. PDFs whose page/content relationships cannot be recovered from the supported local structure may produce `pdf_text_unavailable`; this is explicit and deterministic.

## Self-audit

`numeric.py`, `segmentation.py`, `models.py`, the HTML/MHTML parsers, `ledger.py`, all frozen specifications, source artifacts, and first-run artifacts are unchanged by this repair. The production repair diff contains none of: `TSLA`, `AAPL`, `114524`, `89028`, `page/35`, or `block/144`.

No commit or push was performed. Unrelated pre-existing worktree modifications were preserved.
