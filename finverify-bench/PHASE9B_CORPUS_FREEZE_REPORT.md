# Phase 9B Primary Source Corpus Freeze Report

## Status

**FINAL VERDICT: SAFE TO FREEZE**

Phase 9B establishes the authoritative primary-source corpus for the
FinVerifyBench verification track.

No scientific benchmark examples, DEV/TEST splits, perturbations, annotations,
or FinVerify outputs were created or inspected during corpus construction.

---

## Acquisition

Acquisition commit:

`e01860c3380c53d2e1a2bbc20f3356176dcf7084`

The corpus contains:

- 6 companies
- 12 source artifacts
- 2 artifacts per company

Companies:

- Apple Inc. (AAPL)
- The Goldman Sachs Group, Inc. (GS)
- JPMorgan Chase & Co. (JPM)
- Microsoft Corporation (MSFT)
- NVIDIA Corporation (NVDA)
- Tesla, Inc. (TSLA)

Source artifacts are stored under:

`data/verification/sources/`

---

## Canonical Representation

The canonical corpus representation is defined as the exact tracked
source-artifact bytes represented by the repository after acquisition commit:

`e01860c3380c53d2e1a2bbc20f3356176dcf7084`

SHA-256 is used for artifact integrity verification.

The canonical hashes and byte sizes are recorded in:

`data/verification/source_manifest.json`

---

## Provenance Note

Pre-commit acquisition hashes for text-formatted artifacts were observed to
differ from the representation inspected during corpus auditing, while the
binary PDF artifacts retained matching hashes.

This pattern is consistent with Git text normalization during commit, but
line-ending normalization has not been independently demonstrated as the sole
cause of every observed pre-commit discrepancy.

For reproducibility, the exact tracked source-artifact bytes represented after
the acquisition commit are therefore designated as the canonical corpus
representation for all subsequent experiments.

No scientific conclusion depends on the pre-commit byte representation.

---

## Independent Corpus Review

The acquired corpus underwent independent content and provenance review before
freeze.

The reviews found:

- primary-source provenance acceptable;
- financial content valid;
- no source replacement required;
- no corpus expansion required before eligibility filtering;
- no CRITICAL or HIGH corpus blocker.

The corpus was assessed as sufficient to proceed to eligibility-rule definition
and later candidate enumeration.

Feasibility assessments are not guarantees of the final number of eligible
examples. Final Natural and Controlled set sizes depend on application of the
subsequently frozen eligibility and sampling rules.

---

## Integrity Validation

The canonical manifest was independently validated against the source
directory.

Validation result:

- Manifest artifacts: 12/12
- Companies: 6/6
- Missing artifacts: 0
- Extra artifacts: 0
- Hash mismatches: 0
- Byte-size mismatches: 0

**Validation: PASS**

Validator:

`scripts/validate_source_manifest.py`

Manifest generator:

`scripts/generate_source_manifest.py`

---

## Scientific Isolation

During Phase 9B:

- FinVerify executed on corpus: **NO**
- Scientific examples created: **NO**
- Candidate claims selected: **NO**
- Controlled perturbations generated: **NO**
- DEV/TEST created: **NO**
- TEST outcomes inspected: **NO**
- Source artifacts modified during freeze: **NO**

Corpus selection and certification were performed independently of FinVerify
verification outcomes.

---

## Freeze Boundary

After this freeze, the 12 canonical source artifacts and their canonical hashes
must not be silently modified.

Any future source-corpus expansion or replacement must:

1. be explicitly documented;
2. have a methodological justification independent of FinVerify performance;
3. receive a new provenance record and hash;
4. preserve the original Phase 9B freeze record;
5. occur according to the subsequently frozen eligibility/expansion protocol.

The next phase is the definition and freeze of source/candidate eligibility
rules before scientific candidate enumeration.

---

## Final Declaration

Source artifacts modified during freeze: **NO**

Manifest artifacts: **12/12**

Companies: **6/6**

Canonical hash validation: **PASS**

Missing artifacts: **0**

Extra artifacts: **0**

Hash mismatches: **0**

Byte-size mismatches: **0**

FinVerify executed: **NO**

Scientific examples created: **NO**

DEV/TEST created: **NO**

**FINAL VERDICT: SAFE TO COMMIT**