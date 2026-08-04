# Phase 9C-G Eligibility Implementation Report

## Scope and provenance

- Starting commit: `2985f2dc3fa4ddd4d44c2f8fd5b52fe6ba3f6b34`
- Authoritative contracts: `SOURCE_ELIGIBILITY_v1.md` plus
  `SOURCE_ELIGIBILITY_AMENDMENT_1.md` and
  `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md`.
- Scientific Run-2 ledger: not opened, read, hashed, or enumerated.
- Production eligibility: not executed.
- FinVerify, model, baseline, verifier, and benchmark outcomes: not used.

## Implemented boundary

The engine separates raw schema/provenance validation, reviewer-supplied
semantic decisions, and deterministic post-review construction. It does not
infer financial eligibility, replace human review, generate perturbations, or
sample.

Implemented contracts include:

- exact lexical and structured identity normalization with conservative
  `UNKNOWN`, `UNSPECIFIED`, and `NOT_APPLICABLE` semantics;
- exact normalized-value keys without tolerance or fuzzy comparison;
- complete raw-record preservation and review-state validation;
- frozen reason-code validation and precedence;
- fact clustering with singleton retention when identity is unresolved;
- unchanged Section 40 canonical hierarchy;
- Amendment 1 source-event graph grouping, transitive components, and
  deterministic `source_group_id` construction;
- the seven pre-sampling challengeable dimensions and per-parent recoverable
  subset;
- Natural and Controlled-parent pools without Phase 9D sampling;
- the exact expansion trigger only;
- deterministic JSON/JSONL serialization and non-overwriting outputs;
- default-deny protection for the canonical Run-2 path and hash/schema checks
  when authorization is explicitly supplied.

## Synthetic validation

The implementation tests use only synthetic records and fixtures. They cover
normalization, state semantics, identity separation, duplicate clusters,
canonical tie-breaks, source-event grouping and transitivity, Controlled-parent
recoverability, Phase 9D independence, expansion thresholds, deterministic
serialization, production denial, authorization validation, and dependency
isolation.

The CLI writes eligibility ledger/pool views, source-group and summary
artifacts, and an `ELIGIBILITY_FREEZE.json` containing input and output hashes,
protocol/amendment version, and implementation-commit provenance. Existing
frozen outputs are never silently overwritten.

## Restrictions verified

No frozen scientific specification, enumeration parser, numeric grammar,
candidate-ID construction, verifier/model code, or scientific enumeration
artifact was changed. No production authorization was granted and no commit
or push was performed.

Validation results: focused eligibility tests **18 passed**; existing
FinVerifyBench tests **81 passed**; frozen Phase 7H identity/provenance tests
**7 passed**. The backend regression suite was not rerun because the new
eligibility package has no backend import overlap.
