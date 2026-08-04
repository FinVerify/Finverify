# Phase 9C-E Enumerator Freeze Report

Starting commit: `ce863ab0ed573414dc56ff1eba17da5037876919`

Governing frozen documents:

- `ENUMERATOR_SPEC_v1.md`
- `SOURCE_ELIGIBILITY_v1.md`
- `PROTOCOL.md`
- `EXPERIMENT_SPEC_v1.md`
- `PHASE8_INFRA_REPORT.md`
- `data/verification/source_manifest.json` (metadata/schema inspected only)

SHA-256 references:

- `PROTOCOL.md`: `20BE7CD07B933F3417024ADDC99C947CC45985741AA1365B45EDEB4C4FB0D0A1`
- `EXPERIMENT_SPEC_v1.md`: `1AB06CDF89AA42DBC80E48674AFFB6C54AD0F38418BE4F87E715B98E900053EA`
- `ENUMERATOR_SPEC_v1.md`: `303D50CD07230BB48A4DFB0BC9309CBFED50CCEEBC8A4FBC9B515406DF1EADB8`
- `SOURCE_ELIGIBILITY_v1.md`: `7E19D2F11906D0723EBA65A4FC95DD1C79952DE09E475DDFC1D3898BE5C7AC03`

## Implementation

Implemented a verifier-blind `verification/enumeration/` package with:

- manifest-backed source identity and SHA-256 validation;
- mandatory canonical Phase 9B corpus guard;
- deterministic HTML, MHTML, and local PDF structural parsing;
- frozen punctuation segmentation;
- frozen lexical quantitative grammar and precedence;
- atomic multi-number extraction, normalization, provenance, and source locators;
- exact `fvq1_` SHA-256 candidate IDs;
- deterministic raw candidate and parse-issue JSONL serialization;
- CLI: `scripts/enumerate_verification_candidates.py`.

Parsing uses Python standard-library modules only, including `html.parser`,
`email`, `zlib`, and PDF text-operator parsing. No models, OCR, network, or
additional parsing dependency was introduced.

Synthetic coverage includes HTML prose/table, MHTML local primary HTML, PDF
multi-page prose, compressed-text-capable PDF parsing, numeric grammar cases,
hash failures, deterministic ordering/output, and the production-corpus guard.

Files added/modified by this phase are confined to `finverify-bench/verification/enumeration/`,
`finverify-bench/scripts/enumerate_verification_candidates.py`,
`finverify-bench/tests/test_enumerator.py`, and this report. Frozen documents,
Phase 7H verifier files, frontend files, and existing numeric data were not
modified.

## Verification results

- Focused enumerator tests: 32 passed, including blocker-repair regressions for percentage words, singular/plural basis-point forms, `bps`, `times`, adjacent `x`, and rejection of spaced `12 x` as a ratio.
- Existing FinVerifyBench tests: 15 passed.
- Frozen identity/provenance tests: 52 passed.
- Backend regression: 553 passed, 1 warning.
- Deterministic repeated-output and SHA-256 test: passed.
- Production-corpus guard test: passed; canonical source artifacts were not opened or enumerated.
- Manifest/hash validation tests: passed for success, mismatch, and missing artifact.

No real Phase 9B corpus was enumerated. `data/verification/sources/**` was not
modified or quantitatively inspected. No candidate ledger, Natural Set,
Controlled Set, eligibility review, split, sampling, or experiment output was
created.

## Known limitations

- PDF extraction is deterministic local text-operator parsing with FlateDecode
  support; OCR and inferred PDF table structure are intentionally unsupported.
- PDFs using unusual font encodings or image-only pages may produce parse
  issues rather than recovered text.
- Candidate enumeration is intentionally syntactic and does not perform
  financial eligibility filtering, deduplication, or researcher arithmetic.

Remaining CRITICAL/HIGH findings: NONE.

Final status: READY FOR ADVERSARIAL REVIEW. Do not enumerate the canonical
corpus until the separate post-freeze production authorization step is
introduced and recorded.
