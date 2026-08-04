# Phase 8 Infrastructure Report

- Starting commit: `f1ff63e06c0751218dfbcf2071cbb434aa8fa873`
- Governing documents: `PROTOCOL.md` v3 and `EXPERIMENT_SPEC_v1.md` v1.0
- Phase 8 scope: reusable verification-track infrastructure only; no scientific dataset or experiment was run.

## Architecture

Added a small standard-library `verification/` package alongside the existing
FinVerifyBench code. It contains:

- `schema.py`: versioned JSONL pair, claim/evidence, source provenance, and annotation records;
- `perturbations.py`: matched controls and deterministic single-dimension derivatives;
- `natural.py`: source-backed natural-pair ingestion without verifier calls;
- `splitting.py`: source-group-safe DEV/TEST assignment;
- `validators.py`: schema, leakage, parent-link, value-invariance, and single-dimension checks;
- `freeze.py`: read-only SHA-256 hashing and non-overwriting freeze manifests;
- `annotations.py`: blinded CSV export, private mapping, raw-response import/preservation;
- `summary.py` and `io.py`: dataset QA summaries and JSONL I/O.

Thin CLI scripts were added for validation, splitting, freezing, annotation
export, and annotation import.

Controlled perturbations preserve values and source groups, record parent and
shift dimension, and require exactly one changed identity dimension. The
infrastructure does not assume diagnostic dimensions are verifier gates.

## Tests

- Phase 8 infrastructure tests: 11 passed.
- Existing FinVerifyBench tests: 15 passed.
- Frozen Phase 7H/identity/provenance tests: 52 passed.
- Backend regression: 553 passed, 1 warning; unchanged from the frozen baseline.

## Integrity and limitations

- Frozen verifier files were not modified.
- Existing FinVerifyBench-Numeric data were not modified by Phase 8; the pre-existing `finverify-bench/data/seed_50.json` worktree modification was preserved.
- No final scientific DEV/TEST dataset, Natural Set, annotation collection, A0/A1/A2 runner, baseline, bootstrap, or paper table was created.
- Annotation agreement calculation and adjudication are intentionally deferred; imported raw rows preserve all required fields.
- Content-level human eligibility and textual perturbation rendering remain operator-controlled and are not inferred by this infrastructure.

## Next human/operator phase

1. Prepare source-backed candidate pairs independently of FinVerify output.
2. Run `python scripts/validate_verification_dataset.py --input <pairs.jsonl> --output <validation.json>`.
3. Run `python scripts/split_verification_dataset.py --input <pairs.jsonl> --output <split.jsonl> --manifest <split_manifest.json> --seed 20260804`.
4. Review and freeze the resulting source-group manifest before any central TEST construction.
5. Export blinded annotation tasks with `python scripts/export_annotations.py --input <pairs.jsonl> --output <annotation.csv> --mapping <private_mapping.json>`.
6. Preserve responses with `python scripts/import_annotations.py --input <responses.csv> --mapping <private_mapping.json> --raw-output <annotations_raw.jsonl>`.
7. Create a dataset freeze manifest with `python scripts/freeze_verification_dataset.py --input <dataset.jsonl> --output <freeze_manifest.json> --seed 20260804`.

Do not proceed to final dataset construction, annotation collection, A0/A1/A2,
baselines, or statistics until the protocol/spec freeze prerequisites are
completed.
