# SOURCE ELIGIBILITY AMENDMENT 1

**Amendment identifier:** `SOURCE_ELIGIBILITY_AMENDMENT_1`  
**Parent protocol:** `SOURCE_ELIGIBILITY_v1.md` v1.0  
**Discovery phase:** Phase 9C-F1 blocker traceability audit  
**Status:** pre-outcome amendment draft for adversarial review

This amendment supplements `SOURCE_ELIGIBILITY_v1.md`; it does not rewrite,
replace, or modify that immutable historical document. It resolves exactly the
three implementation ambiguities identified before production eligibility
execution:

1. duplicate-equivalence normalization and comparison;
2. source-group overlap determination;
3. pre-sampling declaration of Controlled challenge dimensions.

No canonical-occurrence rule, corpus-expansion source rule, threshold,
enumeration rule, or verifier rule is amended.

## 1. Information available and information excluded

This amendment is based only on the frozen source protocol, the Phase 9C-F
traceability finding, and the already-frozen experiment design. It does not use
the Run-2 candidate ledger, individual scientific candidates, eligible-pool
counts or composition, FinVerify outputs, model outputs, baseline outputs,
attack success, or any benchmark outcome. No external network, model, LLM, or
fuzzy semantic service is authorized.

The amendment is frozen before production eligibility decisions, eligible-pool
counts, Phase 9D sampling, controlled perturbation generation, and verifier or
model evaluation. Future candidate distributions or experimental performance
must not be used to reinterpret it.

## 2. Amendment A — duplicate-equivalence contract

### 2.1 Preserved source values

The reviewer/source-derived value for every identity dimension is retained
unchanged. A deterministic normalized value is stored separately. Normalized
values are comparison keys only and never replace source wording, evidence, or
reviewer judgments. No fuzzy similarity, external ontology, LLM, or numeric
tolerance is used.

The identity tuple remains exactly the tuple frozen in `SOURCE_ELIGIBILITY_v1.md`
sections 37–40:

```text
Entity, Concept, Period, Scope, Accounting Basis, Temporal Frame,
Value Role, normalized Value
```

### 2.2 Common lexical normalization

For fields represented as text, the deterministic normalizer applies Unicode
NFKC, trims leading/trailing whitespace, collapses internal Unicode whitespace
to one ASCII space, and applies Unicode case-folding. It does not translate,
stem, synonym-expand, remove legal suffixes, or infer a label. The original
value remains available beside the normalized value.

The following explicit-state values are separate comparison states:

```text
UNKNOWN       = conflicting or unresolved source interpretation
UNSPECIFIED   = the source does not state the dimension
NOT_APPLICABLE = the source explicitly states that the dimension does not apply
```

`UNKNOWN` never matches any value, including another `UNKNOWN`.
`UNSPECIFIED` never matches an explicit value or `UNKNOWN`, and two
`UNSPECIFIED` values do not establish duplicate equivalence. `NOT_APPLICABLE`
matches only `NOT_APPLICABLE`. This conservative treatment prevents missing
information from being treated as identity evidence.

### 2.3 Entity

The normalized Entity key is the source-explicit issuer identity supplied by
the canonical source metadata or explicitly resolved from permitted source
context, after common lexical normalization. A source-explicit canonical
issuer identifier may be copied as an exact key. No broad corporate ontology,
alias inference, parent/subsidiary mapping, ticker lookup, or external lookup
is performed. Different issuer keys remain separate even when a human might
consider them related.

### 2.4 Concept

The normalized Concept key is the common-lexically-normalized original source
concept label. No fuzzy matching, embedding similarity, or implementer-created
alias list is permitted. An alias can be used only if it is added to a future
versioned, explicitly frozen alias table before review. In Amendment 1 there is
no additional alias table. Different labels therefore remain separate unless
the source itself provides the same explicit concept label.

### 2.5 Period

An explicitly recoverable period is represented as a structured exact key:

```text
period_kind + normalized fiscal/calendar interval or explicit relative label
             + explicit reporting-event anchor where a relative label is used
```

Quarter/fiscal-year labels, explicit start/end dates, and explicit comparison
period labels retain their source kind and exact components. A relative label
such as “prior quarter” matches another occurrence only when its explicit
reporting-event anchor and relative label are identical. No period is inferred
from neighboring numbers, document order, or arithmetic. Different or
unresolved periods remain separate.

### 2.6 Scope

The normalized Scope key is an exact representation of the explicit source
qualifier: for example, an explicitly stated consolidated/company scope or an
exact normalized segment/business label and path. An absent qualifier is
`UNSPECIFIED`; a conflicting qualifier is `UNKNOWN`. Company and segment
scopes never merge, and different segment labels never merge through semantic
similarity.

### 2.7 Accounting Basis

The normalized Accounting Basis key is the exact source-explicit qualifier,
using stable labels such as `gaap`, `non_gaap`, `reported`, `adjusted`, or
`other:<normalized explicit label>`. No basis is inferred from the numeric
value. Explicit GAAP and non-GAAP/adjusted values remain distinct even when
their numbers are equal.

### 2.8 Temporal Frame

The normalized Temporal Frame key is the exact source-explicit frame:
`actual`, `guidance`, `comparison`, or `other:<normalized explicit label>`.
Historical actual, comparison, and guidance/outlook values never merge merely
because their numbers are equal. An absent or conflicting frame uses the
explicit-state rules above.

### 2.9 Value Role

The normalized Value Role key is the exact source-supported role from the
frozen taxonomy: `current`, `comparison`, `year_over_year_change`,
`sequential_change`, `range_lower`, `range_upper`, `guidance_center`,
`tolerance`, or `financial_change_amount`. A role is not inferred from a
number's position or from verifier behavior. Different roles remain separate.

### 2.10 Normalized Value

Normalized Value is compared as an exact deterministic numeric representation,
including sign and semantic unit. Equivalent explicit scale representations may
map to the same exact base-unit value only through the frozen numeric
normalization contract. The comparison uses exact canonical decimal/rational
components and not binary floating-point equality, tolerance, or closeness.
Percentage, basis-point, currency, ratio, and per-share units remain distinct
unless the source normalization contract explicitly establishes equivalence.
Original text, scale, unit, and precision remain preserved.

### 2.11 Duplicate-equivalence decision

Two occurrences are duplicate-equivalent if and only if:

1. every component of the identity tuple has a determinate comparison value;
2. every normalized component is exactly equal, including normalized Value;
3. source evidence supports that the occurrences represent the same underlying
   financial fact under the frozen identity rules; and
4. neither occurrence has an unresolved or missing identity component that
   would permit a materially different interpretation.

They must remain separate when any component differs; when any component is
`UNKNOWN` or `UNSPECIFIED`; when source precision does not establish the same
fact; when the concepts/roles/scopes/bases/frames differ; or when equality
would require semantic inference, fuzzy matching, numerical closeness, or
researcher arithmetic. `NOT_APPLICABLE` matches only the same explicit state.

Equivalent occurrences receive the same stable fact cluster, and all remain
in the construction ledger. Canonical selection is unchanged and remains the
Section 40 hierarchy of the parent protocol.

## 3. Amendment B — source-group overlap contract

### 3.1 Purpose

The source-group rule prevents leakage and pseudo-independence between
artifacts that are representations of the same issuer reporting event. It is
based on source/event provenance, not eligibility outcomes, candidate counts,
or verifier behavior.

### 3.2 Deterministic event keys

For every source artifact, construct a source-event descriptor from frozen
source metadata and explicit document provenance:

```text
issuer_key
reporting_event_key
reporting_period_coverage
artifact_role
```

`issuer_key` uses the exact source-explicit issuer identity normalization in
section 2.3. `reporting_event_key` is the exact source-explicit release/event
identifier or, where no identifier exists, the exact normalized tuple of
issuer, reporting period/event date, and reporting-event type. No date or event
is guessed from a candidate number or neighboring text. If an issuer or event
cannot be resolved, the descriptor is marked unresolved and does not create an
automatic overlap edge.

### 3.3 Overlap edge

Two artifacts **must** share a source group when either condition holds:

1. they have the same determinate `issuer_key` and the same determinate
   `reporting_event_key`; or
2. their frozen source metadata explicitly identifies them as covering the same
   issuer reporting event or the same reporting-event coverage, even if their
   artifact roles differ (for example, release and presentation for that
   event).

This is the objective meaning of substantial overlap for this amendment:
substantial overlap is established by shared source-explicit reporting-event
identity/coverage, not by a percentage of numbers or an observed candidate
intersection. A shared issuer without a shared event is insufficient. A shared
numeric value without source-explicit event identity is insufficient.

Artifacts **must remain separate** when their determinate issuer differs, when
their determinate reporting event differs, or when overlap would require
inference from candidate contents rather than frozen source/event provenance.
An unresolved event does not justify merging by default; it is recorded for
source-provenance review before a split. No threshold is tuned to the corpus.

### 3.4 Components and group IDs

Create an undirected graph whose vertices are source artifacts and whose edges
are the mandatory overlap edges above. Source groups are the transitive
connected components. Transitivity is required: if A overlaps B and B overlaps
C, all three share a group even when A and C have no direct artifact-role
match.

The deterministic group identifier is:

```text
sg1_ + SHA256("finverify-source-group-v1\n" + sorted member source_ids joined by "\n")
```

Member IDs are sorted lexicographically; the digest is lowercase hexadecimal.
The group manifest records every member's source ID, canonical path, hash,
issuer/event descriptor, edge rationale, protocol/amendment version, and
review provenance. Every source artifact maps to exactly one group. The
manifest is frozen before any DEV/TEST split; no outcome can alter it.

## 4. Amendment C — pre-sampling Controlled challenge declaration

### 4.1 Frozen challengeable set

Before production parent eligibility is evaluated, the challengeable identity
dimensions are frozen as:

```text
concept
period
entity
scope
accounting_basis
temporal_frame
value_role
```

This set is directly supported by the frozen experiment design: Concept and
Period are the primary controlled perturbations; Entity, Scope, Accounting
Basis, Temporal Frame, and Value Role are diagnostic perturbations. The source
protocol sections 45–47 authorize these additional dimensions when explicitly
recoverable.

`value` is not a challengeable identity dimension: it remains invariant in a
controlled pair. Raw/corrected provenance is a separate experiment and is not
a controlled identity shift. No additional dimension may be added by an
implementer.

### 4.2 Parent eligibility before Phase 9D

Controlled-parent eligibility is evaluated after Natural eligibility and
deduplication but before parent sampling or perturbation generation. Every
parent must have recoverable Value, Entity, Concept, and Period, as required by
the parent protocol. The parent record also receives a deterministic
`challengeable_dimensions` subset containing exactly those dimensions from the
frozen set that are explicitly recoverable for that parent under the source
evidence rules.

The parent is `controlled_parent_eligible` only if it is Natural-eligible,
canonical for its fact cluster, satisfies the required Value/Entity/Concept/
Period fields, and has at least one explicitly recoverable dimension in the
frozen challengeable set that supports a financially meaningful authorized
challenge. A parent need not recover every challengeable dimension; a later
sampled parent may be challenged only on one of its recorded dimensions.

Phase 9D may choose among the already authorized dimensions in a parent's
`challengeable_dimensions` set, subject to its separately frozen sampling
procedure. Phase 9D may not add a new challenge dimension, change the frozen
set, or retroactively change parent eligibility. Which dimension is actually
challenged for a sampled parent is distinct from whether that dimension is
challengeable in the complete parent pool.

No parent decision uses perturbation success, FinVerify behavior, model
behavior, or the identity of future sampled parents.

## 5. Unaffected provisions and expansion boundary

The following remain exactly as frozen in `SOURCE_ELIGIBILITY_v1.md`:

- canonical occurrence selection and its Section 40 hierarchy;
- eligibility thresholds and target ranges;
- candidate enumeration, candidate IDs, and numeric grammar;
- Natural representation and evidence principles except for the comparison
  mechanics above;
- information barriers and no-silent-deletion requirements;
- Phase 9D sampling and all verifier/model execution rules.

Eligibility computes and reports the existing triggers only:

```text
N_unique_natural_eligible < 60
N_controlled_parent_eligible < 15
```

Actual expansion-source acquisition and ordering remain a separate subsequent
procedure. This amendment does not select or prioritize expansion sources.

## 6. Provenance and effective relationship

The parent protocol remains immutable. This amendment is a versioned,
pre-outcome supplement effective only for implementation and production
eligibility review after its own freeze and adversarial approval. It must be
recorded with the eligibility ledger, source-group manifest, duplicate-cluster
records, and Controlled-parent pool freeze. Its amendment identifier and Git
commit are part of construction provenance.

Every normative addition above is within exactly one authorized category:

- **A:** deterministic identity normalization/comparison;
- **B:** deterministic source-event overlap/group construction;
- **C:** pre-sampling challenge-dimension declaration and parent eligibility.

No other scientific policy area is modified. No implementation code is created
by this amendment.

**Parent protocol modified:** NO  
**Implementation specification modified:** NO  
**Scientific candidate ledger inspected:** NO  
**Eligibility outcomes inspected:** NO  
**FinVerify/model/baseline/verifier outcomes used:** NO  
**Additional scientific policy areas modified:** 0  
**Remaining unresolved ambiguities:** 0
