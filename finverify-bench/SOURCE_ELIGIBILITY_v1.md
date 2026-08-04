# FinVerifyBench Verification Track
# Source and Candidate Eligibility Protocol

**Document:** `SOURCE_ELIGIBILITY_v1.md`  
**Version:** 1.0  
**Phase:** 9C — Source and Candidate Eligibility Freeze  
**Status:** FINAL FREEZE CANDIDATE  
**Sampling seed reserved:** `20260804`

---

# 1. Purpose

This document defines the source-to-candidate construction rules for the
FinVerifyBench Verification Track.

It freezes:

- the candidate enumeration universe;
- quantitative occurrence extraction principles;
- Natural candidate representation;
- claim atomicity;
- evidence construction;
- financial identity requirements;
- financial/operational scope;
- eligibility and exclusion rules;
- ambiguity handling;
- duplicate equivalence;
- canonical occurrence selection;
- source grouping;
- Controlled-parent eligibility;
- corpus-expansion triggers;
- information barriers;
- candidate-ledger provenance;
- the boundary between eligibility freeze and later sampling freeze.

The purpose is to prevent post-hoc benchmark construction.

Candidate eligibility MUST be determined independently of:

- FinVerify predictions;
- FinVerify verification status;
- FinVerify confidence or trust scores;
- whether FinVerify succeeds or fails;
- whether a controlled perturbation succeeds;
- baseline outputs;
- model outputs;
- desired benchmark accuracy;
- desired effect size;
- desired statistical significance;
- desired paper conclusions.

The governing principle is:

> Source validity determines benchmark eligibility.
> Verifier behavior determines experimental results.

These stages MUST remain separate.

---

# 2. Frozen Upstream Components

This protocol operates downstream of previously frozen research components.

Relevant upstream artifacts include:

- `PROTOCOL.md`
- `EXPERIMENT_SPEC_v1.md`
- Phase 7H verifier freeze
- Phase 8 verification infrastructure
- Phase 9B primary-source corpus freeze

Phase 9B corpus freeze commit:

`e21f436cb191ca22f1795fc4503407941245bd5d`

Phase 9B acquisition commit:

`e01860c3380c53d2e1a2bbc20f3356176dcf7084`

Canonical source manifest:

`data/verification/source_manifest.json`

Phase 9B freeze report:

`PHASE9B_CORPUS_FREEZE_REPORT.md`

The Phase 9B corpus contains:

- 6 companies;
- 12 authoritative source artifacts;
- 2 artifacts per company.

Companies:

- Apple Inc. (AAPL)
- The Goldman Sachs Group, Inc. (GS)
- JPMorgan Chase & Co. (JPM)
- Microsoft Corporation (MSFT)
- NVIDIA Corporation (NVDA)
- Tesla, Inc. (TSLA)

This protocol does NOT modify those source artifacts.

If this document conflicts with a previously frozen governing scientific
protocol, the earlier frozen protocol takes precedence until the conflict is
explicitly documented and resolved.

---

# 3. Dataset Validity Is Independent of Verifier Capability

Dataset eligibility MUST NOT be restricted to identity dimensions currently
enforced by FinVerify.

The frozen verifier currently enforces:

- Value
- Concept
- Period

Value provenance is enforced separately through the frozen raw/corrected
verification semantics.

The following dimensions are currently diagnostic/extracted-only:

- Entity
- Scope
- Accounting Basis
- Temporal Frame
- Value Role

A scientifically valid source claim MUST NOT be excluded merely because the
current verifier does not enforce one of these dimensions.

For example, otherwise valid claims may include:

- segment-level revenue;
- non-GAAP EPS;
- forward guidance;
- comparison-period values;
- scope-sensitive metrics.

Such candidates may expose limitations of the frozen verifier.

That is a scientific result, not an eligibility defect.

---

# 4. Enumeration Architecture

Scientific candidate construction MUST begin with deterministic, verifier-blind
enumeration.

The required order is:

1. frozen source corpus;
2. deterministic quantitative occurrence extraction;
3. immutable raw occurrence ledger;
4. human eligibility review;
5. eligibility/adjudication freeze;
6. duplicate resolution;
7. unique eligible candidate pool freeze;
8. Phase 9D pre-outcome sampling freeze;
9. FinVerify execution.

FinVerify MUST NOT be executed on scientific candidates before Steps 1–8 are
complete.

Manual browsing of source documents for the purpose of selectively adding
"interesting" candidates outside the enumeration procedure is prohibited.

---

# 5. Enumeration Universe

The enumeration universe is the complete canonical Phase 9B source corpus.

However, exhaustive manual reading is NOT the mechanism used to define the
initial candidate universe.

Instead, a deterministic broad-recall extractor MUST enumerate quantitative
occurrences from machine-readable representations of the canonical artifacts.

The extractor should intentionally prioritize recall over precision.

It is acceptable for the raw ledger to contain later-ineligible occurrences.

Examples include:

- dates;
- operational counts;
- page-related numbers;
- non-financial percentages.

These occurrences must be rejected through explicit eligibility rules rather
than silently omitted through subjective manual scanning.

No source artifact, section, page, table, or prose region may be manually
excluded from the enumeration universe merely because it is difficult,
lengthy, or inconvenient.

---

# 6. Deterministic Candidate Extractor

Candidate enumeration MUST be implemented through a version-controlled
extractor.

Expected implementation location:

`scripts/enumerate_verification_candidates.py`

The extractor MUST operate independently of FinVerify.

The extractor MUST NOT call:

- the FinVerify verifier;
- model APIs;
- LLMs;
- baseline systems;
- experiment result files.

The extractor may identify broad quantitative forms including:

- currency-denominated values;
- percentages;
- basis points;
- EPS/per-share numeric forms;
- financial ratios;
- explicit share quantities potentially relevant to financial claims.

The extractor MAY initially capture non-financial occurrences.

Eligibility is decided later.

The exact extractor implementation, version, dependencies, and tests MUST be
committed before its output becomes the scientific raw candidate ledger.

---

# 7. Artifact Parsing

Canonical source bytes remain the provenance authority.

For enumeration, deterministic parsing may convert:

- HTML;
- MHTML;
- PDF

into machine-readable structural representations.

Parsing MUST preserve enough provenance to trace every occurrence back to the
canonical artifact.

Where available, provenance should include:

- `source_id`;
- canonical source SHA-256;
- document-relative locator;
- page number for PDF;
- section or heading path;
- table identifier;
- row/column context;
- character/text offset or equivalent deterministic locator.

Parsed intermediate representations MUST NOT replace the canonical source
artifacts.

If an artifact or region cannot be parsed reliably, the failure must be logged.

It must not be silently skipped.

A deterministic documented recovery procedure may then be used without
consulting verifier outputs.

---

# 8. Raw Occurrence Ledger

The first scientific enumeration artifact is the:

`raw_candidate_ledger`

Each detected quantitative occurrence receives a stable `candidate_id`.

Candidate IDs MUST be assigned before:

- eligibility decisions;
- duplicate removal;
- DEV/TEST assignment;
- FinVerify execution.

Candidate IDs MUST NOT be renumbered because an occurrence is later excluded.

At minimum, each raw occurrence should preserve:

- `candidate_id`;
- `source_id`;
- source SHA-256;
- source locator;
- raw source span;
- target numeric occurrence;
- raw numeric representation;
- normalized numeric representation where applicable;
- structural context available from parsing;
- enumeration status.

FinVerify outputs MUST NOT be present in this ledger.

---

# 9. Unit of Enumeration

The fundamental enumeration unit is a:

**targeted explicit quantitative occurrence representing a potential financial
fact.**

A sentence, table row, paragraph, or utterance may contain multiple numeric
occurrences.

Each target occurrence receives its own candidate record.

Example:

> Revenue was $39.3 billion, up 12% sequentially and 78% year over year.

This produces three raw target occurrences:

1. `$39.3 billion`
2. `12%`
3. `78%`

All three may share the same raw source span.

They remain separate candidate records because they represent different
potential financial facts.

---

# 10. Natural Claim Representation

Natural examples MUST preserve naturally occurring source language.

The Natural track MUST NOT use manually rewritten claim sentences.

For each Natural candidate:

`raw_claim_text`

must be a verbatim source span containing the target numerical occurrence.

Researchers MUST NOT manually add:

- entity;
- concept;
- period;
- scope;
- accounting basis;
- temporal frame;
- value role;

to make the claim easier to interpret.

Researchers MUST NOT stylistically rewrite the source claim.

Deterministic whitespace/encoding normalization needed for machine processing
may be stored separately, but the original source text and provenance must be
preserved.

---

# 11. Targeted Atomicity

Natural atomicity is established through the target occurrence, not through
manual rewriting.

For a source span:

> Revenue was $39.3 billion, up 12% sequentially and 78% year over year.

three candidates may share identical `raw_claim_text`, while storing different:

- `target_value`;
- `target_offset`;
- `value_role`;
- financial identity metadata.

This preserves natural source language while making the evaluated quantitative
fact explicit.

The target occurrence MUST be identifiable deterministically within the raw
source span.

---

# 12. Explicit-Value Requirement

For the Natural track, the target numerical value MUST be explicitly present in
the canonical source material.

Source:

> Revenue increased from $10B to $12B.

Potential explicit candidates include:

- `$10B`
- `$12B`

The researcher MUST NOT introduce:

- `20% growth`

unless `20%` is explicitly stated in eligible source material.

This prevents researcher-derived arithmetic from becoming source ground truth.

---

# 13. Derived Values

Researcher-derived values are excluded from the Natural track.

Examples include:

- calculated growth rates;
- calculated differences;
- calculated margins;
- calculated averages;
- synthetic guidance midpoints;
- calculated range endpoints;
- conversions requiring substantive financial assumptions.

Simple representation normalization is NOT derivation.

Example:

`$39.3 billion`

to:

`39,300,000,000`

is normalization.

Example:

`$10B → $12B therefore 20% growth`

is derivation.

---

# 14. Numerical Normalization

The raw textual representation MUST always be preserved.

A normalized numerical representation may additionally be stored.

Normalization MUST preserve:

- sign;
- scale;
- unit;
- percentage interpretation;
- basis-point interpretation;
- per-share interpretation.

Normalization MUST NOT change financial meaning.

Equivalent representations such as:

`$39.3B`

and:

`$39,300M`

may normalize to the same base value while retaining their original source
representations.

---

# 15. Financial Eligibility Boundary

The Verification Track is restricted to quantitative financial claims.

Eligible categories include:

- revenue and sales;
- income and earnings;
- expenses;
- assets;
- liabilities;
- equity;
- cash and cash equivalents;
- cash flow;
- free cash flow;
- margins;
- EPS/per-share financial values;
- financial growth/change percentages;
- financial ratios;
- basis-point changes in financial metrics;
- financial guidance;
- financial share quantities directly relevant to per-share or capital
  structure claims.

The numerical form alone does NOT determine eligibility.

A percentage is eligible only when it represents an eligible financial fact.

---

# 16. Operational Metrics

Purely operational quantities are outside the Verification Track.

Examples normally excluded include:

- vehicle delivery counts;
- physical production volumes;
- shipment counts;
- subscriber counts;
- customer counts;
- user counts;
- employee headcounts;
- physical capacity measures;
- non-monetary operational volumes.

Their presence inside an earnings release does not make them financial claims.

A monetary or financial-ratio claim involving an operational business segment
may still be eligible.

Example:

`Automotive revenue = $X`

may be eligible.

`Vehicles delivered = X`

is not.

---

# 17. Other Non-Financial Numbers

The following are also excluded unless they form part of an eligible financial
claim:

- page numbers;
- dates used only as dates;
- years used only as labels;
- document identifiers;
- footnote numbers;
- telephone numbers;
- addresses;
- section numbering.

Such occurrences may appear in the raw ledger and receive an explicit
exclusion code.

---

# 18. Financial Identity

An eligible candidate must contain enough authoritative source context for a
competent financial reader to resolve the target financial fact.

The following dimensions must be recorded where recoverable:

- Entity
- Concept
- Period
- Scope
- Accounting Basis
- Temporal Frame
- Value Role

Eligibility is based on human/source interpretability under this protocol, not
on FinVerify's ability to extract the field.

---

# 19. Entity

The reporting entity must be recoverable from:

- the claim span;
- structural context;
- document metadata;
- unambiguous document-level context.

The company name need not appear in every individual sentence.

A candidate is excluded for entity ambiguity only when the relevant reporting
entity cannot be resolved from the permitted source context.

FinVerify failure to extract Entity is NOT an entity-ambiguity criterion.

---

# 20. Concept

The financial concept represented by the target value must be recoverable with
reasonable specificity from the permitted source context.

Examples include:

- Revenue
- Net Income
- Diluted EPS
- Gross Margin
- Operating Income
- Free Cash Flow
- Assets Under Management
- Segment Revenue

Concept eligibility is broader than the current FinVerify concept registry.

A source-valid concept MUST NOT be excluded because FinVerify cannot map it.

Original source terminology must be preserved.

Canonical concept mappings, where used, must be stored separately.

---

# 21. Period

The reporting period must be recoverable when period identity is material.

Period information may come from deterministic structural context including:

- claim text;
- table column header;
- section heading;
- document reporting context.

Examples include:

- Q4 FY2025;
- FY2024;
- quarter ended January 26, 2025;
- previous quarter;
- year-ago quarter.

A candidate is excluded when multiple materially different periods remain
plausible after applying the permitted context rules.

Period MUST NOT be guessed from neighboring numbers.

---

# 22. Scope

Both company-level and segment/business-level financial claims may be eligible.

Examples include:

- consolidated revenue;
- Data Center revenue;
- FICC revenue;
- Automotive revenue;
- investment banking fees.

Scope must be preserved where recoverable.

A segment claim MUST NOT be converted into a company-level claim.

A candidate is excluded for scope ambiguity only when materially different
financial interpretations remain possible after applying the permitted
evidence rules.

FinVerify's current lack of scope enforcement is NOT grounds for exclusion.

---

# 23. Accounting Basis

Both GAAP and non-GAAP claims may be eligible.

Examples include:

- GAAP diluted EPS;
- non-GAAP diluted EPS;
- reported expense;
- adjusted expense.

Accounting basis must be recorded where explicitly or structurally
recoverable.

GAAP and non-GAAP values are distinct financial facts even if their numerical
values happen to be equal.

A candidate is excluded for basis ambiguity only when the financial meaning
cannot be resolved from the permitted source context.

FinVerify failure to extract basis is NOT an exclusion criterion.

---

# 24. Temporal Frame

Historical/actual and forward-looking financial claims may both be eligible.

Temporal frames include:

- actual;
- guidance/outlook;
- comparison;
- other explicitly defined forward-looking financial statements.

Guidance MUST NOT be represented as historical actual performance.

Temporal frame must be recorded where recoverable.

---

# 25. Value Role

The role of each target value must be preserved.

Possible roles include:

- current;
- comparison;
- year-over-year change;
- sequential change;
- range lower bound;
- range upper bound;
- guidance center;
- tolerance;
- financial change amount.

A comparison value MUST NOT silently become a current-period value.

The role taxonomy may be extended only through documented pre-outcome schema
revision.

---

# 26. Guidance

Explicit financial guidance may be eligible.

Example:

> Revenue is expected to be $43.0 billion, plus or minus 2%.

Potential explicit target occurrences include:

- `$43.0 billion` with role `guidance_center`;
- `2%` with role `tolerance`.

The researcher MUST NOT calculate synthetic lower or upper endpoints.

Example:

> Revenue is expected to be between $73.7B and $74.8B.

Potential target occurrences include:

- `$73.7B` with role `range_lower`;
- `$74.8B` with role `range_upper`.

A midpoint MUST NOT be created unless explicitly stated in the source.

Normalized ranges must preserve explicit lower and upper bounds separately.

---

# 27. Evidence Construction Principle

Evidence construction MUST be deterministic and verifier-blind.

The previous discretionary standard:

"minimal but sufficient"

is NOT sufficient by itself.

Evidence must instead follow structural rules defined below.

Evidence MUST NOT be expanded or reduced after observing FinVerify or baseline
behavior.

---

# 28. Prose Evidence

For a prose candidate, the canonical evidence package consists of:

1. the complete sentence containing the target occurrence;
2. the nearest applicable section/subsection heading, when structurally
   available;
3. document-level reporting identity metadata required to establish issuer and
   reporting event.

A neighboring prose sentence is NOT automatically included.

It may be included only when a deterministic dependency is recorded because
the target sentence contains an explicit unresolved reference whose financial
identity depends on that immediately adjacent sentence.

Examples include:

- "this quarter";
- "the segment";
- "compared with the prior period";

where the required referent is not available from the target sentence,
structural heading, or document metadata.

Any dependency-based neighboring-sentence inclusion must be logged before
verifier execution.

---

# 29. Table Evidence

For a table candidate, the evidence package must preserve the structural path
needed to identify the target cell.

At minimum, where available:

1. table title;
2. unit/scale label;
3. row label/path;
4. column label/path;
5. target cell;
6. directly applicable accounting-basis label;
7. directly applicable footnote marker/text only when required to interpret
   the target fact.

A naked table cell is never sufficient evidence when identity depends on table
structure.

Tables MUST NOT be flattened in a way that destroys row/column identity.

---

# 30. Transcript Evidence

For transcript candidates, the evidence package consists of:

1. target utterance/sentence containing the numerical occurrence;
2. speaker identity/role when structurally available;
3. nearest applicable transcript section/event context;
4. document-level issuer/reporting-event metadata.

Additional neighboring utterances may be included only under the same explicit
dependency rule used for prose.

---

# 31. Evidence Freeze

The evidence representation supplied to scientific systems MUST be frozen
before system execution.

FinVerify and competing verification baselines must receive the same
evaluation evidence representation for the same candidate unless a separately
frozen experiment explicitly studies context variation.

Human annotation interfaces may hide internal metadata for blinding purposes,
but the authoritative evidence provenance must remain unchanged.

No system-specific evidence editing is permitted.

---

# 32. Eligibility Review

The deterministic extractor defines the raw occurrence universe.

Human review determines whether each occurrence satisfies the frozen financial
eligibility rules.

Reviewers MUST NOT inspect FinVerify or baseline outcomes.

Each raw occurrence must end as either:

- `ELIGIBLE`;
- `EXCLUDED`;
- `ADJUDICATION_REQUIRED`.

No occurrence may silently disappear.

---

# 33. Ambiguity Review

Ambiguity is a property of the source-backed financial identity, not a property
of FinVerify behavior.

For identity-sensitive exclusions, reviewers must apply the same permitted
source context defined in this protocol.

For candidates where ambiguity remains genuinely judgment-dependent:

1. Reviewer A records an independent decision.
2. Reviewer B records an independent decision.
3. disagreement is marked `ADJUDICATION_REQUIRED`;
4. adjudication resolves the final eligibility decision without access to
   FinVerify outcomes.

Two reviewers agreeing that a candidate is ambiguous is valid.

Two reviewers disagreeing does not itself prove that the source is ambiguous.

No mandatory agreement coefficient threshold determines candidate validity.

Agreement statistics may be reported separately where appropriate.

---

# 34. Exclusion Codes

Every excluded occurrence must receive a primary exclusion code.

Permitted primary codes include:

`EXC_NON_FINANCIAL`

Target occurrence is not an eligible quantitative financial fact.

`EXC_DERIVED_ONLY`

Candidate would require researcher-derived arithmetic not explicitly stated in
the source.

`EXC_ENTITY_AMBIGUOUS`

Relevant reporting entity cannot be resolved.

`EXC_CONCEPT_AMBIGUOUS`

Financial concept cannot be resolved.

`EXC_PERIOD_AMBIGUOUS`

Material reporting period cannot be resolved.

`EXC_SCOPE_AMBIGUOUS`

Material financial scope cannot be resolved.

`EXC_BASIS_AMBIGUOUS`

Material accounting basis cannot be resolved.

`EXC_TEMPORAL_AMBIGUOUS`

Actual/guidance/comparison frame cannot be resolved.

`EXC_VALUE_ROLE_AMBIGUOUS`

Target numerical role cannot be resolved.

`EXC_EVIDENCE_INSUFFICIENT`

Authoritative source material does not contain enough permitted context to
establish the target fact.

`EXC_TABLE_CONTEXT_LOST`

Required table structure cannot be reliably recovered.

`EXC_PARSE_FAILURE`

The canonical source occurrence exists but deterministic parsing/recovery
cannot preserve sufficient trustworthy structure.

`EXC_OUT_OF_SCOPE`

Occurrence falls outside the frozen financial verification task definition.

Duplicate status is handled separately and is NOT itself a financial
eligibility failure.

---

# 35. Multiple Exclusion Reasons

Where multiple exclusion conditions apply:

- one `primary_exclusion_code` must be recorded;
- all additional applicable reasons may be stored in
  `secondary_exclusion_codes`.

Primary exclusion priority is:

1. `EXC_NON_FINANCIAL`
2. `EXC_DERIVED_ONLY`
3. `EXC_OUT_OF_SCOPE`
4. identity ambiguity codes
5. `EXC_EVIDENCE_INSUFFICIENT`
6. `EXC_TABLE_CONTEXT_LOST`
7. `EXC_PARSE_FAILURE`

Within the identity-ambiguity category, all applicable ambiguous dimensions
must be recorded rather than hiding additional ambiguity.

---

# 36. Forbidden Exclusion Reasons

The following are NEVER valid exclusion reasons:

- FinVerify got the example wrong;
- FinVerify could not map the concept;
- FinVerify returned UNMAPPED;
- FinVerify returned UNRESOLVED;
- FinVerify confidence was low;
- a baseline performed unexpectedly;
- the example lowers benchmark accuracy;
- the example raises benchmark accuracy;
- the example weakens an expected effect;
- the example weakens statistical significance;
- the example is inconvenient for the hypothesis.

Eligibility is frozen independently of verifier behavior.

---

# 37. Duplicate Financial Facts

The same underlying financial fact may appear multiple times:

- within one document;
- in prose and tables;
- across earnings releases;
- financial statements;
- presentations;
- supplements;
- transcripts;
- other artifacts covering the same reporting event.

Repeated occurrence does NOT create independent scientific facts.

Duplicate equivalence is evaluated using the financial identity tuple:

- Entity
- Concept
- Period
- Scope
- Accounting Basis
- Temporal Frame
- Value Role
- normalized Value

Two occurrences are duplicates only when they represent the same underlying
financial fact after identity normalization.

Equal numbers alone do NOT imply duplication.

Examples that remain distinct include:

- same value, different periods;
- same value, different segment scope;
- same value, GAAP versus non-GAAP;
- same value, actual versus guidance;
- same value, different financial concepts.

---

# 38. Rounded Duplicate Values

Numerically equivalent representations may be duplicate occurrences even when
display scales differ.

Examples:

`$39.3B`

and:

`$39,300M`

may represent the same fact.

Where one occurrence is rounded more coarsely than another, duplicate
resolution must consider source identity and explicit reporting precision.

Rounding equivalence MUST NOT merge materially different values merely because
they are close under verifier tolerance.

Duplicate equivalence is a dataset-construction decision and MUST NOT use the
FinVerify numeric matching threshold as its sole criterion.

---

# 39. Duplicate Clusters

All otherwise eligible duplicate occurrences are retained in the construction
ledger and linked through a stable:

`fact_cluster_id`

No occurrence is silently deleted.

Each cluster records all known source occurrences of the same financial fact.

This preserves provenance and allows duplicate auditing.

Only one canonical occurrence from a fact cluster may enter the unique Natural
sampling pool.

---

# 40. Canonical Duplicate Selection

Canonical occurrence selection MUST be independent of verifier behavior.

The canonical occurrence is selected using the following hierarchy:

1. occurrence with the most direct authoritative financial reporting context;
2. if one occurrence is in a formal financial statement table and another is a
   repeated narrative restatement of the identical fact, prefer the formal
   financial statement occurrence;
3. otherwise prefer the occurrence in the source artifact with the lower
   frozen `source_id`;
4. if multiple equivalent occurrences remain in the same artifact, choose the
   earliest deterministic source locator.

The hierarchy MUST be applied mechanically.

FinVerify readability, parser success, or observed verification performance
MUST NOT influence canonical selection.

All non-canonical occurrences remain preserved in the ledger.

---

# 41. Source Groups

Source grouping exists to prevent leakage and false independence.

A `source_group_id` represents a leakage-relevant cluster of source artifacts
whose reporting coverage materially overlaps for the same issuer and financial
reporting event.

Artifacts are grouped together when they contain substantial overlapping
financial facts from the same reporting release cycle.

Examples include:

- earnings release + presentation for the same quarter;
- earnings release + earnings supplement for the same quarter;
- earnings release + transcript for the same reporting event;
- Q4 release and annual financial material when the same FY/Q4 financial facts
  materially overlap.

Source grouping is established from source provenance and reporting coverage,
not from verifier behavior.

---

# 42. Source-Group Manifest

Before DEV/TEST splitting, an explicit source-group manifest MUST be created and
frozen.

The manifest must map every source artifact to exactly one
`source_group_id`.

The mapping for the current 12-artifact corpus must be reviewed before any
split is generated.

Source-group definitions MUST NOT be changed because of observed FinVerify
performance.

If future corpus expansion occurs, new groups must be assigned using the same
principle.

---

# 43. DEV/TEST Isolation

DEV/TEST assignment occurs at the `source_group_id` level.

All candidates originating from artifacts in one source group must remain on
the same side of the DEV/TEST boundary.

Individual candidate randomization across the boundary is prohibited.

Duplicate fact clusters must also never cross the DEV/TEST boundary.

If a fact cluster unexpectedly spans two proposed source groups, the groups
must be merged before splitting.

This merge is based on source/fact overlap and occurs before verifier
execution.

---

# 44. Natural Track

A Natural candidate is an eligible quantitative financial fact occurring
naturally in the canonical authoritative source corpus.

Natural candidates preserve:

- verbatim source language;
- explicit target numerical occurrence;
- source provenance;
- financial identity metadata;
- deterministic evidence context.

Permitted processing includes:

- deterministic parsing;
- occurrence targeting;
- numeric normalization;
- metadata annotation;
- evidence packaging.

Prohibited processing includes:

- manual claim rewriting;
- adding identity information to claim text;
- stylistic simplification;
- paraphrasing;
- synthetic arithmetic;
- changing financial meaning.

---

# 45. Controlled Parent Eligibility

A Controlled parent must first be an eligible, deduplicated source-backed
financial candidate.

At minimum, the parent must have recoverable:

- Value;
- Entity;
- Concept;
- Period.

The source evidence must independently support the unperturbed parent.

Where a controlled perturbation targets an additional identity dimension, that
dimension must be explicitly recoverable for the parent.

Examples include:

- Scope;
- Accounting Basis;
- Temporal Frame;
- Value Role.

A parent MUST NOT be selected because a perturbation is known to fool
FinVerify.

---

# 46. Controlled Parent Pool

All unique eligible candidates satisfying the parent criteria form the:

`controlled_parent_pool`

Researchers MUST NOT manually create a smaller "interesting" parent pool.

The complete parent-eligible pool must be frozen before final parent sampling.

The pool must receive:

- stable IDs;
- deterministic ordering;
- SHA-256 hash;
- Git commit provenance.

No FinVerify outputs may be inspected before this freeze.

---

# 47. Controlled Perturbations

Controlled derivatives are not part of Natural enumeration.

They are generated only after:

1. parent eligibility;
2. parent-pool freeze;
3. Phase 9D parent-sampling freeze.

A controlled derivative must alter only the declared experimental dimension.

All non-target dimensions and the numerical value must remain invariant where
required by the governing experiment specification.

Phase 8 validation infrastructure must enforce the single-dimension mutation
constraint.

Attack success against FinVerify MUST NOT determine whether a derivative is
retained.

---

# 48. Natural Target Size

The intended final Natural evaluation set is:

**60–80 unique examples**

This is a design/sampling target.

It is NOT an eligibility criterion.

Eligibility rules MUST NOT be loosened or tightened to force the dataset into
this range.

The order is:

1. enumerate;
2. adjudicate eligibility;
3. deduplicate;
4. freeze unique eligible pool;
5. determine whether expansion is mechanically required;
6. freeze Phase 9D sampling procedure;
7. sample.

---

# 49. Controlled Target Size

The intended Controlled track uses approximately:

**15–25 parent claims**

supporting approximately:

**80–120 matched-control and single-dimension challenge pairs**

These are experimental design targets, not eligibility criteria.

Controlled-parent eligibility MUST NOT depend on attack success.

---

# 50. Corpus Expansion Trigger

Corpus expansion is triggered IF AND ONLY IF, after complete verifier-blind
enumeration, eligibility review, adjudication, and deduplication:

`N_unique_natural_eligible < 60`

OR:

`N_controlled_parent_eligible < 15`

If both thresholds are satisfied, corpus expansion is prohibited for the
current benchmark version.

No qualitative "coverage looks insufficient" trigger is permitted.

No expansion may be triggered by:

- FinVerify performance;
- baseline performance;
- attack success;
- effect size;
- statistical significance;
- desired identity distribution;
- desired paper result.

---

# 51. Corpus Expansion Procedure

If the mechanical expansion trigger is reached:

1. document the triggered threshold;
2. preserve the original Phase 9B corpus unchanged;
3. define the next source acquisition block without consulting verifier
   outcomes;
4. acquire authoritative sources;
5. establish provenance;
6. hash and freeze the added artifacts;
7. assign source groups;
8. run the SAME frozen extractor;
9. apply the SAME eligibility protocol;
10. update the candidate ledger and freeze records;
11. reassess the same numerical trigger.

The eligibility rules must not be rewritten merely because expansion occurred.

---

# 52. Sampling Seed

The reserved deterministic research seed is:

`20260804`

This seed must be used by Phase 9D where pseudo-random sampling is required
unless a previously frozen governing specification already mandates another
seed.

Seed selection MUST NOT be repeated until a favorable sample appears.

Seed mining is prohibited.

---

# 53. Eligibility Freeze vs Sampling Freeze

Phase 9C freezes:

- enumeration rules;
- extractor requirements;
- Natural representation;
- atomicity;
- evidence rules;
- financial eligibility;
- operational exclusions;
- identity interpretation;
- ambiguity procedure;
- exclusion taxonomy;
- duplicate rules;
- source grouping principles;
- Controlled-parent eligibility;
- expansion thresholds;
- reserved random seed;
- information barriers.

Phase 9D may freeze, after the eligible pool is known:

- exact Natural sample size within the frozen target range;
- exact stratification variables;
- stratum allocation;
- deterministic sampling implementation;
- exact Controlled-parent sample size within the frozen target range;
- parent allocation across strata.

Phase 9D MUST occur before:

- FinVerify execution;
- baseline execution;
- controlled attack evaluation;
- TEST outcome inspection.

The eligible-pool composition may inform Phase 9D sampling design.

Verifier performance may not.

---

# 54. Sampling Principles for Phase 9D

Although exact allocations are deferred, Phase 9D must obey the following
already-frozen principles:

1. sampling operates only on frozen eligible pools;
2. sampling is deterministic and reproducible;
3. sampling uses source/identity metadata only;
4. sampling never uses FinVerify or baseline outcomes;
5. source-group isolation is preserved;
6. duplicate fact clusters cannot create multiple independent Natural examples;
7. the reserved seed is used for pseudo-random choices;
8. the sampling specification is committed before system execution.

---

# 55. Information Barrier

Until the candidate pools and Phase 9D sampling specification are frozen,
dataset-construction personnel and scripts MUST NOT use scientific FinVerify
outputs for candidate decisions.

During:

- enumeration;
- eligibility review;
- ambiguity adjudication;
- duplicate resolution;
- source grouping;
- Natural sampling;
- Controlled-parent sampling;

the following information is prohibited as a decision input:

- FinVerify prediction;
- FinVerify status;
- FinVerify trust/confidence;
- baseline prediction;
- attack success;
- aggregate verifier performance.

Accidental exposure must be documented.

---

# 56. Artifact Separation

Dataset-construction artifacts and experimental-result artifacts must remain
operationally separate.

Construction artifacts include:

- raw occurrence ledger;
- eligibility decisions;
- adjudication records;
- duplicate clusters;
- source-group manifest;
- unique eligible pool;
- Controlled-parent pool;
- sampling manifest.

Experimental artifacts include:

- FinVerify outputs;
- baseline outputs;
- attack results;
- accuracy metrics;
- statistical results.

Experimental artifacts MUST NOT be required to generate or validate
construction artifacts.

---

# 57. Cryptographic Freeze

Scientific construction artifacts must be frozen through content hashes and Git
provenance.

At minimum, freeze manifests should record SHA-256 for:

- raw candidate ledger;
- eligibility/adjudication ledger;
- source-group manifest;
- unique eligible Natural pool;
- Controlled-parent pool;
- Phase 9D sampling manifest.

Git commit hashes must identify the repository state associated with each
freeze.

Filesystem creation timestamps are NOT scientific provenance and MUST NOT be
used as the primary information-barrier mechanism.

---

# 58. No Silent Deletion

Every enumerated occurrence must remain auditable.

If excluded, retain:

- candidate ID;
- provenance;
- raw target occurrence;
- exclusion status;
- primary exclusion reason;
- secondary reasons where applicable.

If duplicate, retain:

- candidate ID;
- fact cluster;
- canonical/non-canonical status.

If selected or not selected during sampling, preserve that status in the
sampling manifest.

Candidates must not disappear from the scientific record because they are
inconvenient.

---

# 59. Candidate Funnel Reporting

Final benchmark documentation must report the construction funnel.

At minimum:

- raw enumerated quantitative occurrences;
- non-financial exclusions;
- derived/out-of-scope exclusions;
- identity/evidence exclusions;
- parse failures;
- eligible occurrences before deduplication;
- duplicate occurrences;
- unique eligible financial facts;
- Controlled-parent-eligible facts;
- final Natural sample;
- final Controlled-parent sample.

Counts must be derived from frozen construction artifacts.

---

# 60. Human Review Provenance

Eligibility and adjudication records should preserve:

- reviewer identifier or blinded reviewer code;
- decision;
- primary exclusion reason;
- secondary reasons;
- adjudication status;
- adjudicated decision where applicable.

Review records MUST NOT contain FinVerify outputs.

Human review exists to interpret source validity, not to optimize verifier
performance.

---

# 61. Change Control

After Phase 9C freeze, the rules in this document must not be silently changed.

Any amendment requires:

1. version increment;
2. explicit change description;
3. methodological justification;
4. identification of affected construction stages;
5. rerunning affected eligibility decisions consistently;
6. preservation of the previous protocol;
7. disclosure in benchmark documentation.

A change motivated by observed FinVerify or baseline performance is prohibited.

---

# 62. Pre-Enumeration Freeze Checklist

Scientific enumeration MUST NOT begin until:

- [ ] Phase 9B corpus freeze is intact.
- [ ] Canonical source manifest validates.
- [ ] Phase 9C protocol has received adversarial review.
- [ ] Phase 9C protocol has received independent reproducibility review.
- [ ] All remaining CRITICAL/HIGH methodology blockers are resolved.
- [ ] Enumeration extractor specification is consistent with this protocol.
- [ ] FinVerify has not been run on scientific candidates.
- [ ] No candidate has been selected based on verifier behavior.

---

# 63. Phase 9C Exit Criteria

Phase 9C is complete only when:

1. this protocol has received final blocker review;
2. no unresolved CRITICAL/HIGH methodological findings remain;
3. the final document is committed;
4. the freeze commit hash is recorded;
5. candidate enumeration has not yet begun;
6. no scientific candidate has been selected using FinVerify or baseline
   behavior.

After Phase 9C freeze, implementation/testing of the deterministic enumerator
may proceed.

Scientific candidate enumeration may begin only after that implementation is
reviewed against this frozen protocol.

---

# 64. Phase 9D Boundary

Phase 9D is the:

**Pre-Outcome Sampling Freeze**

It occurs only after:

- deterministic enumeration;
- eligibility review;
- adjudication;
- duplicate resolution;
- source-group assignment;
- unique eligible pool freeze;
- Controlled-parent pool freeze.

Phase 9D determines the final deterministic sampling procedure.

No scientific FinVerify or baseline execution may occur between Phase 9C and
Phase 9D.

---

# 65. Final Scientific Principle

FinVerifyBench measures a frozen verifier against independently defined
financial claims.

The benchmark must not redefine financial validity around what FinVerify
already knows how to verify.

Therefore:

> Source validity determines benchmark eligibility.

> Verifier capability does not determine dataset membership.

> Sampling is frozen before outcomes.

> Experimental outcomes are observed only after construction decisions are
> immutable.