# FinVerify Identity-Aware Verification

## EXPERIMENT_SPEC.md --- v1.0 Final Candidate

**Study:** Identity-Aware Verification of Numerical Financial Claims\
**Working paper title:** *Beyond Numerical Coincidence: Identity-Aware
Verification of AI-Generated Financial Claims*\
**Governing protocol:** `FinVerify Experimental Protocol v3`\
**Purpose:** Executable implementation contract for dataset tooling,
experiment runners, metrics, statistics, result provenance, and
paper-table generation.

> This document does not redefine the scientific protocol. If this
> specification conflicts with Protocol v3, Protocol v3 wins. Any
> ambiguity that could alter a TEST result must be resolved before
> central TEST execution and recorded before freeze.

------------------------------------------------------------------------

# 0. Implementation philosophy

The experiment code must evaluate the frozen FinVerify system; it must
not improve it.

The implementation must therefore obey five rules:

1.  **No TEST-driven development.**
2.  **No new verification semantics.**
3.  **No hidden fallback that converts missing identity information into
    a match.**
4.  **No manual experimental numbers.**
5.  **Every reported result must be reproducible from a frozen command
    and machine-readable artifact.**

The implementation should be minimal. Do not refactor unrelated
FinVerify or FinVerifyBench code merely to make the experiment directory
aesthetically cleaner.

------------------------------------------------------------------------

# 1. Required freeze inputs

Before any central TEST run, create a machine-readable
`freeze_manifest.json` containing at least:

``` json
{
  "protocol_version": "v3",
  "protocol_sha256": "<filled-after-freeze>",
  "protocol_git_commit": "<filled-after-freeze>",
  "finverify_git_commit": "<post-7G SHA>",
  "finverify_git_tag": "<research tag>",
  "git_dirty": false,
  "python_version": "<exact>",
  "dependency_fingerprint": "<lock/hash or environment identifier>",
  "canonical_verification_path": "<module:function>",
  "numeric_tolerance_rule": "<exact frozen rule>",
  "concept_unknown_semantics": "<exact frozen rule>",
  "period_unknown_semantics": "<exact frozen rule>",
  "controlled_split_seed": 20260804,
  "bootstrap_seed": 20260806,
  "bootstrap_replicates": 10000,
  "embedding_model": "<frozen before TEST>",
  "embedding_revision": "<frozen before TEST>",
  "embedding_threshold": "<DEV-selected before TEST>",
  "llm_judge_included": false,
  "llm_judge_model": null,
  "central_test_started_at": null
}
```

If an implementation-dependent field remains unresolved, central TEST
execution is blocked.

------------------------------------------------------------------------

# 2. Recommended minimal architecture

The exact paths may be adapted to the audited repository. Do not
duplicate canonical code unnecessarily.

``` text
finverify-bench/
├── verification/
│   ├── schema.py
│   ├── evaluator.py
│   ├── metrics.py
│   ├── ablations.py
│   ├── perturbations.py
│   ├── statistics.py
│   └── validators.py
│
├── data/
│   └── verification/
│       ├── sources_manifest.json
│       ├── controlled_dev.jsonl
│       ├── controlled_test.jsonl
│       ├── natural_dev.jsonl          # only if used
│       ├── natural_test.jsonl
│       ├── extraction_eval.jsonl
│       ├── annotations_raw.csv
│       └── annotations_gold.csv
│
├── scripts/
│   ├── build_controlled_dataset.py
│   ├── build_natural_candidates.py
│   ├── validate_verification_dataset.py
│   ├── export_annotation_forms.py
│   ├── import_annotations.py
│   ├── run_extraction_evaluation.py
│   ├── run_identity_ablation.py
│   ├── run_provenance_evaluation.py
│   ├── run_diagnostic_challenge.py
│   ├── run_natural_evaluation.py
│   ├── run_gold_vs_extracted.py
│   ├── run_embedding_baseline.py
│   ├── run_llm_judge.py
│   ├── run_numeric_continuity.py
│   ├── run_statistics.py
│   └── generate_paper_tables.py
│
├── results/
└── paper/generated/
```

The existing FinVerifyBench Numeric track must remain untouched.

------------------------------------------------------------------------

# 3. Canonical verification-pair schema

Each verification pair must have a stable immutable ID.

``` json
{
  "id": "fvv_000001",
  "source_group_id": "src_nvda_q4fy25_revenue",
  "split": "test",
  "dataset_track": "controlled_primary",

  "claim": {
    "text": "NVIDIA Q4 FY2025 revenue was $39.3 billion.",
    "value": 39300000000,
    "entity": "NVDA",
    "concept": "Revenue",
    "period": "Q4_FY2025",
    "accounting_basis": null,
    "scope": "company",
    "temporal_frame": "actual",
    "value_role": "current"
  },

  "evidence": {
    "text": "...",
    "value": 39300000000,
    "entity": "NVDA",
    "concept": "Revenue",
    "period": "Q4_FY2025",
    "accounting_basis": null,
    "scope": "company",
    "temporal_frame": "actual",
    "value_role": "current"
  },

  "gold_label": "SUPPORT",
  "pair_type": "matched_control",
  "shift_dimension": null,

  "source": {
    "ticker": "NVDA",
    "document_type": "earnings_release",
    "document_id": "<stable id>",
    "document_hash": "<sha256>"
  },

  "construction": {
    "generator_version": "<commit>",
    "seed": 20260804,
    "parent_pair_id": null
  }
}
```

Allowed `gold_label` values:

``` text
SUPPORT
REJECT
INSUFFICIENT
```

Allowed controlled `shift_dimension` values:

``` text
concept
period
entity
scope
accounting_basis
temporal_frame
value_role
null
```

Do not encode expected FinVerify output in the dataset.

------------------------------------------------------------------------

# 4. Canonical run-record schema

Every evaluated example must produce a row containing at least:

``` json
{
  "run_id": "...",
  "example_id": "fvv_000001",
  "source_group_id": "...",
  "split": "test",
  "experiment_id": "E3",
  "configuration": "A2",
  "gold_label": "SUPPORT",
  "system_status": "VERIFIED",
  "raw_value": 39300000000,
  "corrected_value": null,
  "evidence_value": 39300000000,
  "gold_concept": "Revenue",
  "extracted_concept": "Revenue",
  "gold_period": "Q4_FY2025",
  "extracted_period": "Q4_FY2025",
  "correction_applied": false,
  "metadata": {}
}
```

Allowed system statuses are exactly:

``` text
VERIFIED
VERIFIED_WITH_CORRECTION
REJECTED
UNRESOLVED
EVIDENCE_UNAVAILABLE
UNMAPPED
```

Unknown internal states must not silently map to `VERIFIED`.

------------------------------------------------------------------------

# 5. Dataset build order

The implementation must enforce this dependency order:

``` text
freeze source documents
        ↓
assign source_group_id
        ↓
split source groups DEV / TEST
        ↓
generate controlled matched controls
        ↓
generate controlled perturbations
        ↓
validate controlled construction
        ↓
freeze controlled datasets + hashes
```

Variants from one source group may never cross DEV/TEST.

Default controlled split seed:

``` text
20260804
```

Target source-group allocation:

``` text
DEV  = approximately 30–40%
TEST = approximately 60–70%
```

No manual movement after perturbation generation.

------------------------------------------------------------------------

# 6. Controlled dataset construction

## 6.1 Source-claim target

Start with approximately 15--20 independent real source claims.

A source claim must:

-   represent a real numerical financial assertion;
-   have traceable evidence;
-   have interpretable Concept and Period;
-   support a legitimate matched SUPPORT control;
-   permit at least one financially meaningful perturbation.

Do not select source claims based on whether FinVerify currently
succeeds.

## 6.2 Matched control

For every source claim:

``` text
claim financial identity == evidence financial identity
claim value == evidence value
gold_label = SUPPORT
pair_type = matched_control
```

## 6.3 Primary perturbations

Primary controlled perturbations are only:

``` text
concept
period
```

For each adversarial pair:

``` text
claim value == evidence value
exactly one target identity dimension changes
gold_label = REJECT
dataset_track = controlled_primary
```

These examples feed E1, E2, and E3.

## 6.4 Diagnostic perturbations

Diagnostic dimensions:

``` text
entity
scope
accounting_basis
temporal_frame
value_role
```

They feed E5 only.

They do **not** imply that FinVerify implements corresponding gates.

## 6.5 Controlled validator

`validate_verification_dataset.py` must fail non-zero if any of the
following occurs:

-   duplicate example ID;
-   duplicate source-group assignment conflict;
-   source group appears in both DEV and TEST;
-   adversarial value differs from its matched control;
-   target dimension did not change;
-   more than one declared identity dimension changed without explicit
    exception metadata;
-   missing parent/control link;
-   invalid label;
-   invalid split;
-   missing document provenance;
-   missing required Concept/Period for a primary challenge pair;
-   schema validation failure.

Produce:

``` text
results/dataset_validation.json
```

with counts and all violations.

------------------------------------------------------------------------

# 7. Natural dataset construction

## 7.1 Source universe

Freeze exact documents from the pre-existing six-company universe:

``` text
AAPL
TSLA
JPM
NVDA
MSFT
GS
```

Record document IDs/hashes before candidate sampling.

## 7.2 Candidate generation

`build_natural_candidates.py` may use the frozen extraction pipeline to
identify candidate numerical claims, but eligibility must not depend on:

-   successful Concept extraction;
-   successful Period extraction;
-   successful scope/basis/frame tagging;
-   successful canonical mapping;
-   value agreement;
-   FinVerify status.

Any extraction-based candidate-generation limitation must be documented.

## 7.3 Natural pair eligibility

Include if:

-   claim is a numerical financial assertion;
-   source is frozen;
-   candidate evidence is available for annotation;
-   pair is intelligible from supplied material;
-   pair is not a duplicate;
-   no inaccessible external information is required.

## 7.4 Natural exclusions

Only:

``` text
non-numerical
corrupted source
duplicate
corrupted/missing evidence span
unintelligible with supplied context
requires unavailable external information
```

Every exclusion must have a machine-readable reason.

## 7.5 Target

``` text
approximately 60–100 Natural pairs
```

Do not expand because results are weak.

------------------------------------------------------------------------

# 8. Annotation tooling

## 8.1 Export

`export_annotation_forms.py` should generate annotation-ready batches of
approximately 10 examples.

Each item exposes only:

``` text
Claim
Evidence
Optional source context required for interpretation
Decision:
  SUPPORT
  REJECT
  INSUFFICIENT
Reason(s), optional/secondary:
  Entity
  Concept
  Period
  Scope
  Accounting Basis
  Temporal Frame
  Value Role
  Value
  Missing Information
  Other
```

Never expose:

-   FinVerify output;
-   expected perturbation;
-   gold metadata;
-   expected gate;
-   system failure history.

## 8.2 Import

Preserve each annotator response as a separate immutable row:

``` text
annotation_id
example_id
annotator_id_anonymized
decision
reason_fields
timestamp
batch_id
validity_status
```

Never overwrite raw responses.

## 8.3 Gold aggregation

Target:

``` text
>=3 independent valid annotations per Natural example
```

Primary:

``` text
majority vote
```

No majority:

``` text
blinded adjudication
```

Agreement:

``` text
Krippendorff alpha
nominal
3 classes
computed before adjudication
```

Also report raw exact agreement.

Artifact:

``` text
results/annotation_agreement.json
```

------------------------------------------------------------------------

# 9. Metric library

Implement metrics once in `verification/metrics.py`. All experiments
call the same functions.

## 9.1 Primary FVR

For a set of Gold `REJECT` examples:

``` text
FVR =
count(gold == REJECT and status == VERIFIED)
/
count(gold == REJECT)
```

`VERIFIED_WITH_CORRECTION` does not count as raw false verification.

## 9.2 Unsafe Support Rate

``` text
USR =
count(gold in {REJECT, INSUFFICIENT} and status == VERIFIED)
/
count(gold in {REJECT, INSUFFICIENT})
```

## 9.3 Verification Precision

``` text
VP =
count(gold == SUPPORT and status == VERIFIED)
/
count(status == VERIFIED)
```

Return `null`/undefined when denominator = 0.

## 9.4 Verification Recall

``` text
VR =
count(gold == SUPPORT and status == VERIFIED)
/
count(gold == SUPPORT)
```

## 9.5 Raw decision coverage

``` text
Coverage_raw =
count(status in {VERIFIED, REJECTED})
/
N_total
```

## 9.6 Abstention/status reporting

Report separately:

``` text
UNRESOLVED
EVIDENCE_UNAVAILABLE
UNMAPPED
```

and combined abstention.

Do not assume:

``` text
Abstention = 1 - Coverage_raw
```

because `VERIFIED_WITH_CORRECTION` is separately represented.

## 9.7 Strict Attack Rejection

``` text
SAR =
count(gold == REJECT and status == REJECTED)
/
count(gold == REJECT)
```

## 9.8 Safe Non-Verification

``` text
SNVR =
count(gold == REJECT and status != VERIFIED)
/
count(gold == REJECT)
```

## 9.9 Control Retention

``` text
CR =
count(matched_control and gold == SUPPORT and status == VERIFIED)
/
count(matched_control and gold == SUPPORT)
```

## 9.10 Correction Precision

``` text
CP =
count(valid corrected support and status == VERIFIED_WITH_CORRECTION)
/
count(status == VERIFIED_WITH_CORRECTION)
```

Undefined if denominator = 0.

Every metric artifact must contain numerator and denominator, not only
percentages.

------------------------------------------------------------------------

# 10. Statistical library

Implement in `verification/statistics.py`.

## 10.1 Primary cluster bootstrap

Unit:

``` text
source_group_id
```

Replicates:

``` text
10,000
```

Default seed:

``` text
20260806
```

For every replicate:

1.  sample source groups with replacement;
2.  include all examples from selected groups;
3.  compute `FVR_A0`;
4.  compute `FVR_A2`;
5.  compute `delta = FVR_A2 - FVR_A0`.

Report:

``` text
point_estimate
ci_low
ci_high
n_source_groups
n_examples
replicates
seed
```

Primary artifact:

``` text
results/bootstrap_ci.json
```

## 10.2 Secondary intervals

Use source/document cluster bootstrap where examples share a source
unit.

## 10.3 McNemar

Optional sensitivity analysis only. Do not implement a novel
cluster-adjusted variant.

------------------------------------------------------------------------

# 11. E0 --- Extraction Reliability

**Purpose:** Quantify whether frozen 7F can recover the metadata later
used for verification/diagnosis.

**Dataset:** `extraction_eval.jsonl`

**Target size:** approximately 100 real sentences/spans sampled
independently of extraction success.

**Gold fields where applicable:**

``` text
numeric value
entity
concept
period
scope
accounting_basis
temporal_frame
value_role
```

**System:** frozen 7F extraction only.

**No DEV tuning.**

**Outputs:**

``` text
results/extraction_evaluation.csv
results/extraction_evaluation.json
```

**Report:**

-   numeric claim/value P/R/F1;
-   Concept exact canonical accuracy + missing/unmapped;
-   Period structured match + UNKNOWN;
-   Scope accuracy/macro-F1 + UNKNOWN where meaningful;
-   Accounting Basis accuracy/macro-F1 + UNKNOWN;
-   Temporal Frame accuracy/macro-F1 + UNKNOWN;
-   Value Role accuracy/macro-F1 + UNKNOWN;
-   Entity metric appropriate to actual representation;
-   explicitly state if Entity is not independently extracted;
-   pipeline exact-match over an explicitly named field set.

**Failure interpretation:** Extraction failures are results. Do not add
regexes after TEST.

------------------------------------------------------------------------

# 12. E1 --- Concept Numerical Coincidence

**Research question:** Can Concept enforcement distinguish same-number
claims referring to different financial concepts?

**Dataset:** Controlled TEST Concept-shift adversarial pairs + their
matched controls.

**Configurations:**

``` text
A0 = Value
A1 = Value + Concept
```

**Primary adversarial metric:** FVR.

**Utility metrics:**

``` text
SAR
SNVR
CR
VR
status distribution
```

**Required paired output:** per-example A0 and A1 status.

**Artifact:**

``` text
results/concept_challenge.csv
```

**No code changes after observing TEST.**

------------------------------------------------------------------------

# 13. E2 --- Period Numerical Coincidence

**Research question:** Can Period enforcement distinguish same-number
claims referring to incompatible reporting periods?

**Dataset:** Controlled TEST Period-shift adversarial pairs + matched
controls.

**Configurations:**

``` text
A1 = Value + Concept
A2 = Value + Concept + Period
```

A1 is used rather than A0 so the incremental Period effect is isolated
after Concept enforcement.

**Metrics:**

``` text
FVR
SAR
SNVR
CR
VR
status distribution
```

**Artifact:**

``` text
results/period_challenge.csv
```

------------------------------------------------------------------------

# 14. E3 --- Enforced Identity Ablation --- PRIMARY

**Research question:** Does the complete frozen enforced identity
configuration reduce false verification relative to numerical matching?

**Dataset:** Entire Controlled Primary TEST set.

**Configurations:**

``` text
A0 — Numeric
A1 — Numeric + Concept
A2 — Numeric + Concept + Period
```

**Primary comparison:**

``` text
A0 vs A2
```

**Primary outcome:**

``` text
delta_FVR = FVR_A2 - FVR_A0
```

**Primary inference:**

``` text
10,000-replicate source-group bootstrap
95% CI
```

**Secondary metrics:**

``` text
FVR
VP
VR
Coverage_raw
combined abstention
status distribution
SAR
SNVR
CR
```

**Required artifact:**

``` text
results/enforced_identity_ablation.csv
results/enforced_identity_ablation.json
```

Each configuration must be evaluated on identical TEST examples.

**Paper destination:** Main results table.

------------------------------------------------------------------------

# 15. E4 --- Provenance Isolation

**Research question:** How often would collapsing post-hoc correction
into ordinary verification overstate original-output correctness?

**Dataset:** Eligible controlled and/or Natural examples where
correction machinery is applicable. Dataset subset rule must be frozen
before execution and recorded.

**Compare reporting views:**

``` text
Strict provenance:
  VERIFIED
  VERIFIED_WITH_CORRECTION
  other statuses

Collapsed legacy-style operational view:
  VERIFIED_OR_CORRECTED = VERIFIED + VERIFIED_WITH_CORRECTION
```

Do not change actual system outputs.

**Report:**

``` text
raw verified count/rate
verified-with-correction count/rate
correction precision
collapsed apparent support rate
difference between collapsed and raw support rate
```

Where gold labels permit, report original-output correctness separately
from corrected-output success.

**Artifact:**

``` text
results/provenance_evaluation.csv
results/provenance_evaluation.json
```

**Interpretation:** Correction success is not original model
correctness.

------------------------------------------------------------------------

# 16. E5 --- Diagnostic Identity Challenge

**Research question:** Which same-number semantic mismatches remain
failure modes outside the frozen Concept/Period enforcement boundary?

**Dataset:** Controlled Diagnostic TEST.

**Dimensions:**

``` text
entity
scope
accounting_basis
temporal_frame
value_role
```

**System:** frozen final FinVerify configuration only. Do not create
synthetic per-dimension gates.

**Report per dimension:**

``` text
N
FVR
SAR
SNVR
CR for corresponding controls
status distribution
```

Include qualitative failures.

**Artifact:**

``` text
results/controlled_diagnostic.csv
results/controlled_diagnostic_summary.json
```

**Critical interpretation rule:** A poor result is not a bug unless
frozen semantics were implemented incorrectly.

------------------------------------------------------------------------

# 17. E6 --- Natural Financial Claims

**Research question:** What does frozen FinVerify do on naturally
sampled financial claim-evidence pairs?

**Dataset:** adjudicated `natural_test.jsonl`.

**System:** frozen end-to-end FinVerify.

**Report:**

``` text
N
gold label distribution
system status distribution
FVR over REJECT
USR over REJECT + INSUFFICIENT
VP
VR
Coverage_raw
combined abstention
VERIFIED_WITH_CORRECTION rate
bootstrap CIs
```

Every false verification must appear in `natural_errors.csv`.

**Artifacts:**

``` text
results/natural_evaluation.csv
results/natural_evaluation.json
results/natural_errors.csv
```

**No fixes based on these errors.**

------------------------------------------------------------------------

# 18. E7 --- Gold vs Extracted Pipeline Gap

**Research question:** How much of the Concept/Period verification
behavior is lost because of extraction rather than the verification rule
itself?

**Restriction:** Only Concept and Period may be substituted with gold
metadata, and only if the runner can do so without inventing new
verifier behavior.

**Conditions:**

``` text
Gold(C,P)
Extracted(C,P)
```

All other verification semantics remain identical.

**Dataset:** eligible Controlled Primary TEST; Natural TEST may be
secondary if gold C/P labels are reliable.

**Report:**

``` text
FVR_gold
FVR_extracted
delta_pipeline_FVR
CR_gold
CR_extracted
delta_pipeline_CR
status distributions
```

Optional bootstrap intervals may be reported.

**Artifact:**

``` text
results/gold_vs_extracted.csv
results/gold_vs_extracted.json
```

If the frozen architecture cannot validly support the Gold condition,
mark E7 `NOT_RUN_ARCHITECTURAL_CONSTRAINT` rather than hacking around
it.

------------------------------------------------------------------------

# 19. E8 --- Numeric Baseline

E8 is operationally A0 but gets a standalone baseline artifact for
comparison tables.

**Input:** same TEST examples used by the corresponding experiment.

**Rule:** exact frozen FinVerify numerical agreement semantics.

**No learned parameters.**

**Artifact:**

``` text
results/numeric_baseline.json
```

Do not implement a second approximate tolerance function.

------------------------------------------------------------------------

# 20. E9 --- Embedding Similarity Baseline

**Purpose:** Test whether ordinary text-level semantic similarity can
solve the verification task.

**Model:** one fixed sentence-embedding model, exact identifier/revision
frozen before TEST.

**Input:**

``` text
claim.text
evidence.text
```

**Score:**

``` text
cosine_similarity(embedding(claim), embedding(evidence))
```

**Binary target for threshold tuning:**

``` text
SUPPORT
NON_SUPPORT = REJECT + INSUFFICIENT
```

**Threshold selection:** DEV only.

Objective:

``` text
maximize Balanced Accuracy
```

Tie-breaking:

``` text
if multiple thresholds produce identical best Balanced Accuracy,
choose the highest threshold
```

Record:

``` text
tau_dev
DEV objective value
candidate threshold procedure
model/revision
library versions
```

Apply `tau_dev` to TEST without retuning.

**Report:**

``` text
balanced accuracy
precision
recall
FVR on REJECT
confusion matrix
```

Because this baseline does not abstain unless explicitly designed before
freeze, do not fabricate abstention.

**Artifacts:**

``` text
results/embedding_baseline_dev.json
results/embedding_baseline.json
```

------------------------------------------------------------------------

# 21. E10 --- LLM Judge --- OPTIONAL SECONDARY

Decision to include must be frozen before central TEST.

**Prompt intent:**

``` text
Financial claim:
{claim}

Evidence:
{evidence}

Does the supplied evidence independently support the financial claim?

Return exactly one label:
SUPPORT
REJECT
INSUFFICIENT
```

The final exact prompt must be stored as a file and hashed.

Do not enumerate Concept/Period/Scope/etc. in the prompt.

**Settings:**

``` text
temperature = 0 where supported
one primary run per example
no majority-of-N sampling
```

**Parser:**

-   exact normalized label accepted;
-   malformed response -\> frozen `PARSE_ERROR`;
-   do not manually repair TEST outputs.

Map `PARSE_ERROR` separately; do not silently map to a favorable class.

**Artifacts:**

``` text
results/llm_judge.json
results/llm_judge_raw.jsonl
```

Record model/provider/version/date/API parameters.

If omitted, record the reason.

------------------------------------------------------------------------

# 22. E11 --- FinVerifyBench-Numeric Continuity

**Purpose:** Secondary continuity with the existing benchmark.

**Dataset:** existing frozen FinVerifyBench Numeric TEST split only.

**Do not modify existing 500 samples or splits.**

Before running:

1.  hash committed benchmark files;
2.  identify canonical evaluator;
3.  document known generator inconsistency;
4.  document that historical baseline fixtures are synthetic;
5.  do not reuse historical synthetic percentages as empirical results.

Run only reproducible systems/predictions with known provenance.

**Report existing benchmark metrics as implemented by the canonical
evaluator**, plus exact run provenance.

**Artifact:**

``` text
results/numeric_benchmark.json
```

This experiment cannot replace E3 as the paper's central result.

------------------------------------------------------------------------

# 23. Experiment dependency graph

``` text
PHASE 7G
  ↓
CODE FREEZE
  ↓
PROTOCOL FREEZE
  ↓
DATASET BUILDERS + VALIDATORS
  ↓
CONTROLLED DEV/TEST FREEZE
  ↓
NATURAL COLLECTION
  ↓
ANNOTATION + GOLD FREEZE
  ↓
E0 EXTRACTION
  ↓
DEV-ONLY BASELINE TUNING
  ↓
CENTRAL TEST START MARKER
  ↓
E1 CONCEPT
E2 PERIOD
E3 PRIMARY ABLATION
E4 PROVENANCE
E5 DIAGNOSTIC
E6 NATURAL
E7 GOLD-vs-EXTRACTED
E8 NUMERIC BASELINE
E9 EMBEDDING
E10 LLM JUDGE [IF FROZEN IN]
  ↓
STATISTICS
  ↓
E11 NUMERIC CONTINUITY
  ↓
TABLE GENERATION
  ↓
RESULT FREEZE
```

E0 may occur before central TEST because it evaluates a separately
frozen extraction sample and must not be used to modify frozen 7F.

------------------------------------------------------------------------

# 24. Central TEST start marker

Before the first central TEST command, update `freeze_manifest.json`:

``` json
{
  "central_test_started_at": "<ISO-8601 timestamp>"
}
```

Commit or archive the manifest.

From that timestamp onward:

-   no system tuning;
-   no TEST edits;
-   no threshold tuning;
-   no perturbation-rule changes;
-   no annotation-label changes based on system results.

Any validity bug follows Protocol v3's deviation procedure.

------------------------------------------------------------------------

# 25. Standard runner behavior

Every experiment script must support, where applicable:

``` text
--split
--input
--output
--seed
--config
--manifest
```

Every runner must:

1.  refuse TEST execution if freeze requirements are missing;
2.  record Git commit and dirty status;
3.  record input dataset SHA256;
4.  record configuration;
5.  emit per-example results;
6.  emit aggregate results;
7.  exit non-zero on schema/integrity failure;
8.  never mutate input datasets;
9.  never silently drop failed examples.

If an example cannot be processed, emit a row with an explicit
failure/status.

------------------------------------------------------------------------

# 26. Suggested commands

Exact names may change with repository architecture, but the final
README must expose equivalent one-command runs.

``` bash
python scripts/validate_verification_dataset.py \
  --input data/verification/controlled_test.jsonl \
  --output results/dataset_validation.json
```

``` bash
python scripts/run_extraction_evaluation.py \
  --input data/verification/extraction_eval.jsonl \
  --output results/extraction_evaluation.json
```

``` bash
python scripts/run_identity_ablation.py \
  --split test \
  --input data/verification/controlled_test.jsonl \
  --configs A0 A1 A2 \
  --output results/enforced_identity_ablation.json
```

``` bash
python scripts/run_diagnostic_challenge.py \
  --split test \
  --input data/verification/controlled_test.jsonl \
  --output results/controlled_diagnostic_summary.json
```

``` bash
python scripts/run_natural_evaluation.py \
  --input data/verification/natural_test.jsonl \
  --output results/natural_evaluation.json
```

``` bash
python scripts/run_statistics.py \
  --input results/enforced_identity_ablation.csv \
  --cluster source_group_id \
  --bootstrap 10000 \
  --seed 20260806 \
  --output results/bootstrap_ci.json
```

``` bash
python scripts/generate_paper_tables.py \
  --results results/ \
  --output paper/generated/
```

PowerShell equivalents may be documented for Windows.

------------------------------------------------------------------------

# 27. Paper-table contract

`generate_paper_tables.py` must generate numerical cells directly from
frozen artifacts.

## Main table

Rows:

``` text
A0 Numeric
A1 + Concept
A2 + Period
```

Columns at minimum:

``` text
FVR ↓
Verification Precision ↑
Verification Recall ↑
Control Retention ↑
Coverage_raw ↑
Abstention
```

## Controlled dimension table

Rows:

``` text
Concept
Period
Entity
Scope
Accounting Basis
Temporal Frame
Value Role
```

Clearly mark Concept/Period as **enforced primary** and the rest as
**diagnostic**.

## Natural table

Include:

``` text
Gold distribution
Status distribution
FVR
USR
VP
VR
Coverage_raw
Abstention
```

## Extraction table

Only use metrics meaningful for each field.

## Provenance table

Separate:

``` text
VERIFIED
VERIFIED_WITH_CORRECTION
collapsed operational support
correction precision
```

------------------------------------------------------------------------

# 28. Result sanity checks

Before tables are generated, automatically assert:

-   all A0/A1/A2 runs contain identical primary TEST example IDs;
-   no source-group split leakage;
-   metric numerators do not exceed denominators;
-   all status counts sum to N;
-   no duplicate run/example/config rows;
-   no TEST embedding threshold was fit on TEST;
-   bootstrap uses declared source groups;
-   diagnostic rows are not mislabeled as implemented gates;
-   corrected verification is not counted as raw VERIFIED;
-   all result files contain commit/dataset hashes.

Failure blocks table generation.

------------------------------------------------------------------------

# 29. What Codex is allowed to decide

Codex may decide:

-   internal class/function organization;
-   efficient file parsing;
-   test structure;
-   serialization implementation;
-   CLI ergonomics;
-   reuse of existing canonical utilities;
-   minimal architecture needed to avoid duplication.

Codex may **not** decide:

-   scientific labels;
-   metric definitions;
-   identity dimensions;
-   primary comparison;
-   dataset eligibility;
-   DEV/TEST membership after freeze;
-   perturbation semantics;
-   UNKNOWN semantics;
-   numerical tolerance;
-   annotation aggregation;
-   bootstrap unit;
-   embedding threshold objective;
-   whether a poor TEST result should trigger a system fix.

If implementation requires one of these decisions, Codex must stop and
surface the ambiguity.

------------------------------------------------------------------------

# 30. Required tests for experiment infrastructure

At minimum add tests for:

### Schema

-   valid pair accepted;
-   invalid label rejected;
-   invalid split rejected;
-   missing source group rejected.

### Split integrity

-   same source group across DEV/TEST rejected.

### Perturbations

-   value invariant;
-   target dimension changes;
-   non-target primary identity invariant;
-   parent control exists.

### Metrics

-   FVR toy example;
-   VP denominator zero -\> undefined;
-   VR toy example;
-   CR excludes `VERIFIED_WITH_CORRECTION`;
-   SNVR includes abstentions/non-verification;
-   status counts sum correctly.

### Ablations

-   A0 ignores Concept/Period;
-   A1 enforces Concept but not Period;
-   A2 enforces Concept + Period;
-   UNKNOWN cannot become a match.

### Provenance

-   correct raw -\> VERIFIED;
-   wrong raw + valid correction -\> VERIFIED_WITH_CORRECTION;
-   wrong raw + invalid correction -\> not verified;
-   corrected status never counted as raw VERIFIED.

### Bootstrap

-   resamples source groups, not individual rows;
-   deterministic under fixed seed.

### Artifact provenance

-   TEST runner refuses missing freeze manifest;
-   dirty repository is recorded;
-   dataset hash recorded;
-   input file never mutated.

------------------------------------------------------------------------

# 31. Stop conditions

Implementation must stop and ask for a scientific decision if:

-   7G re-audit shows Concept/Period are not actually canonical enforced
    semantics;
-   A0/A1/A2 cannot be constructed without inventing behavior;
-   Gold Concept/Period injection requires modifying verification
    semantics;
-   source grouping cannot be established without ambiguous manual
    decisions;
-   Natural evidence construction requires a new retrieval method not
    frozen in Protocol v3;
-   a proposed diagnostic perturbation necessarily changes multiple
    dimensions and cannot be transparently classified;
-   annotation data do not meet the frozen minimum and the
    deadline/stopping rule has not been defined;
-   historical FinVerifyBench outputs lack executable provenance.

Do not improvise around these blockers.

------------------------------------------------------------------------

# 32. Success criteria for implementation

The experiment infrastructure is complete when:

``` text
[ ] dataset schemas validate
[ ] source-group split leakage test passes
[ ] controlled builder is deterministic
[ ] Natural candidate procedure is reproducible
[ ] annotation export/import works
[ ] raw annotations are immutable
[ ] E0 runner works
[ ] A0/A1/A2 runner works
[ ] E4 provenance runner works
[ ] E5 diagnostic runner works
[ ] E6 Natural runner works
[ ] E7 either runs validly or records architectural non-run
[ ] E8 numeric baseline works
[ ] E9 DEV threshold + frozen TEST works
[ ] E10 optional path is frozen or explicitly omitted
[ ] E11 continuity runner uses only reproducible provenance
[ ] cluster bootstrap works
[ ] all required machine-readable artifacts are generated
[ ] paper tables are generated from artifacts
[ ] result sanity checks pass
[ ] full experiment-infrastructure test suite passes
```

No target accuracy/FVR value is part of success criteria.

------------------------------------------------------------------------

# 33. Final implementation boundary

The intended scientific pipeline is:

``` text
REAL FINANCIAL CLAIM + EVIDENCE
              │
              ▼
       FROZEN EXTRACTION
              │
              ▼
     VALUE / CONCEPT / PERIOD
              │
       ┌──────┴──────┐
       ▼             ▼
   RAW VALUE      CORRECTION
       │             │
       ▼             ▼
   VERIFIED      VERIFIED_WITH_CORRECTION
       │
       ▼
FALSE-VERIFICATION / COVERAGE ANALYSIS
```

The primary experiment tests only the identity constraints actually
enforced by the frozen system:

``` text
A0 = Value
A1 = Value + Concept
A2 = Value + Concept + Period
```

Other financial identity dimensions are deliberately retained as
diagnostic challenges and extraction targets.

The experiment suite must therefore be capable of producing an
uncomfortable result without changing the system.

That is a feature of the study, not a failure of the implementation.

------------------------------------------------------------------------

# 34. Freeze status

**EXPERIMENT_SPEC v1.0 STATUS: FINAL CANDIDATE --- NOT YET
HASH-FROZEN.**

Before freezing:

1.  Phase 7G must be completed and independently re-audited.
2.  Protocol v3 implementation-dependent placeholders must be filled.
3.  Exact embedding model/revision must be selected.
4.  LLM Judge inclusion decision/model must be frozen before central
    TEST.
5.  This specification and Protocol v3 must receive one blocker-only
    methodological review.
6.  Accepted validity-critical corrections must be applied before
    dataset construction.
7.  Record SHA256 and Git commit for both documents.

After that, this file becomes the implementation contract for the
experiment infrastructure.
