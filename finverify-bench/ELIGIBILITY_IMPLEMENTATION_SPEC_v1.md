# FinVerifyBench Eligibility Implementation Specification

**Document:** `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md`  
**Phase:** 9C-F  
**Status:** specification-only implementation contract  
**Governing policy:** `SOURCE_ELIGIBILITY_v1.md` v1.0, supplemented by
`SOURCE_ELIGIBILITY_AMENDMENT_1.md` and `SOURCE_ELIGIBILITY_AMENDMENT_2.md`
**Reserved Phase 9D seed:** `20260804`

This document operationalizes the jointly applicable frozen sources
`SOURCE_ELIGIBILITY_v1.md`, `SOURCE_ELIGIBILITY_AMENDMENT_1.md`, and
`SOURCE_ELIGIBILITY_AMENDMENT_2.md`. The parent protocol and both amendments
remain historically immutable. Amendment 1 governs duplicate equivalence,
source grouping, and pre-sampling Controlled challenge dimensions. Amendment 2
governs only the Step 4 eligibility-determination mechanism: frozen LLM
ensemble annotation plus blinded human audit. No amendment changes the
enumerator, eligibility rubric, thresholds, or verifier.

## 1. Purpose and scope

The construction sequence is:

```text
frozen Run-2 raw enumeration
  -> frozen LLM-ensemble eligibility annotation
  -> blinded stratified human audit and adjudication
  -> duplicate-equivalence clustering
  -> source-group assignment
  -> unique eligible Natural and Controlled-parent pool freeze
  -> Phase 9D sampling freeze
  -> FinVerify execution
```

Eligibility determines source validity. It does not determine sample
membership, run FinVerify, generate controlled perturbations, perform DEV/TEST
assignment, or perform Phase 9D sampling. The raw occurrence ledger remains
immutable and auditable. Excluded and duplicate occurrences remain in the
construction ledger.

Every rule here is either **A**, directly required by
`SOURCE_ELIGIBILITY_v1.md`; **B**, neutral implementation mechanics; or **C**,
`REQUIRES PRE-IMPLEMENTATION AMENDMENT` because it would change policy. No rule
uses Run-2 distributions, desired pool size, verifier behavior, or candidate
difficulty.

## 2. Canonical input contract

The only authorized scientific input is:

```text
data/verification/enumeration/raw_candidate_ledger_run2.jsonl
```

Its frozen identity is:

| Field | Required value |
|---|---|
| enumerator commit | `252afe742cecae4f53a5f92d65fa35f25d2538bb` |
| candidate count | `14118` |
| parse-issue count | `0` |
| ledger SHA-256 | `ec9532fa60225be63d5446ca2137b260255d97a74354a25e82f1b3ecd62a0093` |
| ledger byte size | `64871267` |
| freeze metadata | `data/verification/enumeration/SECOND_RUN_FREEZE.json` |
| parse issues | `data/verification/enumeration/parse_issues_run2.jsonl` |
| parse-issue SHA-256 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

The freeze metadata must identify Phase 9C-A3, the post-A2 canonical raw
enumeration, the enumerator commit, all hashes/counts above, and that it
supersedes `FIRST_RUN_FREEZE.json` for scientific use. Run 1 is preserved
defect provenance and is never a fallback.

An explicit supplied path is accepted only when its bytes hash to the exact
Run-2 hash and its freeze metadata, enumerator commit, parse-issue ledger,
schema, and provenance all validate. The implementation must reject any
mismatch as a hard failure. It must not normalize before hashing or silently
fall back to another ledger.

Every JSONL record must contain the frozen raw fields:

```text
candidate_id, source_id, source_sha256, relative_path, source_format,
source_locator, raw_source_span, target_raw_text, target_start, target_end,
numeric_kind, normalized_value, normalized_unit, scale, parser_metadata,
enumeration_status
```

Strings, numeric types, offsets, finite values, and metadata must validate;
`raw_source_span[target_start:target_end]` must equal `target_raw_text`; and
candidate IDs must be unique. Invalid JSONL, duplicate IDs, invalid offsets,
or schema failure is a hard input failure. Raw fields, IDs, hashes, spans, and
provenance are copied, never rewritten.

## 3. Information barrier and production guard

Eligibility code, LLM annotation prompts, and audit interfaces must not import, invoke, or read
FinVerify predictions/status/confidence/trust, verifier or experiment outputs,
baseline/model outputs, attack success, aggregate performance, effect size, or
statistical significance. No candidate decision may use expected verifier
behavior.

Development and tests use synthetic fixtures only. Production annotation
against Run 2 is a separate default-deny operation requiring explicit
authorization after implementation freeze and adversarial review. Release of
the audit manifest and start of human audit are a second, separate
default-deny gate. The two gates must not be conflated. Both record the
implementation commit and validated input/configuration hashes. A normal flag,
environment variable, fallback, or alternate path must not bypass either gate.

The annotation model-family roster must be disjoint, at model-family
granularity, from every later FinVerifyBench evaluation-target and LLM-baseline
roster. Both rosters are frozen before annotation or evaluation begins.

## 4. Candidate review states

Each raw occurrence has exactly one scientific state:

```text
ELIGIBLE
EXCLUDED
ADJUDICATION_REQUIRED
```

These are the exact states permitted by the source protocol. The last is not
an eligible pool member until resolved. No occurrence silently disappears.

Separate workflow fields are non-scientific metadata:

```text
eligibility_status
primary_exclusion_code
secondary_exclusion_codes
ambiguity_status: NONE | IDENTITY_AMBIGUOUS | ADJUDICATION_REQUIRED | RESOLVED
review_workflow_status: LLM_ANNOTATED | AUDIT_PENDING | HUMAN_AUDITED | ADJUDICATION | FINALIZED
review_method
reviewer_id
review_timestamp
adjudication_id
```

`EXCLUDED` requires one primary reason; all applicable additional reasons are
retained. `ELIGIBLE` has no exclusion reason. Reviewer timestamps are audit
metadata only and never affect identity, ordering, grouping, or hashes.

Under Amendment 2, `eligibility_status` for the full ledger is initially
produced by the frozen LLM ensemble. The permitted workflow values are
extended as follows without changing the three scientific terminal states:

```text
review_method: LLM_ENSEMBLE_ANNOTATION | HUMAN_AUDIT | ADJUDICATION
audit_status: NOT_SELECTED | SELECTED | DOUBLE_CODED | ADJUDICATED
agreement_tier: unanimous | majority | split
label_source: llm_only | llm_audited_agree | llm_human_consensus | llm_human_adjudicated
```

The LLM annotation, human-audit judgments, and adjudication values are
separate provenance fields. An LLM-only occurrence is never described as
human-reviewed. A human audit does not silently overwrite the LLM annotation;
the final `eligibility_status` source is recorded by `label_source`.

## 5. Deterministic rules and reason codes

Mechanical validation may reject malformed input but is not semantic
eligibility. A source occurrence with untrustworthy structural recovery may be
reviewed as `EXC_PARSE_FAILURE`; a lost required table structure may be
`EXC_TABLE_CONTEXT_LOST`. Offset or raw-span invariant failure is a hard input
failure, not a repaired candidate.

The frozen reason-code vocabulary is:

```text
EXC_NON_FINANCIAL
EXC_DERIVED_ONLY
EXC_ENTITY_AMBIGUOUS
EXC_CONCEPT_AMBIGUOUS
EXC_PERIOD_AMBIGUOUS
EXC_SCOPE_AMBIGUOUS
EXC_BASIS_AMBIGUOUS
EXC_TEMPORAL_AMBIGUOUS
EXC_VALUE_ROLE_AMBIGUOUS
EXC_EVIDENCE_INSUFFICIENT
EXC_TABLE_CONTEXT_LOST
EXC_PARSE_FAILURE
EXC_OUT_OF_SCOPE
```

Primary precedence is exactly:

1. `EXC_NON_FINANCIAL`;
2. `EXC_DERIVED_ONLY`;
3. `EXC_OUT_OF_SCOPE`;
4. identity ambiguity;
5. `EXC_EVIDENCE_INSUFFICIENT`;
6. `EXC_TABLE_CONTEXT_LOST`;
7. `EXC_PARSE_FAILURE`.

Within identity ambiguity, the neutral stable order is Entity, Concept,
Period, Scope, Accounting Basis, Temporal Frame, Value Role; all applicable
codes remain secondary. Duplicate status is never an exclusion reason. No
frequency, span-length, numeric-kind, source-distribution, or Run-2 heuristic
is authorized.

## 6. Semantic eligibility review

Amendment 2 applies the following frozen rubric twice: first by the locked
LLM ensemble to all 14,118 occurrences, and then by blinded human auditors for
the deterministic audit sample. The task question and checklist below must be
copied verbatim into every annotator prompt and human-audit interface; they
must not be paraphrased.

The reviewer answers:

> Does this explicitly enumerated occurrence represent an eligible quantitative
> financial fact, with sufficient permitted source context to resolve the
> relevant identity and evidence, without researcher-derived arithmetic?

The reviewer separately checks explicit presence of the value; financial versus
purely operational scope; Entity, Concept, and materially required Period;
recoverable Scope, Accounting Basis, Temporal Frame, and Value Role; evidence
sufficiency; and absence of researcher-derived meaning.

Eligible categories are revenue/sales, income/earnings, expenses, assets,
liabilities, equity, cash, cash flow/free cash flow, margins, EPS/per-share,
financial growth/change percentages, financial ratios, basis-point changes in
financial metrics, guidance, and financially relevant share quantities.

Purely operational quantities such as deliveries, production, shipments,
subscribers, customers, users, employees, capacity, and non-monetary volumes
are `EXC_NON_FINANCIAL`. Monetary or financial-ratio claims about an
operational segment may remain eligible. Dates, labels, page numbers,
identifiers, footnotes, telephone numbers, addresses, and section numbers are
excluded unless part of an eligible financial claim.

The frozen verifier enforces Value, Concept, and Period, with provenance
separate. Entity, Scope, Accounting Basis, Temporal Frame, and Value Role are
diagnostic/extracted-only. A source-valid claim is not excluded because the
verifier does not enforce one of those dimensions; it is excluded only when
source identity is genuinely unresolved under the frozen evidence rules.

Target values must be explicit in canonical source text. Normalization is
allowed; arithmetic is not. Ranges yield separate explicit occurrences. No
midpoint, difference, growth rate, margin, average, range endpoint, or other
unstated value is created. Multiple targets in one span receive separate
records with distinct offsets. Comparison, sequential, year-over-year,
guidance, tolerance, per-share, percentage, basis-point, and ratio roles are
preserved and not silently relabeled.

## 7. Review context and evidence

The reviewer may see only the deterministic package: raw source span, target
text and offsets, source ID/hash/format/locator, parser metadata, applicable
heading, document issuer/reporting-event metadata, and deterministic table or
transcript structure. Additional source context is retrieved only by the
recorded locator and frozen structural representation, not by arbitrary
browsing of unrelated material or outcomes.

For prose, evidence is the complete sentence containing the target, nearest
applicable heading when available, and document-level issuer/reporting-event
metadata. One neighboring sentence is allowed only when a logged dependency
such as “this quarter”, “the segment”, or “compared with the prior period” is
unresolved by the target sentence, heading, or document metadata.

For tables, retain title, unit/scale, row path, column path, target cell,
applicable basis label, and directly required footnote marker/text. A naked
cell is insufficient when structure is needed; rows and columns are not
flattened. For transcripts, retain target utterance, speaker identity/role when
available, nearest event/section context, and document issuer/reporting
metadata. Neighboring utterances use the same dependency rule.

The evidence object records type, verbatim evidence text/span, target, locator,
structural context, and dependency log. Evidence is frozen before system
execution and is the same for systems in the same experiment unless a separate
context-variation specification is frozen.

## 8. Reviewer and adjudication provenance

For ambiguity-sensitive cases, Reviewer A and Reviewer B independently decide
without seeing one another or any system outcome. Disagreement becomes
`ADJUDICATION_REQUIRED`; adjudication resolves it without FinVerify, baseline,
model, or attack information. Two agreeing reviewers may establish ambiguity;
disagreement alone does not prove ambiguity. No agreement-coefficient
threshold is an eligibility rule. Blinded reviewer codes, method, rationale,
adjudication ID, and final decision are retained.

## 8A. Amendment 2 annotation and human-audit protocol

### 8A.1 Locked ensemble configuration

Before any Run-2 occurrence is processed, commit the exact bytes of
`annotation_config.lock.json` and its lowercase SHA-256. The lock is immutable
after annotation begins and contains an exact model-family and model-version
roster with `k >= 3` annotators; the full verbatim prompt for every annotator,
including the Section 6 question/checklist and Section 7 evidence boundary;
identical fixed decoding and structured-output settings; output schema,
aggregation rule, timeout, retry count, refusal/malformed-output fallback; the
disjoint evaluation/baseline model-family roster; configuration version; and
implementation commit. No annotator may receive context beyond Section 7 or
experimental outcomes.

### 8A.2 Corpus-wide aggregation

Run the locked ensemble once, in one non-interactive batch, over all 14,118
occurrences. For `k` annotators, k-of-k agreement yields the label and
`agreement_tier: unanimous`; (k-1)-of-k agreement yields the label and
`agreement_tier: majority`. Any other vote pattern yields
`agreement_tier: split` and `eligibility_status: ADJUDICATION_REQUIRED`.
Refusal, timeout, malformed output, or exhausted retry is logged and follows
the fixed fallback; it is never defaulted to either substantive label. For an
`EXCLUDED` result, exclusion codes use only agreeing exclusion annotators and
the unchanged Section 5 precedence; code disagreement routes to
`ADJUDICATION_REQUIRED`.

### 8A.3 Sequencing and audit strata

The mandatory sequence is: freeze/hash the annotation configuration; run and
freeze/hash the full LLM annotation ledger; derive and freeze/hash the audit
manifest; then begin human audit. Audit strata are derived only from frozen
annotation output:

```text
A = unanimous/majority ELIGIBLE
B = unanimous/majority EXCLUDED
C = split / ADJUDICATION_REQUIRED
```

Lock `N_A`, `N_B`, and `N_C` in the manifest header. Allocation may depend
only on these population sizes, never on audit results or experimental
outcomes.

### 8A.4 Deterministic n=100 audit sampling

The guaranteed human-audit floor is exactly `n=100`; the floor, allocation
rule, and stopping rule are frozen before the audit manifest is generated.
The manifest is generated only after the full annotation ledger is frozen.
Additional volunteer reviews are allowed only under an exogenous fixed
calendar/logistics stopping rule, never based on agreement, error, or kappa.

The Phase 9D seed `20260804` is not reused. Derive:

```text
audit_seed_hex = SHA256(UTF8("finverify-phase9c-audit-v1\n" +
  raw_ledger_sha256_lower + "\n" + annotation_config_sha256_lower)).hexdigest()
```

For candidate ID `c`, order within its stratum by ascending
`SHA256(UTF8("finverify-phase9c-audit-rank-v1\n" + audit_seed_hex + "\n" + c)).hexdigest()`,
breaking ties by UTF-8 candidate ID. Allocate the 100 cases proportionally
using floor plus largest remainder, lexical tie order `A < B < C`, and the
specified capacity redistribution when a stratum is exhausted. Each case has
`pi_i = n_h / N_h`, or zero only when its stratum receives no slots.

`audit_manifest_v1.csv` is generated exactly once before human review and
contains every candidate ID, stratum, `pi_i`, deterministic rank, selection
flag, both input hashes, derived seed, and generation timestamp. Selection and
allocation are never redrawn.

### 8A.5 Human audit and double coding

Auditors receive only the Section 7 evidence package and Section 6 rubric.
They are blind to model identities, individual votes, LLM aggregate,
agreement tier/stratum, LLM rationale, and experimental outcomes. Case order is
randomized independently of stratum.

Exactly 20 of the 100 selected cases are double-coded, not additional cases.
Allocate them proportionally across selected strata using the same floor,
largest-remainder, `A < B < C`, and capacity rules. Within each stratum rank
using `SHA256(UTF8("finverify-phase9c-double-code-v1\n" + audit_seed_hex +
"\n" + candidate_id)).hexdigest()` with the same candidate-ID tie-break.

If the first human judgment diverges from the LLM label, a second independent
blind human review is required, even outside the fixed 20-case subset. If two
human judgments agree, that consensus is binding and is not overridden by an
unblinded adjudicator. If they disagree, an adjudicator sees the complete
record, issues a written timestamped justification, and supplies
`adjudicated_label`; conflicts of interest are disclosed per case. Human-human
kappa uses the fixed double-coded subset and never changes corpus-wide LLM
labels.

### 8A.6 Weighted audit statistics

For stratum `h` in `{A,B,C}`, define `W_h = N_h / 14118` and let `p_h` be
the within-stratum agreement rate between the frozen LLM label and binding
human-audit label. Report:

```text
p_weighted = sum_h(W_h * p_h)
```

Report each `p_h`, the weighted estimate, and the following deterministic
stratified finite-population normal-approximation 95% confidence interval. Let
`N = 14118`, `N_h` be the frozen population size of stratum `h`, `n_h` its
audited sample size, and `a_h` the number of audited cases whose binding human
label agrees with the frozen LLM label. For every non-empty stratum, require
`0 < n_h <= N_h` and define:

```text
p_h = a_h / n_h
W_h = N_h / N
p_hat = sum_h(W_h * p_h)
f_h = n_h / N_h
V_hat = sum_h(W_h^2 * (1 - f_h) * p_h * (1 - p_h) / (n_h - 1))
SE = sqrt(V_hat)
z_95 = 1.959963984540054
CI_lower = max(0, p_hat - z_95 * SE)
CI_upper = min(1, p_hat + z_95 * SE)
```

The sums include every non-empty stratum, including a stratum whose sample
proportion is zero or one. Use binary64 IEEE-754 arithmetic, evaluate each
sum in lexicographic stratum order `A`, `B`, `C`, and round only displayed
values to six decimal places; retain the unrounded binary64 values in the
freeze artifact. If any non-empty stratum has `n_h < 20`, or if a required
stratum has `n_h = 0`, set the interval status to
`UNDERPOWERED` / `NOT_ESTIMATED` and do not report `V_hat`, `SE`, or bounds;
descriptive `p_h` and `p_hat` may still be retained. If all inferential strata
meet the threshold, zero variance is valid: a point estimate of 0 yields
`[0, 0]`, and a point estimate of 1 yields `[1, 1]`. Always clamp bounds to
the closed unit interval as shown. These are the only confidence intervals
authorized; no bootstrap or alternative critical value is permitted. Also
report Cohen's kappa overall and per stratum and human-human kappa from the
20 double-coded cases. These statistics measure annotation/audit agreement,
not FinVerify performance, and do not alter any LLM label. A sensitivity
analysis of plausible eligibility-label error is required before experimental
conclusions.

### 8A.7 Label provenance and final freeze

The full ledger preserves the LLM result for all occurrences. Additive fields
are:

```text
llm_annotation, agreement_tier, human_audit_label, human_audit_label_2,
adjudicated_label, label_source, audit_stratum, inclusion_probability,
annotation_config_hash, audit_manifest_id, audit_status
```

`label_source` is one of `llm_only`, `llm_audited_agree`,
`llm_human_consensus`, or `llm_human_adjudicated`. `eligibility_status` is the
LLM value for the first two, binding human consensus for the third, and the
adjudicated value for the fourth. No field is silently overwritten. Reviewer
identity, exclusion reasons, adjudication status, and timestamps apply to the
human-audit layer, not to `llm_annotation`.

The final freeze hashes and records Git provenance for:

```text
annotation_config.lock.json
llm_annotation_ledger.jsonl
audit_manifest_v1.csv
human_audit_ledger.jsonl
eligibility_ledger.jsonl
source_group_manifest.json
eligible_natural_pool.jsonl
controlled_parent_pool.jsonl
eligibility_summary.json
```

`ELIGIBILITY_FREEZE.json` records every artifact hash, Run-2 ledger hash,
annotation-config hash, audit-manifest hash, audit seed, ordered annotation
and audit-gate timestamps, implementation commit, model-family disjointness
attestation, audit size, double-coded count, weighted statistics, and the
statement that the corpus is LLM-annotated with a blinded human audit rather
than fully human-reviewed. The annotation gate freezes before manifest
generation; the audit-release gate freezes before human review.

## 9. Duplicate equivalence

Duplicate resolution occurs only after eligibility and adjudication. The
normalized comparison tuple is exactly:

```text
Entity, Concept, Period, Scope, Accounting Basis, Temporal Frame,
Value Role, normalized Value
```

The source-derived value is retained unchanged beside its normalized value.
For textual fields, normalization is Unicode NFKC, trim, collapse internal
Unicode whitespace to one ASCII space, and Unicode case-fold. No stemming,
synonym expansion, legal-suffix removal, ontology, fuzzy matching, alias
inference, embedding, LLM, external lookup, or verifier information is used.

The comparison states are `UNKNOWN`, `UNSPECIFIED`, and `NOT_APPLICABLE`.
`UNKNOWN` never matches any value, including another `UNKNOWN`.
`UNSPECIFIED` never matches an explicit value, `UNKNOWN`, or another
`UNSPECIFIED`. `NOT_APPLICABLE` matches only `NOT_APPLICABLE`. This is the
conservative Amendment 1 contract for missing or unresolved identity.

The dimension-specific normalized values are:

- **Entity:** source-explicit issuer identity from canonical metadata or
  permitted source context; no corporate ontology or parent/subsidiary aliasing.
- **Concept:** exact normalized source concept label. Amendment 1 freezes no
  alias table; different labels remain separate.
- **Period:** exact period kind and explicit fiscal/calendar interval or
  relative label plus its explicit reporting-event anchor. No inference from
  neighboring numbers.
- **Scope:** exact explicit company/consolidated or segment/business qualifier
  and path. Missing is `UNSPECIFIED`; company and segment scopes do not merge.
- **Accounting Basis:** exact explicit label such as `gaap`, `non_gaap`,
  `reported`, `adjusted`, or `other:<label>`; it is never inferred.
- **Temporal Frame:** exact explicit `actual`, `guidance`, `comparison`, or
  `other:<label>`; actual, comparison, and guidance do not merge.
- **Value Role:** exact source-supported role from the frozen taxonomy:
  `current`, `comparison`, `year_over_year_change`, `sequential_change`,
  `range_lower`, `range_upper`, `guidance_center`, `tolerance`, or
  `financial_change_amount`.
- **Normalized Value:** exact canonical decimal/rational value including sign
  and semantic unit. Equivalent explicit scales may share an exact base-unit
  value; binary floating-point equality, numeric closeness, and verifier
  tolerance are not used. Original scale, unit, precision, and text remain.

Two occurrences are duplicate-equivalent if and only if every tuple component
has a determinate comparison value, every normalized component is exactly
equal, source evidence supports the same underlying financial fact, and no
materially different interpretation remains. They remain separate if any
component differs; if any component is `UNKNOWN` or `UNSPECIFIED`; if source
precision does not establish the same fact; or if equality requires semantic
inference, fuzzy matching, numerical closeness, or researcher arithmetic.

All equivalent occurrences retain a stable `fact_cluster_id`; none is deleted.
Exactly one canonical occurrence is selected using the unchanged Section 40
hierarchy, applied mechanically in order and using later criteria only as
tie-breakers:

1. most direct authoritative financial reporting context;
2. formal financial-statement table over repeated narrative restatement;
3. lower frozen `source_id`;
4. earliest deterministic locator in the same artifact.

Non-canonical provenance remains preserved. No new canonical preference is
introduced here.

## 10. Source groups

`source_group_id` is a leakage-relevant cluster of artifacts representing the
same issuer reporting event. Amendment 1 defines substantial overlap by
source-explicit event identity/coverage, not by candidate frequency, numeric
intersection, percentage threshold, eligibility outcome, or verifier behavior.

For each artifact, construct an event descriptor from frozen source metadata:

```text
issuer_key
reporting_event_key
reporting_period_coverage
artifact_role
```

`issuer_key` uses the exact source-explicit Entity normalization in Section 9.
`reporting_event_key` is the exact source-explicit release/event identifier or,
if absent, the exact normalized tuple of issuer, reporting period/event date,
and reporting-event type. No date or event is inferred from candidate numbers.
An unresolved issuer or event creates no automatic overlap edge.

Two artifacts must share a group when they have the same determinate issuer and
reporting-event keys, or when frozen source metadata explicitly identifies them
as covering the same issuer reporting event/coverage despite different artifact
roles or formats. They must remain separate when issuer or event differs, or
when overlap would require inference from candidate contents. An unresolved
event is recorded for source-provenance review and is not merged by default.

Build an undirected graph of artifacts using those mandatory edges. The groups
are its transitive connected components: if A overlaps B and B overlaps C, all
three share a group. The deterministic identifier is:

```text
sg1_ + SHA256("finverify-source-group-v1\n" +
              sorted member source_ids joined by "\n")
```

The digest is lowercase hexadecimal. `source_group_manifest.json` records
every member's source ID, canonical path/hash, issuer/event descriptor, edge
rationale, protocol/amendment version, and review provenance. Every artifact
maps to exactly one group. Duplicate fact clusters must not cross groups; if
source/fact overlap would split one cluster, merge before splitting. This
phase does not assign DEV/TEST or sample.

## 11. Controlled-parent eligibility

No perturbation is generated here. Before production parent eligibility is
evaluated, Amendment 1 freezes the complete challengeable identity-dimension
set:

```text
concept, period, entity, scope, accounting_basis, temporal_frame, value_role
```

Concept and Period are primary perturbations. Entity, Scope, Accounting Basis,
Temporal Frame, and Value Role are diagnostic perturbations. This set is
supported by the frozen experiment design and source protocol. Value is not a
challengeable identity shift: it remains invariant in a controlled pair.
Raw/corrected provenance is separate and is not a controlled identity shift.
No additional dimension may be added here.

A Controlled parent must first be an eligible, deduplicated, source-backed
canonical occurrence. The ledger keeps separate `natural_eligible`,
`controlled_parent_eligible`, and `challengeable_dimensions` fields. The last
is the deterministic subset of the frozen seven dimensions explicitly
recoverable for that parent under the source evidence rules.

`controlled_parent_eligible` is true only when:

1. `natural_eligible` is true;
2. the occurrence is canonical for its eligible fact cluster;
3. Value, Entity, Concept, and Period are independently recoverable;
4. evidence supports the unperturbed parent; and
5. at least one frozen challengeable dimension is explicitly recoverable and
   supports a financially meaningful authorized challenge.

A parent need not recover every challengeable dimension. Phase 9D may choose
only among the already-authorized dimensions in that parent's recorded subset;
the dimension actually selected for a sampled parent is distinct from the
dimension being challengeable in the complete parent pool. Phase 9D may not
add a dimension or retroactively change parent eligibility. Eligibility is
decided before parent sampling and perturbation generation and never depends
on perturbation success, FinVerify behavior, model behavior, or future sample
identity. All qualifying unique candidates form the complete
`controlled_parent_pool`.

## 12. Review ledger and outputs

`eligibility_ledger.jsonl` is UTF-8 JSONL, one object per line, and retains
every raw occurrence exactly once. It copies all raw fields and adds:

```text
eligibility_status, primary_exclusion_code, secondary_exclusion_codes,
ambiguity_status, review_workflow_status, review_method, reviewer_id,
review_timestamp, adjudication_id, llm_annotation, agreement_tier,
human_audit_label, human_audit_label_2, adjudicated_label, label_source,
audit_stratum, audit_status, inclusion_probability, annotation_config_hash,
audit_manifest_id, entity, concept, period, scope,
accounting_basis, temporal_frame, value_role,
entity_normalized, concept_normalized, period_normalized, scope_normalized,
accounting_basis_normalized, temporal_frame_normalized, value_role_normalized,
normalized_value_key, evidence, fact_cluster_id, canonical_occurrence,
source_group_id, challengeable_dimensions, natural_eligible,
controlled_parent_eligible, protocol_version
```

Non-applicable fields use stable `null`, `[]`, or empty-object encodings; they
are not omitted to hide a decision. Original source wording and raw fields are
never overwritten. `eligible_natural_pool.jsonl` contains canonical final
Natural-eligible facts. `controlled_parent_pool.jsonl` contains canonical
Controlled-parent-eligible facts. These are derived views, not replacements.

The frozen companion artifacts are:

```text
source_group_manifest.json
eligibility_summary.json
ELIGIBILITY_FREEZE.json
```

The summary reports raw occurrences, exclusion classes, parse failures,
eligible pre-deduplication occurrences, duplicates, unique eligible facts,
Controlled-parent facts, and later sample counts. It contains no outcomes.

Serialization is deterministic UTF-8 JSONL with stable field order, compact
separators, no NaN/Infinity, and a final newline. Output order is the tuple
`(source_id, source_locator, target_start, target_end, target_raw_text,
candidate_id)`. Reviewer timestamps and machine paths do not enter identity,
ordering, grouping, or hashes.

## 13. Pool freeze and expansion

After frozen full-corpus LLM annotation, required blinded audit/adjudication,
and deterministic deduplication, compute:

```text
N_unique_natural_eligible
N_controlled_parent_eligible
```

The trigger is exactly:

```text
N_unique_natural_eligible < 60 OR N_controlled_parent_eligible < 15
```

If triggered, report corpus expansion required. Do not relax eligibility,
resample, cherry-pick excluded records, select expansion sources, acquire
sources automatically, inspect FinVerify, or perform Phase 9D sampling.
Expansion-source acquisition and ordering remain a separately frozen
subsequent procedure. If both thresholds are satisfied, expansion is
prohibited for that benchmark version.

The 60–80 Natural and approximately 15–25 Controlled-parent targets are
sampling/design targets, not eligibility criteria.

## 14. Freeze, tests, and change control

The eligibility freeze records SHA-256 and Git provenance for the raw ledger,
`annotation_config.lock.json`, `llm_annotation_ledger.jsonl`,
`audit_manifest_v1.csv`, `human_audit_ledger.jsonl`, eligibility/adjudication
ledger, source-group manifest, Natural pool, Controlled-parent pool, and
summary. It also records the annotation-gate and audit-release gate
timestamps, audit seed and size, double-coded count, weighted audit
statistics, model-family disjointness attestation, and the statement that the
corpus is LLM-annotated with a blinded audit rather than fully human-reviewed.
Existing frozen manifests cannot be silently overwritten; an amendment
requires a new version and change record.

Future implementation tests use synthetic fixtures only and cover: exact input
hash/freeze validation; malformed JSONL/schema/offset rejection; Run-1
rejection; deterministic exclusions and precedence; semantic-review routing;
no FinVerify/model/network dependency; default-deny production access;
deterministic serialization and repeated byte identity; expansion triggers; no
silent deletion; and funnel accounting. Tests must not inspect the Run-2 ledger.

Amendment 1 behavior must be tested directly. Duplicate fixtures cover lexical
case/whitespace normalization; different Entity labels remaining separate;
equal numeric values with different Concepts remaining separate; different
Periods; consolidated versus segment Scope; GAAP versus non-GAAP; `UNKNOWN`,
`UNSPECIFIED`, and `NOT_APPLICABLE` semantics; exact normalized-value
comparison; and repeated equivalent fact clustering without deletion.

Source-group fixtures cover same issuer plus same event; different issuers;
different events; one event represented by multiple artifact roles/formats;
explicit amended/restated event relationships; transitive grouping; and
deterministic `source_group_id` construction.

Controlled-parent fixtures cover required Value/Entity/Concept/Period;
recoverable and non-recoverable challenge dimensions; multiple recoverable
dimensions; a recoverable dimension not ultimately sampled; and parent
eligibility independent of Phase 9D selection or any outcome. No perturbation
is generated by these eligibility tests.

Amendment 2 behavior must also be tested with synthetic records only: lock-file
schema, exact prompt/config hash, at least three disjoint model families,
fixed decoding and schema; unanimous, majority, split, EXCLUDED-code
disagreement, retry exhaustion, and no-default aggregation; ordered
annotation and audit-release gates; deterministic A/B/C stratum allocation,
inclusion probabilities, rank ordering, and the audit seed; exactly 100 audit
slots and exactly 20 double-coded slots; blind exported columns and private
mapping restoration; divergence-triggered second review and adjudication;
label-source provenance; weighted statistics and confidence-interval method;
and complete final-freeze artifact hashing/no-overwrite behavior. These tests
must not call FinVerify, a verifier, a model service, or inspect any scientific
ledger.

An implementation defect is failure to execute a frozen rule, such as accepting
the wrong hash, losing provenance, nondeterministic serialization, silent
deletion, invalid reason codes, or outcome use. It must be documented,
synthetically regression-tested, and reviewed. An undesirable pool distribution
is not an implementation defect and cannot justify changing policy.

Any ambiguity not resolvable by the frozen protocol, neutral mechanics, or
reviewer/adjudication provenance is explicitly:

**REQUIRES PRE-IMPLEMENTATION AMENDMENT**

No such ambiguity is silently resolved here. Amendments increment the version,
describe affected stages, preserve this specification, and rerun affected
construction decisions consistently.

## 15. Clause-by-clause comparison and freeze checklist

| Source sections | Translation | Class |
|---|---|---|
| 1–8, 55–56 | phase order, raw provenance, information barrier | A/B |
| 9–14, 26 | atomicity, explicit values, normalization, no derivation | A |
| 15–25 | financial scope, identity, diagnostic-only dimensions, roles | A |
| 27–36 | evidence, review states, adjudication, reason codes | A/B |
| 37–43 + Amendment 1 A/B | duplicate identity, clusters, canonical choice, source groups | A/B |
| 44–47 + Amendment 1 C | Natural and Controlled-parent boundaries | A |
| 48–54 | targets, triggers, seed, Phase 9D boundary | A |
| 57–64 | hashes, no deletion, funnel, change control, freeze boundary | A/B |
| paths, encodings, ordering, serialization | neutral execution mechanics | B |

Amendment 2 is additionally incorporated by Sections 8A and 12–14 of this
specification: the frozen ensemble, two default-deny gates, blinded A/B/C audit,
20 double-coded cases, weighted reporting, provenance, and final artifact
freeze are implementation requirements. Amendment 2 changes only the parent
Step 4 mechanism and does not alter enumeration, duplicate/source-group rules,
Controlled-parent rules, verifier behavior, or Phase 9D.

- [x] Derived from `SOURCE_ELIGIBILITY_v1.md` without changing policy.
- [x] Jointly governed by `SOURCE_ELIGIBILITY_v1.md`, Amendment 1, and Amendment 2.
- [x] Verifier-blind; no Run-2 candidates were inspected for rule design.
- [x] Preserves raw IDs, spans, offsets, hashes, and provenance.
- [x] Defines evidence, atomicity, exclusions, duplicates, groups, and pools.
- [x] Keeps diagnostic/extracted-only dimensions from becoming capability gates.
- [x] Defers sampling and perturbation generation to Phase 9D/later phases.
- [x] Defines expansion triggers without pool-size tuning.
- [x] Defines deterministic ensemble aggregation, blinded audit/adjudication, weighted statistics, and provenance.
- [x] Keeps the full corpus explicitly LLM-annotated rather than describing it as fully human-reviewed.
- [x] Freezes the annotation configuration, annotation ledger, audit manifest, human-audit ledger, and final artifact hashes in order.
- [x] Establishes synthetic-only tests and default-deny production authorization.

**Pre-implementation amendments required:** 0  
**Unresolved ambiguities:** 0  
**Scientific ledger inspected during specification work:** NO
