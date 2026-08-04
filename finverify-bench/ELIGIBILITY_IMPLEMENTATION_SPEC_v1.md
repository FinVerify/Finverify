# FinVerifyBench Eligibility Implementation Specification

**Document:** `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md`  
**Phase:** 9C-F  
**Status:** specification-only implementation contract  
**Governing policy:** `SOURCE_ELIGIBILITY_v1.md` v1.0  
**Reserved Phase 9D seed:** `20260804`

This document operationalizes the frozen source-eligibility policy. It does
not amend that policy, the experiment specification, the enumerator, or the
verifier. If a conflict is found, the earlier frozen governing specification
controls and this document must be amended before implementation.

## 1. Purpose and scope

The construction sequence is:

```text
frozen Run-2 raw enumeration
  -> verifier-blind eligibility review and adjudication
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

Eligibility code and review interfaces must not import, invoke, or read
FinVerify predictions/status/confidence/trust, verifier or experiment outputs,
baseline/model outputs, attack success, aggregate performance, effect size, or
statistical significance. No candidate decision may use expected verifier
behavior.

Development and tests use synthetic fixtures only. Production review against
Run 2 is a separate default-deny operation requiring explicit authorization
after implementation freeze and adversarial review. The authorization records
the implementation commit and validated Run-2 hash. A normal flag, environment
variable, or alternate path must not bypass the guard.

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
review_workflow_status: UNREVIEWED | INDEPENDENT_REVIEW | ADJUDICATION | FINALIZED
review_method
reviewer_id
review_timestamp
adjudication_id
```

`EXCLUDED` requires one primary reason; all applicable additional reasons are
retained. `ELIGIBLE` has no exclusion reason. Reviewer timestamps are audit
metadata only and never affect identity, ordering, grouping, or hashes.

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

## 9. Duplicate equivalence

Duplicate resolution occurs only after eligibility and adjudication. Two
occurrences are equivalent only when they represent the same fact using:

```text
Entity, Concept, Period, Scope, Accounting Basis, Temporal Frame,
Value Role, normalized Value
```

Equal numbers alone do not imply duplication. Different periods, scopes,
concepts, GAAP/non-GAAP bases, actual/guidance frames, or roles remain
distinct. Equivalent display scales may be merged only when source identity
and reporting precision establish the same fact; FinVerify tolerance is never
the sole criterion.

All equivalent occurrences retain a stable `fact_cluster_id` in the complete
ledger. Exactly one is `canonical_occurrence: true`. Selection is mechanical:

1. most direct authoritative financial reporting context;
2. formal financial-statement table over repeated narrative restatement;
3. lower frozen `source_id`;
4. earliest deterministic locator in the same artifact.

Unresolved precision or identity requires adjudication, not outcome-based
choice. Non-canonical provenance remains preserved.

## 10. Source groups

`source_group_id` is a leakage-relevant cluster of artifacts with substantial
overlapping facts from one issuer and reporting event. Release/presentation,
release/supplement, release/transcript, and overlapping Q4/annual materials
are grouped when their coverage materially overlaps. Grouping uses source
provenance and reporting coverage, never verifier behavior.

Before any split, `source_group_manifest.json` maps every artifact to exactly
one stable group and records member IDs/hashes, reporting event, rationale,
review/adjudication provenance, and protocol version. Duplicate fact clusters
must not cross groups. If source/fact overlap would split one cluster, merge
groups before splitting. This phase does not assign DEV/TEST or sample.

## 11. Controlled-parent eligibility

No perturbation is generated here. A Controlled parent must first be an
eligible, deduplicated, source-backed canonical occurrence. The ledger keeps
separate fields `natural_eligible` and `controlled_parent_eligible`. The
latter is true only when:

1. `natural_eligible` is true;
2. the occurrence is canonical for its eligible fact cluster;
3. Value, Entity, Concept, and Period are independently recoverable;
4. evidence supports the unperturbed parent; and
5. any dimension intended for a later challenge is explicitly recoverable.

The last condition is conditional on a later declared challenge; it does not
turn diagnostic dimensions into universal gates. Parent eligibility precedes
parent sampling and derivative generation and never depends on attack success
or difficulty. All qualifying unique candidates form the complete
`controlled_parent_pool`; no smaller interesting subset is created.

## 12. Review ledger and outputs

`eligibility_ledger.jsonl` is UTF-8 JSONL, one object per line, and retains
every raw occurrence exactly once. It copies all raw fields and adds:

```text
eligibility_status, primary_exclusion_code, secondary_exclusion_codes,
ambiguity_status, review_workflow_status, review_method, reviewer_id,
review_timestamp, adjudication_id, entity, concept, period, scope,
accounting_basis, temporal_frame, value_role, evidence, fact_cluster_id,
canonical_occurrence, source_group_id, natural_eligible,
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

After complete verifier-blind review, adjudication, and deduplication, compute:

```text
N_unique_natural_eligible
N_controlled_parent_eligible
```

The trigger is exactly:

```text
N_unique_natural_eligible < 60 OR N_controlled_parent_eligible < 15
```

If triggered, report it. Do not relax rules, resample, cherry-pick exclusions,
inspect FinVerify, or silently expand. Expansion preserves the original
corpus, adds authoritative hashed sources, assigns groups, runs the same
extractor, applies the same policy, and reassesses the same trigger. If both
thresholds are satisfied, expansion is prohibited for that benchmark version.

The 60–80 Natural and approximately 15–25 Controlled-parent targets are
sampling/design targets, not eligibility criteria.

## 14. Freeze, tests, and change control

The eligibility freeze records SHA-256 and Git provenance for the raw ledger,
eligibility/adjudication ledger, source-group manifest, Natural pool,
Controlled-parent pool, and summary. Existing frozen manifests cannot be
silently overwritten; an amendment requires a new version and change record.

Future implementation tests use synthetic fixtures only and cover: exact input
hash/freeze validation; malformed JSONL/schema/offset rejection; Run-1
rejection; deterministic exclusions and precedence; semantic-review routing;
no FinVerify/model/network dependency; default-deny production access;
duplicate equivalence and canonical choice; source-group isolation;
Controlled-parent eligibility; evidence construction; deterministic
serialization and repeated byte identity; expansion triggers; no silent
deletion; and funnel accounting. Tests must not inspect the Run-2 ledger.

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
| 37–43 | duplicate identity, clusters, canonical choice, source groups | A/B |
| 44–47 | Natural and Controlled-parent boundaries | A |
| 48–54 | targets, triggers, seed, Phase 9D boundary | A |
| 57–64 | hashes, no deletion, funnel, change control, freeze boundary | A/B |
| paths, encodings, ordering, serialization | neutral execution mechanics | B |

- [x] Derived from `SOURCE_ELIGIBILITY_v1.md` without changing policy.
- [x] Verifier-blind; no Run-2 candidates were inspected for rule design.
- [x] Preserves raw IDs, spans, offsets, hashes, and provenance.
- [x] Defines evidence, atomicity, exclusions, duplicates, groups, and pools.
- [x] Keeps diagnostic/extracted-only dimensions from becoming capability gates.
- [x] Defers sampling and perturbation generation to Phase 9D/later phases.
- [x] Defines expansion triggers without pool-size tuning.
- [x] Defines deterministic behavior and human-review provenance.
- [x] Establishes synthetic-only tests and default-deny production authorization.

**Pre-implementation amendments required:** 0  
**Unresolved ambiguities:** 0  
**Scientific ledger inspected during specification work:** NO
