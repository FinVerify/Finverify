# ELIGIBILITY_IMPLEMENTATION_RUN3_SUPERSESSION

**Status:** Amendment
**Supersedes (provenance only):** `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` (Run-2 enumeration references)
**Scope:** Enumeration input/corpus provenance only

## 1. Relationship to ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md

`ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` is preserved unmodified as historical
provenance. It predates the Run-3 enumeration-integrity repair and continues
to describe the eligibility rubric, annotation methodology, reason codes,
evidence rules, aggregation, audit sampling, statistics, duplicate
equivalence, source grouping, Controlled-parent rules, verifier behavior, and
Phase 9D sampling exactly as originally written. This amendment does not
alter, replace, or restate any of that content.

## 2. Run-3 supersedes Run-2 as the canonical scientific enumeration

Run-3 supersedes Run-2 as the canonical scientific enumeration on account of
a documented enumeration-integrity repair. Any statement in
`ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` that identifies Run-2 as the
canonical input/corpus provenance is superseded by this amendment. All other
(methodological) statements in that document remain unchanged and in force.

## 3. Run-2 status: defect provenance only, never a fallback

Run-2 is permanently retired from scientific and production use. It is
preserved solely as defect/historical provenance for audit purposes. Run-2
MUST NOT be used as a scientific fallback under any circumstance, including
failure, unavailability, or incompleteness of Run-3.

## 4. Canonical production binding

Production eligibility and annotation are bound exclusively to:

- `data/verification/enumeration/raw_candidate_ledger_run3.jsonl`
- `THIRD_RUN_FREEZE.json`

## 5. Run-3 provenance record

| Field | Value |
|---|---|
| Run-3 ledger relative path | `data/verification/enumeration/raw_candidate_ledger_run3.jsonl` |
| Run-3 ledger SHA-256 | `1b126257e5a0e7c25a633d4b14d9eea5739378692ad1a777b48776231f32e37d` |
| Run-3 freeze file | `THIRD_RUN_FREEZE.json` |
| Run-3 freeze SHA-256 | `f7fd2e4b79507a763a47eee496e58f2e0c0477d46b40cda3eec54420685e564b` |
| Run-3 enumeration commit | `e077014e3c74e691b362b25a4e58ddf3303e9006` |
| Run-3 candidate count | 14,118 |
| Run-3 candidate-ID schema | `fvq2_` prefix |

For historical reference, the retired Run-2 provenance is:

| Field | Value |
|---|---|
| Run-2 ledger SHA-256 | `ec9532fa60225be63d5446ca2137b260255d97a74354a25e82f1b3ecd62a0093` |
| Run-2 freeze SHA-256 | `f69357c568ec256716da514999431667f3e3418ac510270035a82d28e219edce` |

## 6. No change to scientific methodology

This amendment is limited to enumeration input/corpus identity and
provenance. The Run-3 repair changed enumeration identity/provenance only.
It did not change, and this amendment does not change, the eligibility
rubric, annotation methodology, reason codes, evidence rules, aggregation,
audit sampling, statistics, duplicate equivalence, source grouping,
Controlled-parent rules, verifier behavior, or Phase 9D sampling as defined
in `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md`.

## 7. Scope of superseded references

Within `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md`, references to "Run-2" that
identify the canonical input/corpus provenance (e.g. the frozen raw
candidate ledger and its hash) are superseded by Run-3 as recorded in
Section 5 above. References to "Run-2" that are purely methodological in
nature (i.e., not identifying corpus/provenance) are unaffected and remain
in force.

## 8. Forward provenance requirement

All future `ELIGIBILITY_FREEZE.json` artifacts must record the Run-3 ledger
SHA-256 (`1b126257e5a0e7c25a633d4b14d9eea5739378692ad1a777b48776231f32e37d`)
as canonical enumeration provenance. Recording the Run-2 ledger hash as
canonical provenance in any such future artifact is prohibited.

## 9. Corpus size

The canonical corpus size is preserved unchanged at 14,118 candidates.

## 10. No other changes

This amendment makes no changes beyond those stated in Sections 1-9. It does
not modify the eligibility rubric, annotation methodology, reason codes,
evidence rules, aggregation, audit sampling, statistics, sample sizes, or any
other scientific policy.
