# Phase 9C-A1 — PDF Parser Defect Amendment

## Frozen provenance

- Frozen enumerator commit: `933065de26bc687cbc85efc689aeeee042d2c3bd`
- Production authorization commit: `8a1f445fc972b0daac6685bfeb6bbd61c09a5915`
- First-run raw candidate count: `114,524`
- First-run raw ledger size: `989078352` bytes
- First-run raw ledger SHA-256: `BB85D4F1513254CFDE73CDD134BD5EE693428AB8B167704672C889AFB1EFF38E`
- First-run parse-issues SHA-256: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- First-run freeze manifest SHA-256: `8422CA0B270F3D148941367E9A1E70C9DCBFD7E9AFD2A696D496E5EF0CEB9D3E`

The first-run artifacts are treated as immutable. They were not regenerated, rewritten, or deleted for this amendment. The statistics below are frozen diagnostic facts supplied from the post-freeze structural review; no additional scientific candidates were inspected here.

## Defect observation

The TSLA-02 anomaly was reported as:

- 89,028 total candidates;
- 84,544 plain-number candidates;
- 108,891 PDF candidates out of 114,524 total candidates;
- source locator `page/35/block/144`;
- 4,455 candidates in the affected structural block;
- raw span length 2,074 characters containing binary garbage, replacement/control characters, and arbitrary byte-like content.

This is a deterministic PDF text-extraction defect. The current parser accepts every `stream ... endstream` payload as possible content, including binary resource streams. It then searches those bytes for `BT ... ET` operators and decodes parenthesized or hexadecimal patterns as visible text. A binary payload containing such a pattern can therefore become a `StructuralBlock`; the numeric grammar subsequently enumerates digits in that phantom text.

The synthetic reproduction in `tests/test_enumerator.py` demonstrates the complete failure path: a binary-like image stream produces the visible span `binary phantom 987`, and `987` enters the raw candidate universe with a PDF structural locator.

## Frozen-spec classification

This violates the frozen deterministic source-text and structural-provenance requirements in `ENUMERATOR_SPEC.md` (including the source-stream classification and structural extraction requirements in sections 12, 25, 38, and 39). It is a parser sanitation/text-extraction defect, not an eligibility-policy decision. It does not establish any verifier, model, or downstream scientific outcome, and none was used to identify or reproduce it.

The defect does not authorize rewriting the first-run provenance or silently changing the frozen corpus. Any subsequent repair must be evaluated as a post-freeze defect amendment under the protocol.

## Permitted repair scope

The repair review may modify only deterministic PDF parser stream classification and text sanitization, while preserving source hashes, page/block provenance, target-offset invariants, and explicit parse-issue behavior. It must add or retain synthetic regression coverage for binary-resource contamination. It must not modify numeric grammar, segmentation policy, eligibility policy, verifier behavior, model behavior, or the frozen specifications. No production corpus rerun is authorized by this amendment.

Focused synthetic reproduction test: passed.
