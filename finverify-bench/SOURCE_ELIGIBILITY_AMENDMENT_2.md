# SOURCE ELIGIBILITY AMENDMENT 2

**Amendment identifier:** `SOURCE_ELIGIBILITY_AMENDMENT_2`
**Parent protocol:** `SOURCE_ELIGIBILITY_v1.md` v1.0 (immutable, unmodified by this document)
**Co-frozen sibling amendment:** `SOURCE_ELIGIBILITY_AMENDMENT_1.md` (unmodified by this document; distinct authorized area — see §9)
**Governing implementation contract:** `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` (unmodified by this document; requires subsequent revision — see §10)
**Discovery phase:** Phase 9C-I2, following the Phase 9C-I1 adversarial review pair
**Status:** pre-outcome amendment for adversarial review
**Reserved Phase 9D seed (untouched by this amendment):** `20260804` (`SOURCE_ELIGIBILITY_v1.md` §52)

This amendment supplements `SOURCE_ELIGIBILITY_v1.md`; it does not rewrite,
replace, or modify that immutable historical document, `SOURCE_ELIGIBILITY_AMENDMENT_1.md`,
or `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md`. It resolves exactly one
operational blocker identified before production eligibility execution:

> The parent protocol's Step 4 ("human eligibility review",
> `SOURCE_ELIGIBILITY_v1.md` §4) requires review of every occurrence in the
> frozen Run-2 raw candidate ledger (`raw_candidate_ledger_run2.jsonl`,
> `candidate count: 14118`, `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §2). 100%
> human semantic review of 14,118 occurrences is operationally infeasible
> under available reviewer capacity.

This amendment authorizes exactly one new area, distinct from the three
areas Amendment 1 authorizes (duplicate equivalence, source-group overlap,
pre-sampling Controlled challenge declaration): **the mechanism and
provenance of the Step 4 eligibility-determination pass**, replacing
universal human semantic review with a frozen LLM-ensemble annotation
procedure validated by a blinded, probability-sampled, outcome-independent
human audit. No canonical-occurrence rule, corpus-expansion rule, threshold,
enumeration rule, duplicate/source-group rule, Controlled-parent rule, or
verifier rule is amended.

## 0. Information available and information excluded

This amendment is based only on: the frozen text of `SOURCE_ELIGIBILITY_v1.md`
v1.0, `SOURCE_ELIGIBILITY_AMENDMENT_1.md`, and `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md`;
the stated operational fact that human-review capacity is uncertain and a
large fixed volunteer count cannot be guaranteed; and the findings of the two
Phase 9C-I1 adversarial reviews as characterized in the request that produced
this document. It does not use, and was not informed by: the Run-2 candidate
ledger's contents, any individual scientific candidate, eligible-pool counts
or composition beyond the frozen header metadata already published in
`ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §2 (candidate count, hashes, commit
IDs — provenance metadata, not candidate content), FinVerify outputs, model
outputs, baseline outputs, attack success, or any benchmark outcome. No LLM
annotation and no eligibility processing has been executed. No external
network, model, or LLM was used to derive any rule in this document.

## 1. What the resulting corpus is — and is not

The Phase 9C-I2 eligibility ledger is **LLM-annotated, with a blinded
statistical human audit of a sampled subset**. It is explicitly **not** a
fully human-reviewed corpus. This restates and specializes
`SOURCE_ELIGIBILITY_v1.md` §32's requirement that "Human review determines
whether each occurrence satisfies the frozen financial eligibility rules":
under this amendment, that determination is made for all 14,118 occurrences
by the frozen LLM ensemble (§3–§4 below), and is independently re-derived by
blind human reviewers only for the sampled audit subset (§5–§13). Every
downstream artifact — paper, dataset card, `eligibility_summary.json`,
README — referencing this ledger MUST use language consistent with this
distinction. Prohibited: "human-reviewed eligibility corpus," "manually
verified corpus," or any construction implying 100% human adjudication.
Permitted: "eligibility labels produced by a frozen LLM-ensemble annotation
procedure (`ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §6 rubric), validated by a
blinded stratified human audit of n cases (see §14 for the estimator and its
scope)."

## 2. Amendment to the Enumeration Architecture (`SOURCE_ELIGIBILITY_v1.md` §4)

The nine-step order frozen in §4 is preserved verbatim, with **Step 4 only**
amended:

```text
1. frozen source corpus                                    — UNCHANGED
2. deterministic quantitative occurrence extraction         — UNCHANGED
3. immutable raw occurrence ledger                          — UNCHANGED
4. human eligibility review                                 — AMENDED (this document)
   -> frozen LLM-ensemble eligibility annotation (§3–§4)
   -> blinded, stratified, outcome-independent human audit (§5–§13)
   -> disagreement adjudication (§12)
5. eligibility/adjudication freeze                          — UNCHANGED
6. duplicate resolution                                     — UNCHANGED
7. unique eligible candidate pool freeze                    — UNCHANGED
8. Phase 9D pre-outcome sampling freeze                      — UNCHANGED
9. FinVerify execution                                       — UNCHANGED
```

Step 4's amended output must still terminate in exactly the three states
frozen in `SOURCE_ELIGIBILITY_v1.md` §32 and
`ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §4 — `ELIGIBLE`, `EXCLUDED`,
`ADJUDICATION_REQUIRED` — using the unchanged exclusion-code vocabulary and
precedence order of §34–§35 / Implementation Spec §5. This amendment changes
**who/what performs the determination and how it is audited**, not the
terminal-state vocabulary, the exclusion-code vocabulary, the financial
eligibility rubric (§15–§26 of the parent protocol), or the evidence-
construction rules (§27–§31 / Implementation Spec §7).

## 3. Frozen LLM-ensemble annotation procedure

Before any Run-2 occurrence is processed, the following is fixed,
version-hashed, and committed as `annotation_config.lock.json` (a new
construction artifact under `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §14's
freeze-and-hash regime):

1. **Model identities and versions** — exact model IDs/checkpoints for every
   ensemble annotator (k ≥ 3), subject to the disjointness constraint in §4.
2. **Prompts** — the full verbatim prompt given to each annotator, which MUST
   reproduce, without paraphrase, the eligibility question and checklist
   already frozen in `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §6 ("Does this
   explicitly enumerated occurrence represent an eligible quantitative
   financial fact, with sufficient permitted source context...") and the
   evidence-package boundary already frozen in Implementation Spec §7. No
   annotator may see more or different context than that boundary permits.
3. **Decoding settings** — temperature, top_p, max tokens, fixed identically
   across the full 14,118-occurrence run.
4. **Output schema** — structured per-occurrence output covering: eligibility
   verdict (`ELIGIBLE` / `EXCLUDED` / cannot-resolve), `primary_exclusion_code`
   and `secondary_exclusion_codes` drawn only from the frozen vocabulary in
   `SOURCE_ELIGIBILITY_v1.md` §34 / Implementation Spec §5, and the identity
   fields already present in the frozen ledger schema (`entity`, `concept`,
   `period`, `scope`, `accounting_basis`, `temporal_frame`, `value_role`,
   `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §12).
5. **Aggregation rule** — §4 below.
6. **Failure handling** — malformed/non-schema output, refusal, or timeout is
   logged (never silently dropped, per `SOURCE_ELIGIBILITY_v1.md` §58) and
   routed to a fixed retry-then-`ADJUDICATION_REQUIRED` fallback; a failure
   is never defaulted to `ELIGIBLE` or `EXCLUDED`.

No element of 1–6 may be modified after the annotation run begins. Any
change requires a new, separately versioned amendment.

## 4. Annotation/evaluation model disjointness and deterministic aggregation

**Disjointness.** The model families used for eligibility annotation MUST be
disjoint, at model-family granularity, from the model families subsequently
used as FinVerifyBench evaluation targets or LLM baselines. Both lists (the
annotation ensemble and the evaluation/baseline roster) are fixed and
published before either the annotation run or the evaluation run begins. If
a family is later wanted for both roles, the evaluation design is amended
first; the annotation ensemble is never adjusted to preserve a
previously-chosen evaluation roster. This constraint is orthogonal to, and
does not touch, the verifier-blindness rules already frozen in
`SOURCE_ELIGIBILITY_v1.md` §55 and Implementation Spec §3 — it prevents a
different failure mode (shared model-family bias between labeling and
evaluation), not verifier-outcome leakage.

**Aggregation rule.** For k independently-prompted annotators:

- k-of-k or (k−1)-of-k agreement on `ELIGIBLE`/`EXCLUDED` → that label is the
  ensemble's `eligibility_status` candidate value; `agreement_tier` =
  `unanimous` (k-of-k) or `majority` (k−1-of-k).
- Any other outcome (including genuine splits or a fixed tie-break rule
  reaching no resolution) → `agreement_tier` = `split`, and the occurrence's
  `eligibility_status` candidate value is `ADJUDICATION_REQUIRED` — reusing
  the exact frozen terminal state from `SOURCE_ELIGIBILITY_v1.md` §32,
  rather than introducing a new sentinel value.
- `primary_exclusion_code`/`secondary_exclusion_codes` for an `EXCLUDED`
  majority/unanimous outcome are taken from the majority annotators' codes
  under the unchanged precedence order (§35 / Implementation Spec §5); a
  code disagreement among annotators who agree on the `EXCLUDED` verdict
  itself routes the occurrence to `ADJUDICATION_REQUIRED` rather than being
  silently resolved by vote count.

This rule applies uniformly, in one non-interactive batch, to all 14,118
occurrences, and may not be adjusted post hoc based on how the resulting
distribution looks.

## 5. Human audit — minimum guarantee and stopping rule

- **Frozen minimum guaranteed audit: n = 100** independent human-reviewed
  occurrences, committed regardless of volunteer turnout, fixed now before
  any annotation output exists.
- **Additional volunteer reviews beyond n = 100** are permitted under a
  **pre-registered exogenous stopping rule** referencing only calendar
  time/logistics — never observed agreement or disagreement. Acceptable
  forms: a fixed recruitment deadline; exhaustion of the fixed sampling
  manifest (§8); whichever occurs first.
- **Prohibited:** any stopping rule referencing interim agreement/error
  rates, κ, or any analysis of audit results. This specializes
  `SOURCE_ELIGIBILITY_v1.md` §36's forbidden-reasons list (which already
  prohibits excluding or altering eligibility because "the example lowers
  benchmark accuracy" or similar outcome-favorability reasoning) to the audit
  recruitment decision itself: recruitment duration is never chosen because
  the numbers look good or bad.

## 6. Sequencing: annotation before sampling before review

1. The frozen LLM ensemble annotates all 14,118 occurrences (§3–§4); this
   step produces the corpus-wide `llm_annotation` candidate values,
   `agreement_tier`, and is what is meant by "Step 4" completing under this
   amendment.
2. **Only after** step 1's outputs are frozen and hashed, the audit sample is
   drawn (§7–§8), stratified on `agreement_tier` — a property of the frozen
   annotation output, never of any FinVerify/DVL/Trust Engine result, per the
   unchanged information barrier in `SOURCE_ELIGIBILITY_v1.md` §55 and
   Implementation Spec §3.
3. **Only after** the sampling manifest (§8) is generated and hashed, human
   audit review begins.

Freeze timestamps for steps 1 and 2's outputs must both be logged and must
show step 1 preceding step 2 preceding step 3, per the cryptographic-freeze
and Git-provenance regime already required by `SOURCE_ELIGIBILITY_v1.md` §57.

## 7. Audit strata (deterministic, annotation-output-only)

- **Stratum A — Unanimous/majority Eligible.**
- **Stratum B — Unanimous/majority Excluded.**
- **Stratum C — Split (`ADJUDICATION_REQUIRED` candidate value from §4).**

Stratum population sizes (N_A, N_B, N_C; sum = 14,118) are computed once,
immediately after step 1 of §6, and locked into the manifest header (§8).
Because the frozen Natural-eligible target is only 60–80 unique facts after
deduplication (`SOURCE_ELIGIBILITY_v1.md` §48), N_A is expected to be a small
fraction of 14,118; if N_A is small enough that a meaningful audit fraction
approaches a full census, a 100% audit of Stratum A is permitted and
consistent with this amendment (allocation may be tuned to stratum
*population size*, a frozen-annotation-output structural fact, but never to
observed audit results).

## 8. Deterministic allocation, seed, inclusion probability, manifest

- **Random seed.** The reserved seed `20260804` (`SOURCE_ELIGIBILITY_v1.md`
  §52) remains reserved exclusively for Phase 9D sampling of the frozen
  eligible pool and is **not** reused here. The audit seed is derived once,
  mechanically, from pre-existing frozen hashes:

  `audit_seed_hex = SHA256(UTF8("finverify-phase9c-audit-v1\n" + raw_ledger_sha256_lower + "\n" + annotation_config_sha256_lower)).hexdigest()`

  `raw_ledger_sha256_lower` is the lowercase 64-hex SHA-256 of the already
  frozen Run-2 raw ledger. `annotation_config_sha256_lower` is the lowercase
  64-hex SHA-256 of the exact frozen `annotation_config.lock.json` bytes,
  committed before annotation inference begins. The domain string and newline
  separators above are literal ASCII/UTF-8 bytes. No alternate seed, redraw,
  manual replacement, or selection among multiple manifests is permitted.
- **Deterministic within-stratum order.** No implementation-specific PRNG is
  permitted. For candidate ID `c` in a stratum, compute
  `r(c) = SHA256(UTF8("finverify-phase9c-audit-rank-v1\n" + audit_seed_hex + "\n" + c)).hexdigest()`
  and order candidates by ascending hexadecimal `r(c)`, breaking the
  vanishingly unlikely hash tie by ascending UTF-8 candidate ID. The first
  `n_h` candidates in that order are selected. This makes the manifest
  identical across independent implementations.
- **Allocation.** For requested total audit size `n`, let `N = N_A+N_B+N_C`
  and `q_h = n * N_h / N`. Assign `floor(q_h)` cases to each nonempty
  stratum, then assign remaining slots one at a time by descending fractional
  remainder `q_h-floor(q_h)`. Exact remainder ties use the fixed lexical
  stratum order `A < B < C`. No stratum may receive more than `N_h`; if a
  stratum is exhausted, its unavailable slots are redistributed among strata
  with remaining capacity by reapplying the same proportional floor +
  largest-remainder rule to the remaining slots and remaining capacities.
  This algorithm is the sole allocation rule. Neyman-style or discretionary
  reallocation and later allocation addenda are prohibited. Allocation may
  not use audit results, candidate semantics, FinVerify/model outcomes, or
  observed/estimated agreement variance.
- **Inclusion probability.** Every one of the 14,118 occurrences receives a
  documented selection probability `pi_i = n_h / N_h` for its stratum (or
  `0` only if that stratum receives zero slots under the frozen allocation),
  recorded per occurrence.
- **Immutable manifest.** A single artifact (`audit_manifest_v1.csv` +
  SHA-256, recorded here once generated) lists candidate ID, stratum,
  inclusion probability, deterministic rank/draw order, selection flag, and
  generation timestamp. The manifest records the two input hashes and derived
  `audit_seed_hex`. It is generated exactly once and is a new construction
  artifact under the same freeze regime as the raw ledger, eligibility/
  adjudication ledger, source-group manifest, and pools
  (`SOURCE_ELIGIBILITY_v1.md` §57).

## 9. Relationship to Amendment 1 (no overlap, no conflict)

Amendment 1 authorizes exactly three areas — duplicate-equivalence
normalization (§2), source-group overlap (§3), and pre-sampling Controlled
challenge declaration (§4) — and states explicitly that it does not touch
canonical-occurrence rules, enumeration rules, thresholds, or verifier rules.
This amendment authorizes a fourth, disjoint area (the Step 4
eligibility-determination mechanism) and does not modify, reinterpret, or
depend on any of Amendment 1's three areas. In particular:

- Amendment 1 §2.2 / Implementation Spec §9 forbid LLM, embedding, or fuzzy
  matching **inside the deterministic duplicate-equivalence comparison**.
  This amendment does not touch that comparison. The identity fields an LLM
  annotator records (`entity`, `concept`, `period`, `scope`,
  `accounting_basis`, `temporal_frame`, `value_role`) are raw recorded values
  that flow, unchanged, into Amendment 1's unchanged deterministic
  normalization and comparison pipeline — exactly as a human reviewer's
  recorded values would have. The LLM never performs duplicate-equivalence
  comparison itself; Amendment 1's mechanism is the sole authority for that
  decision, untouched by this amendment.
- Amendment 1's own no-outcome-inspection attestation (§1) and this
  amendment's §0 are independent, parallel attestations for two disjoint
  policy areas; neither supersedes the other.

## 10. Relationship to `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` (Class C change, as anticipated)

The Implementation Spec's own change-control text (§14) states: "Any
ambiguity not resolvable by the frozen protocol, neutral mechanics, or
reviewer/adjudication provenance is explicitly: **REQUIRES
PRE-IMPLEMENTATION AMENDMENT**." This amendment is exactly that anticipated
mechanism, invoked for the Class-C policy change described in §2 above. It
requires the following subsequent revisions to the Implementation Spec,
none of which are made by this document itself (per the instruction that no
code or the historical frozen files be modified here):

- **§4 (Candidate review states):** the terminal states `ELIGIBLE` /
  `EXCLUDED` / `ADJUDICATION_REQUIRED` are unchanged. The workflow field
  `review_workflow_status` (`UNREVIEWED | INDEPENDENT_REVIEW | ADJUDICATION
  | FINALIZED`) and the existing `review_method` field must be extended with
  new permitted values distinguishing the LLM-annotation pass from the
  human-audit pass (e.g., `review_method` gains an `LLM_ENSEMBLE_ANNOTATION`
  value alongside whatever human-review value(s) it already carries; a
  `review_workflow_status` value or an additional `audit_status` field
  records whether an occurrence was additionally human-audited). `reviewer_id`
  and `adjudication_id` are reused unchanged for the human-audit and
  adjudication layers introduced here — no duplicate identity fields are
  created for that purpose.
- **§5 (Deterministic rules and reason codes):** unaffected; reused verbatim
  by the LLM ensemble.
- **§6 (Semantic eligibility review):** the review question and checklist are
  adopted **verbatim, unmodified**, as (a) the LLM annotator prompt's task
  definition and (b) the human-audit reviewer's rubric. No rewording.
- **§7 (Review context and evidence):** adopted verbatim as the evidence
  package boundary for both LLM annotators and human auditors — same
  content, same exclusions, no FinVerify/experiment material to either.
- **§8 (Reviewer and adjudication provenance):** the "Reviewer A / Reviewer
  B... disagreement becomes `ADJUDICATION_REQUIRED`... adjudication resolves
  it without FinVerify, baseline, model, or attack information" text is
  preserved and now additionally governs the human-audit layer (§11–§12
  below); it must be extended to also describe LLM-ensemble-level
  disagreement routing (§4 above), which did not previously exist as a
  concept in a human-only pipeline.
- **§12 (Review ledger and outputs):** the field list must be extended,
  additively, with: `llm_annotation`, `agreement_tier`, `human_audit_label`,
  `human_audit_label_2`, `adjudicated_label`, `label_source`,
  `audit_stratum`, `inclusion_probability`, `annotation_config_hash`,
  `audit_manifest_id`. No existing field is removed, renamed, or
  overwritten; see §13 below for the provenance contract.
- **§13 (Pool freeze and expansion):** unaffected — `natural_eligible` and
  `controlled_parent_eligible` are computed identically from whatever
  `eligibility_status` values result, regardless of how those values were
  produced; the `< 60` / `< 15` triggers are untouched.
- **§14 (Freeze, tests, change control):** new synthetic-fixture test
  categories are required for annotation-config validation, tie/failure
  handling, stratified-manifest determinism, and blinding enforcement — the
  same "tests must not inspect the Run-2 ledger" constraint applies
  unchanged. This amendment additionally introduces a **second default-deny
  production gate**, alongside the existing one in Implementation Spec §3:
  gate one authorizes the LLM-annotation production run against the frozen
  Run-2 ledger; gate two, separately, authorizes release of the audit
  sampling manifest and the start of human-audit review. Neither gate
  substitutes for the other.
- **§15 (Clause-by-clause table):** the row "27–36 | evidence, review
  states, adjudication, reason codes | A/B" requires an added note that the
  *reviewer-identity* clause within source §§32–33 (only) is now governed by
  this amendment; the evidence and reason-code substance in that row is
  unaffected.

## 11. Reviewer blinding

Human audit reviewers are blind, at the time of initial judgment, to: LLM
model identity/identities, individual model votes, the aggregated
`llm_annotation` value, `agreement_tier`/stratum assignment, any LLM
rationale text, and any FinVerify/DVL/Trust Engine output — consistent with
the unchanged information barrier in `SOURCE_ELIGIBILITY_v1.md` §55 and
Implementation Spec §3. Reviewers receive only the same deterministic
evidence package defined in Implementation Spec §7 and the same rubric text
from Implementation Spec §6. Case presentation order is randomized
independent of stratum.

## 12. Disagreement handling and adjudication

This specializes `SOURCE_ELIGIBILITY_v1.md` §33 (Ambiguity Review) and
Implementation Spec §8 for the audited sample:

1. A blind human reviewer records an initial judgment (`human_audit_label`).
2. If it diverges from `llm_annotation`, a **second, independent** human
   reviewer, also fully blind per §11 (including blind to the fact that this
   is a disagreement case), records a fresh judgment
   (`human_audit_label_2`) — mirroring, rather than replacing, the existing
   "Reviewer A / Reviewer B" dual-independent-judgment structure of §33 and
   Implementation Spec §8.
3. After both human judgments exist, apply the following binding rule. If
   `human_audit_label == human_audit_label_2`, that unanimous blind-human
   consensus is final for the human-audit ground-truth record and may not be
   overridden by an unblinded adjudicator, including in favor of the LLM.
   `adjudicated_label` is set mechanically to that consensus value for schema
   continuity, with provenance `llm_human_consensus`; no unblinded
   adjudication occurs. Only when the two blind human reviewers disagree may
   the case proceed to adjudication. In that case the adjudicator sees the
   full record (LLM votes/rationale, both human judgments, source), issues
   `adjudicated_label`, and supplies a timestamped mandatory written
   justification. If the adjudicator is not independent of the annotation-
   pipeline author, that conflict is disclosed in the adjudication log for
   every affected case. This preserves §33's principle that reviewer
   disagreement does not itself prove source ambiguity while preventing an
   unblinded single adjudicator from overruling unanimous blind-human
   judgment.

Exactly **20 cases** within the guaranteed n=100 audit floor are a separate,
pre-registered double-coded subset; they are not additional cases. Allocate
these 20 across the already selected audit strata proportionally to the
selected audit counts using the same floor + largest-remainder + `A < B < C`
tie-break and capacity-redistribution rule in §8. Within each stratum, rank
already selected audit cases by
`SHA256(UTF8("finverify-phase9c-double-code-v1\n" + audit_seed_hex + "\n" + candidate_id)).hexdigest()`
and choose the first allocated cases, with candidate-ID tie-break as in §8.
Both reviewers independently review these cases while blind to each other's
decisions, LLM annotations/votes/rationales, agreement stratum, and all
FinVerify/model outcomes. The fixed 20-case list is stored in the immutable
manifest before human review begins and is used to report human-human Cohen's
κ and its uncertainty; double-coding alone never changes the corpus-wide LLM
annotation.

## 13. Provenance — no undocumented hybrid ground truth

The corpus-wide `eligibility_status` value produced by the frozen LLM
ensemble (§3–§4) is preserved for all 14,118 occurrences and is never
silently overwritten by audit or adjudication results. Audit and
adjudication outcomes are recorded in separate, additive fields (§10's
`ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §12 extension list):

| Field | Populated for | Produced by |
|---|---|---|
| `llm_annotation` | all 14,118 | frozen ensemble + aggregation rule (§3–§4) |
| `agreement_tier` | all 14,118 | frozen ensemble (§4) |
| `human_audit_label` | audited sample only | first blind human reviewer (§12.1) |
| `human_audit_label_2` | disagreement-triggered and fixed double-coded subsets | second blind human reviewer (§12) |
| `adjudicated_label` | two-human consensus or human-human disagreement subset | binding consensus rule or adjudicator (§12.3) |
| `label_source` | all 14,118 | enum: `llm_only` / `llm_audited_agree` / `llm_human_consensus` / `llm_human_adjudicated` |

`eligibility_status` (the field already in `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md`
§12) is set to the LLM ensemble's candidate value for `llm_only` and
`llm_audited_agree` cases, to the binding two-human consensus value for
`llm_human_consensus` cases, and to the adjudicated value only where the two
humans disagreed and adjudication occurred; it is never a silent blend.
`label_source` must accompany every downstream reference to an occurrence's
eligibility so a `llm_only` case is never presented as human-reviewed and a
consensus/adjudicated case is never presented as a pure LLM annotation. This directly extends, rather than replaces,
`SOURCE_ELIGIBILITY_v1.md` §60's Human Review Provenance requirements: those
fields (reviewer identifier, decision, exclusion reasons, adjudication
status) remain exactly as frozen and now apply to the `human_audit_label` /
`human_audit_label_2` / `adjudicated_label` layer specifically, never to
`llm_annotation`.

## 14. Estimator — stratum-weighted, not naive sample-wide

Because strata are very likely sampled disproportionately to population
share, naive unweighted sample-wide agreement is prohibited as a
population-level estimate.

For stratum h ∈ {A, B, C}, population weight **W_h = N_h / 14118**, and
observed within-stratum agreement rate p̂_h (audited n_h in that stratum):

- **Stratum-weighted estimate:** p̂_weighted = Σ_h (W_h × p̂_h)
- **Variance/CI:** stratified-sampling variance with finite-population
  correction per stratum, reported as a 95% CI (normal approximation or
  stratified bootstrap, pre-specified before the audit closes).
- Report p̂_h and its own 95% CI (Wilson/Clopper–Pearson) per stratum, in
  addition to p̂_weighted; report Cohen's κ overall and per stratum; report
  human-human κ from the double-coded subset (§12) as a reliability ceiling.
- **Minimum inferential cell size: 20 audited cases.** No subgroup, category,
  subtype, accounting-frame, or analogous precision, recall, F1, agreement
  rate, or other inferential performance metric may be reported when the
  relevant audited denominator is `< 20`. Such cells may report raw counts
  and descriptive frequencies only and MUST be marked `UNDERPOWERED` /
  `NOT_ESTIMATED` for inferential metrics. This threshold is fixed by this
  amendment and may not be adjusted after audit results are observed.

## 15. What the audit statistics do and do not establish

**Establishes:** the stratum-weighted rate (with CI) at which the frozen
LLM-ensemble procedure agrees with independent blind human judgment on
eligibility, for this ledger, under the unchanged
`ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §6 rubric, at the achieved audit
sample size.

**Does NOT establish:** the downstream error rate of FinVerify/DVL/Trust
Engine outputs or any experimental conclusion built on the eligibility-
filtered corpus (annotation-agreement and downstream-result-error are
different constructs — see §16); an absolute ground truth beyond the
human-human κ ceiling (§12); category/subtype-level reliability at small
cell sizes (§14); or anything about occurrences never sampled.

## 16. Required downstream sensitivity analysis

Before any experimental conclusion is drawn from the eligibility-filtered
corpus, a sensitivity analysis must assess whether plausible eligibility-
labeling error (bounded by the stratum-weighted disagreement rate and its CI
upper bound, §14) could materially alter the conclusion — e.g., re-deriving
the key result(s) under a worst-case-plausible label-error perturbation
concentrated in the stratum most implicated by disagreement. A conclusion
not stable under such perturbation must be flagged as sensitive to
eligibility-labeling error, not presented as robust. This is a new
requirement; nothing in the frozen documents already requires it, and
nothing in them prohibits it.

## 17. Replacement of exact human-review and exact-count claims

Wherever `SOURCE_ELIGIBILITY_v1.md` §32/§60 or documents built on it state or
imply that eligibility labels for the full 14,118-occurrence ledger are the
product of complete human semantic review, or that population-level
eligibility statistics are exact human-derived quantities, that language is
superseded, for the full-corpus pass only, by: labels are LLM-annotation-
derived under the frozen procedure of §3–§4, validated by the blinded
stratified human audit of §5–§13, whose population-level estimate is the
stratum-weighted estimator of §14 reported with its 95% CI — not an exact
human-reviewed count. The candidate funnel reporting required by
`SOURCE_ELIGIBILITY_v1.md` §59 must additionally disclose the audit design
and estimator alongside the existing funnel counts.

## 18. Information barrier (extends `SOURCE_ELIGIBILITY_v1.md` §55 and Implementation Spec §3)

Annotation-procedure design (§3–§4), audit sampling design (§6–§8), and
audit-conduct decisions (§5, §11, §12) must not use, reference, or be
informed by: FinVerify outputs, DVL/Trust Engine results, benchmark/
evaluation performance, a desired or targeted final sample count, or any
anticipated paper conclusion — the exact prohibited-input list already
frozen in `SOURCE_ELIGIBILITY_v1.md` §55, extended to this amendment's new
construction artifacts (`annotation_config.lock.json`, the audit manifest,
the audit ledger — new instances of the "construction artifacts" category in
§56, never touched by "experimental artifacts"). Anyone with access to both
the eligibility pipeline and any experimental-outcome data is disqualified
from making subsequent, unlogged changes to the frozen annotation or
sampling configuration; any such change must be logged with justification
and flagged for adversarial review as a potential barrier breach.

## 19. Change-control compliance (`SOURCE_ELIGIBILITY_v1.md` §61)

This amendment satisfies all seven requirements §61 imposes on any
post-freeze change: (1) version increment — `AMENDMENT_2`, following
`AMENDMENT_1`; (2) explicit change description — §2 above; (3) methodological
justification — operational infeasibility of 14,118-occurrence full human
review, stated in the preamble, not observed-performance-driven, per §36's
forbidden-reasons list; (4) identification of affected construction stages —
Step 4 only (§2); (5) rerunning affected eligibility decisions consistently —
not applicable pre-execution, since no eligibility decision has yet been
made against Run-2 under either the old or new mechanism; (6) preservation of
the previous protocol — the parent protocol, Amendment 1, and the
Implementation Spec are unmodified historical documents, per this document's
own header attestations; (7) disclosure in benchmark documentation — required
by §17 above.

---

## Exact frozen sections superseded

- `SOURCE_ELIGIBILITY_v1.md` **§4**, Step 4 only ("human eligibility review")
  — replaced by the LLM-ensemble-annotation-plus-audit mechanism (§2–§13 of
  this amendment). Steps 1–3 and 5–9 of §4 are unaffected.
- `SOURCE_ELIGIBILITY_v1.md` **§32**, the clause "Human review determines
  whether each occurrence satisfies the frozen financial eligibility rules"
  — superseded insofar as it designates human review as the sole
  determination mechanism for the full 14,118-occurrence pass; the
  terminal-state vocabulary (`ELIGIBLE`/`EXCLUDED`/`ADJUDICATION_REQUIRED`),
  "no occurrence may silently disappear," and "reviewers MUST NOT inspect
  FinVerify or baseline outcomes" are preserved and extended to LLM
  annotators (§4, §18).
- `SOURCE_ELIGIBILITY_v1.md` **§60**, insofar as its human-review-provenance
  fields could be read as applying to `llm_annotation` — clarified (not
  removed) by this amendment's §13 to apply only to the human-audit and
  adjudication layer.
- `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` **§4** and **§8**, insofar as they
  assume a single human-only review pass with no LLM-ensemble stage — the
  terminal states and the disagreement/adjudication *principles* are
  preserved; the reviewer-identity assumption and the field-value space for
  `review_method`/`review_workflow_status` require the extension in §10.

No other clause of any frozen document is superseded.

## Exact frozen sections preserved (unaffected in substance)

`SOURCE_ELIGIBILITY_v1.md` §§1, 2, 3, 5–31 (enumeration architecture other
than Step 4, enumeration universe, extractor, parsing, ledger schema,
atomicity, explicit-value/derivation rules, normalization, financial
eligibility boundary, operational exclusions, financial identity dimensions,
evidence construction), §§34–36 (exclusion codes, precedence, forbidden
reasons), §§37–51 (duplicate facts, source groups, DEV/TEST isolation,
Natural/Controlled-parent definitions, target sizes, expansion trigger and
procedure), §52 (reserved seed, exclusively for Phase 9D, untouched — §8
above), §§53–54, §64 (Phase 9C/9D boundary and Phase 9D sampling
principles), §55–58 (information barrier, artifact separation,
cryptographic freeze, no silent deletion — all extended, not altered, per
§18), §59 (funnel reporting — extended per §17), §62–63 (pre-enumeration and
exit checklists), §65 (final scientific principle). `SOURCE_ELIGIBILITY_AMENDMENT_1.md`
in its entirety (§9 above). `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md` §§2–3,
5–7, 9–11, 13 in substance (schema/list extensions required per §10 do not
change their governing rules).

## Contradictions found

One direct textual tension, resolved rather than papered over: **
`SOURCE_ELIGIBILITY_v1.md` §32 states plainly that "Human review determines
whether each occurrence satisfies the frozen financial eligibility rules."**
Read in isolation, this is in literal conflict with replacing that mechanism
for the full-corpus pass with LLM-ensemble annotation. This amendment does
not deny the conflict; it resolves it through the exact mechanism §61
provides for changing frozen rules after freeze (version increment, change
description, justification, affected-stage identification, protocol
preservation, disclosure — §19 above), and confirms that the Implementation
Spec's own text independently anticipates and authorizes exactly this kind
of change ("REQUIRES PRE-IMPLEMENTATION AMENDMENT," §14). No other
contradiction was found: Amendment 1's no-LLM constraint is scoped strictly
to duplicate-equivalence comparison (§9 above) and does not reach eligibility
determination; the parent protocol's LLM prohibition in §6 is scoped
strictly to the (already-completed, already-frozen) enumeration extractor,
not to eligibility review; the reserved Phase 9D seed is untouched (§8); and
no threshold, target size, or verifier rule is referenced or altered.

## Unresolved ambiguities

- The precise new enum values for `review_method` / `review_workflow_status`
  (§10) are described functionally here but not yet finalized as exact
  string literals; that finalization belongs to the Implementation Spec
  revision, not to this policy amendment.
- Identity/independence of the adjudicator remains an operational limitation
  only for cases where the two blind human reviewers disagree. Unanimous
  blind-human consensus is binding under §12 and cannot be overridden. If no
  independent adjudicator is available for true human-human disagreements,
  the conflict-of-interest disclosure required by §12 is mandatory and must
  be stated as a publication limitation.

## Information-barrier declaration

No Run-2 candidate content, LLM annotation output, human audit result, or
FinVerify/DVL/Trust Engine experimental outcome was inspected, generated, or
referenced in drafting this amendment. No annotation or eligibility
processing was executed. The only production-ledger facts used were the
already-published header metadata in `ELIGIBILITY_IMPLEMENTATION_SPEC_v1.md`
§2 (candidate count `14118`, commit and hash identifiers, freeze metadata
paths) — provenance/identity metadata, not candidate content or eligibility
outcomes. All numeric thresholds introduced here (n=100 floor, cell-size
minimum) were chosen from general statistical-design reasoning and the
operational constraints stated in the request that produced this amendment,
not from any observed result.

## Production data inspected

NO

## FINAL VERDICT

**READY FOR ADVERSARIAL AMENDMENT REVIEW**

Basis: every section reference in this document has been verified against
the literal text and section numbering of the three uploaded frozen
documents (§18 of the prior draft's placeholder mapping has been replaced
throughout with exact citations). The one genuine textual tension against
the frozen protocol (`SOURCE_ELIGIBILITY_v1.md` §32) has been identified
explicitly rather than concealed, and is resolved through the frozen
protocol's own anticipated change-control mechanism (§61) and the
Implementation Spec's own anticipated amendment escape hatch (§14). No
contradiction was found with `SOURCE_ELIGIBILITY_AMENDMENT_1.md`'s three
authorized areas, and this amendment's own authorized area is disjoint from
theirs. Remaining items are genuinely open implementation/design parameters
(§"Unresolved ambiguities"), not unresolved conflicts with frozen text, and
are appropriately deferred to the Implementation Spec revision and the
annotation-run outputs that do not yet exist.
