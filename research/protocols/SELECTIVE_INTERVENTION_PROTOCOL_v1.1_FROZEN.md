# SELECTIVE_INTERVENTION_PROTOCOL_v1

**Status: FROZEN METHODOLOGY --- outcome-producing execution prohibited
until the Pre-Execution Provenance Lock in Section 12 is complete,
hashed, and committed.**

**Study:** Fresh FinNLP submission\
**Working title:** *Deterministic Verification as Selective
Intervention: Coverage, Precision, and Harm in Post-Hoc Numerical
Correction for Financial LLMs*

This protocol defines a new, standalone evaluation. It supersedes the
prior DVL-accuracy narrative for the purposes of this submission, but
does not modify or delete Amendment 1, Amendment 2, Phase 9C, or their
artifacts. Those remain historical provenance.

The methodology in Sections 1--11 is frozen before outcome-producing
execution. Dataset/model byte identities that cannot be known until the
artifacts are fetched are not researcher degrees of freedom: they are
handled by the mechanical Pre-Execution Provenance Lock in Section 12.
No FinQA inference, TAT-QA inference, DVL application to fresh
predictions, FCG outcome evaluation, or gold-based scoring may occur
until that lock is complete.

------------------------------------------------------------------------

## 1. Provenance and motivation

A prior FinVerify evaluation path used the reference answer during
correction selection. Legacy functions including `verify_answer`,
`expanded_verify`, `upgraded_verify`, notebook variants of
`full_verify`, and gold-aware calls into current DVL/math-engine logic
can accept or reject candidate corrections by comparison with
`actual`/`actual_value`. The legacy cross-model evaluation path also
passes reference values into verification.

Accordingly, historical figures such as 1.00%, 24.00%, 32.00%, 38.50%,
and 42.61% are **not evidence for the fresh study**. They may be
mentioned only as explicitly historical, unreproduced prior-reported
values. They may not appear as current results, baselines, or headline
claims.

The fresh study therefore evaluates deterministic verification as a
**selective intervention mechanism**, with gold structurally unavailable
during intervention.

------------------------------------------------------------------------

## 2. Frozen research questions

### RQ1 --- FinQA selective intervention

When a deterministic post-hoc verifier changes a financial LLM's
numerical prediction, how often does that intervention fix an error,
preserve correctness, or harm an already-correct prediction?

### RQ2 --- Rule behavior

Which frozen DVL rules drive successful and harmful interventions, and
what coverage--reliability trade-offs do they exhibit?

### RQ3 --- Cross-dataset transfer

Does the intervention profile observed on FinQA transfer to TAT-QA
without retraining, rule modification, threshold tuning, or
dataset-specific correction logic?

### RQ4 --- Verification mechanism

How does local numerical correction (DVL) compare with relational
financial-constraint verification (FCG) in structural coverage and,
where sample size permits, intervention reliability?

These questions do not presuppose that DVL or FCG improves accuracy. A
null or harmful result remains a valid outcome.

------------------------------------------------------------------------

## 3. Frozen states, transitions, and metrics

For each example:

-   `B ∈ {C, I}` is baseline correctness of the raw parsed prediction
    against gold.
-   `P ∈ {C, I}` is post-intervention correctness.
-   A **firing** occurs only when the verifier changes the numeric
    value.
-   A value returned unchanged is a **non-firing**, even if trust
    metadata changes.

Let:

-   `N` = total evaluated examples.
-   `F` = examples on which the system fires.

For fired examples:

  Baseline    Post        Transition
  ----------- ----------- ------------
  Incorrect   Correct     `I→C`
  Incorrect   Incorrect   `I→I`
  Correct     Incorrect   `C→I`
  Correct     Correct     `C→C`

### 3.1 Primary metrics

-   **Coverage** = `F / N`
-   **Successful-correction rate among firings** = `I→C / F`
-   **Harm rate among firings** = `C→I / F`
-   **Correctness-preserving intervention rate** = `(I→I + C→C) / F`
-   **Intervention precision** = `I→C / (I→C + C→I)`
-   **Net benefit** = `(I→C - C→I) / N`
-   **Baseline accuracy** = `count(B=C) / N`
-   **Post-intervention accuracy** = `baseline_accuracy + net_benefit`

`intervention_precision` is undefined when `I→C + C→I = 0` and must be
serialized/reported as `null` / `n/a`, never coerced to 0 or 1.

`post_intervention_accuracy` is derived from baseline accuracy and net
benefit; an independently calculated value may be used only as an
assertion/check and must agree exactly under the frozen scoring
definition.

### 3.2 Zero-firing rules

If `F_rule = 0`, all metrics with `F_rule` in the denominator are `null`
/ `n/a`. The rule remains visible in the table with firing count 0.

### 3.3 Aggregate versus per-rule units

System-level results use examples as the unit. Rule-level results use
firings attributed under Section 5. Because one example may contain a
multi-rule chain, rule-level counts may sum to more than aggregate
example-level counts. This is expected and must be stated.

------------------------------------------------------------------------

## 4. Gold-isolated architecture

### 4.1 Principle

The intervention stage must be structurally incapable of receiving gold,
correctness labels, error labels, or any value derived from them. This
is enforced by process, file, module, and type separation rather than
caller discipline.

### 4.2 Frozen blind input

``` python
@dataclass(frozen=True)
class BlindInterventionInput:
    example_id: str
    question: str
    context: str
    raw_generation: str
    parsed_prediction: Optional[float]
```

No gold-like field is permitted.

### 4.3 Frozen blind output

``` python
@dataclass(frozen=True)
class Correction:
    rule: str
    before: Optional[float]
    after: Optional[float]

@dataclass(frozen=True)
class BlindInterventionOutput:
    example_id: str
    verified_value: Optional[float]
    correction_log: list[Correction]
    fired_rules: list[str]
    trust_label: str
    trust_color: str
```

### 4.4 Frozen entry point

``` python
def blind_verify(input: BlindInterventionInput) -> BlindInterventionOutput:
    ...
```

This function accepts exactly one typed argument. It has no `actual`,
`actual_value`, `gold`, `target`, `y`, correctness parameter,
`**kwargs`, environment-variable escape hatch, or config path through
which gold can be injected.

If existing internal math functions are reused, the blind wrapper must
make the gold-free branch unavoidable. Prefer extracting/porting the
blind rule math into a module whose public API contains no gold-aware
argument rather than retaining a reachable gold-aware branch.

### 4.5 Process separation

The required order is:

1.  Generate raw prediction ledger.
2.  Persist and hash raw prediction ledger.
3.  Run blind intervention in a process that does not load the gold
    artifact.
4.  Persist and hash intervention ledger.
5.  Terminate blind-intervention process.
6.  Start scoring process.
7.  Load gold artifact.
8.  Join only on `example_id`.
9.  Compute transitions, metrics, and statistics.

The blind stage must still run successfully if the gold file is absent
or renamed.

------------------------------------------------------------------------

## 5. Frozen DVL rule scope and attribution

### 5.1 Rule scope

The fresh DVL is the existing **gold-free** scale/magnitude behavior
reconstructed from the repository. No correction rule may be added or
tuned after outcomes are observed.

The existing gold-free branch includes heuristic scale handling such as:

-   divide by 100 when the frozen rule identifies a large-value scale
    case;
-   multiply by 100 when the frozen rule identifies a sub-unit scale
    case;
-   preserve the frozen ambiguous-range behavior;
-   retain the existing blind magnitude behavior exactly as implemented
    in the frozen code revision.

The implementation must be traced against the repository before
execution and captured by implementation commit hash.

### 5.2 Frozen D1 decision --- sign

**Sign correction is structurally inactive in the fresh blind study
unless the already-existing frozen gold-free implementation can fire it
without any reference value. No new sign heuristic will be designed for
this paper.**

If the reconstructed blind implementation has no gold-free sign
correction, the sign row remains in all rule tables with `F=0` and
metrics `n/a`. This is a boundary finding, not a defect to patch after
results.

### 5.3 Attribution

Fixed rule order follows the frozen implementation.

For a multi-rule chain:

-   every value-changing rule creates one `Correction` entry;
-   each entry records that rule's immediate `before` and `after`;
-   aggregate system scoring compares raw parsed prediction with final
    verified value;
-   rule-level tables attribute the example's final `B→P` transition to
    every rule that actually fired in the chain;
-   therefore rule-level transition counts can exceed aggregate counts.

Report the **chain rate** separately.

Trust-label-only changes are diagnostics and are not firings.

------------------------------------------------------------------------

## 6. FinQA primary experiment

### 6.1 Dataset identity

Use the **official original FinQA repository** (`czyssrs/FinQA`), not
the historical Kaggle mirror, at an immutable commit.

The canonical validation artifact is:

`dataset/dev.json`

The source revision and file SHA-256 are recorded mechanically in the
Pre-Execution Provenance Lock.

Filter to examples whose canonical execution answer can be parsed as
numeric using the frozen filter. The expected historical filtered
universe is **873** examples.

If the official pinned artifact does not produce exactly 873 examples
under the frozen filter:

**STOP. Do not run inference.** Investigate the discrepancy and create a
protocol amendment before any outcome-producing execution.

Preserve the dataset's original FinQA `id` as `example_id`. No synthetic
row-number ID may replace it.

### 6.2 Frozen FinQA context serialization

The input representation uses all three source evidence regions
available in FinQA:

1.  `pre_text`, in original order;
2.  the complete table, row order preserved, cells pipe-delimited;
3.  `post_text`, in original order.

Deterministic serialization:

``` text
PRE-TEXT:
{pre_text paragraphs joined with newline}

TABLE:
{each table row joined with " | ", rows joined with newline}

POST-TEXT:
{post_text paragraphs joined with newline}
```

No gold supporting-fact selection (`gold_inds`) is used to construct
context.

The serializer shall never read or condition on `qa.model_input`, `qa.gold_inds`, `qa.program`, `qa.steps`, `qa.exe_ans`, or any other gold-derived QA metadata. Context is constructed exclusively from `pre_text`, `table`, `post_text`, and the natural-language question.

The complete serialized context is used subject only to the model
input-length budget in Section 6.4. There is **no arbitrary 512-token
pre-text truncation** in the fresh study.

### 6.3 Prompt

``` text
You are a financial analyst. Use the document below to answer the question with ONLY the final number.

DOCUMENT:
{serialized_context}

Question: {question}
Answer:
```

No gold program, gold evidence, execution answer, correctness label, or
error type enters the prompt.

### 6.4 Model and decoding

-   Base model: `mistralai/Mistral-7B-Instruct-v0.3`
-   Adapter: `aadi2026/finverify-lora`
-   Exact immutable revisions: recorded in Pre-Execution Provenance
    Lock.
-   Quantization: NF4 4-bit.
-   Compute dtype: float16 unless the frozen adapter-loading
    implementation demonstrably requires a different dtype; any such
    incompatibility is a stop condition before inference.
-   `do_sample=False`
-   `max_new_tokens=30`
-   no temperature/top-p sampling
-   deterministic tokenizer chat-template application
-   maximum model input length: 1024 tokens **including prompt/template
    overhead but excluding generated continuation**.

If an example exceeds the 1024-token input budget, truncate **context
only**, deterministically, using a frozen balanced evidence-preserving
policy:

1.  retain the full question and prompt instructions;
2.  retain the table before removing prose;
3.  allocate remaining context budget between pre-text and post-text in
    document order, approximately evenly when both are present;
4.  never truncate by gold evidence or correctness;
5.  record `input_tokens`, `context_truncated`, and the exact serialized
    context actually sent.

The ledger-generation implementation must unit-test this policy before
execution.

The 1024-token input budget is frozen for comparability with the historical inference configuration and shall not be tuned after observing experimental outcomes.

### 6.5 Parser

Freeze one parser before execution. It must:

-   strip currency symbols and thousands separators;
-   handle percent signs deterministically;
-   convert parenthesized numeric expressions to negative where
    applicable;
-   extract the last matched numeric token from the generated answer;
-   return `None` on parse failure rather than repairing from
    gold/context.

The exact parser code is implementation-versioned and test-covered.

### 6.6 Self-contained raw ledger --- frozen D4 decision

Each record stores:

``` json
{
  "example_id": "...",
  "question": "...",
  "context": "...",
  "raw_generation": "...",
  "parsed_prediction": 27.9,
  "input_tokens": 812,
  "context_truncated": false
}
```

No gold, correctness, gold evidence, gold program, error label, or
post-intervention value is permitted.

The raw ledger is written once, deterministically ordered by canonical
dataset order, SHA-256 hashed, and never overwritten.

### 6.7 Separate gold artifact

``` json
{"example_id":"...","gold":27.9}
```

Gold is produced as a separate artifact and is unavailable to the blind
intervention process.

------------------------------------------------------------------------

## 7. TAT-QA transfer experiment

TAT-QA is a **core transfer experiment**, not an optional follow-up.

### 7.1 Dataset

Use the official TAT-QA release at an immutable revision recorded in the
Pre-Execution Provenance Lock.

Use the dev split and freeze a deterministic arithmetic/numeric-answer
eligibility filter before inference. Record:

-   source repository;
-   immutable revision;
-   source file SHA-256;
-   raw dev count;
-   eligible count;
-   exclusion counts by mechanical reason.

No expected count is forced. The observed eligible count is provenance,
provided it results from the frozen filter.

### 7.2 Serialization

Serialize all source evidence available to the selected TAT-QA example:

1.  paragraphs in original order;
2.  table in original row order, pipe-delimited;
3.  question.

Do **not** use the historical arbitrary 2,000-character truncation.

Apply the same 1024-token model-input budget and the same principles as
FinQA:

-   preserve instructions/question;
-   prioritize complete table structure;
-   allocate remaining budget deterministically to prose;
-   never select/truncate using gold evidence or correctness;
-   record the exact context sent and truncation metadata.

The TAT-QA serializer is frozen and unit-tested before either dataset's
outcome is scored.

### 7.3 Model, parser, decoding, DVL

Use the **identical pinned base model, adapter, parser, decoding
settings, blind DVL implementation, and metric definitions** used for
FinQA.

There is:

-   no TAT-QA fine-tuning;
-   no threshold tuning;
-   no TAT-QA-specific correction rule;
-   no modification based on FinQA results.

The purpose is transfer of the intervention profile, not leaderboard
optimization.

During scoring, correctness is evaluated against the canonical numeric answer. The dataset `scale` field is retained only for descriptive subgroup analysis and shall never be applied as an additional multiplier or correction during evaluation.

------------------------------------------------------------------------

## 8. Financial Constraint Graph (FCG)

FCG is a second, conceptually distinct verification mechanism:
relational financial consistency rather than local single-value
correction.

### 8.1 Structural eligibility

Candidate financial concepts are extracted deterministically using the frozen `METRIC_ALIASES` registry present in the repository.

Extraction rules:

- Unicode normalization and whitespace collapsing.
- Case-insensitive exact alias matching only.
- No fuzzy matching.
- No embedding similarity.
- No LLM-based extraction.
- No researcher annotation.
- No post-hoc alias creation.

A canonical concept is present iff exactly one alias matches.

An example is structurally FCG-eligible iff the extracted canonical concepts satisfy the `requires` tuple of at least one pre-existing registered constraint.

Eligibility is computed without:

- gold answer;
- baseline correctness;
- DVL outcome;
- FCG verification outcome;
- researcher judgment after seeing results.

The exact constraint registry and extraction implementation are frozen by implementation commit hash before FCG evaluation.

### 8.2 Coverage is always reported

For both FinQA and TAT-QA report:

`FCG structural coverage = eligible_examples / dataset_examples`

Also report eligible `n` and relation/constraint-type counts.

### 8.3 Frozen D5 decision --- inferential threshold

The predeclared threshold is **30 FCG-eligible examples per dataset**.

If `eligible_n >= 30`:

-   include FCG in the main comparative intervention analysis;
-   report the same applicable
    transition/coverage/precision/harm/net-benefit metrics;
-   report uncertainty under Section 9.

If `eligible_n < 30`:

-   FCG is **not deleted or silently omitted**;
-   report structural coverage, eligible `n`, constraint types, and
    descriptive outcomes;
-   exclude it from primary inferential comparison tables;
-   make no generalization or intervention-precision claim from that
    dataset's FCG subset.

The threshold cannot be changed after eligibility or outcomes are
observed.

### 8.4 No post-hoc FCG expansion

No new constraint type may be added because coverage or performance is
disappointing. Any future expansion is a separately labeled
post-hoc/future-work experiment and cannot enter primary results.

------------------------------------------------------------------------

## 9. Statistics

### 9.1 Transition counts first

Every result table must expose raw:

-   `N`
-   `F`
-   `I→C`
-   `C→I`
-   `I→I`
-   `C→C`

before derived rates.

### 9.2 Paired test

Use McNemar's test for paired baseline versus post-intervention
correctness.

Use the **exact binomial McNemar test** when the total discordant count
(`I→C + C→I`) is \<25; otherwise report the standard
continuity-corrected McNemar result. The raw discordant counts are
always shown.

Rule-level tests are secondary and are only reported when the rule has
nonzero discordant transitions. They are not used to redefine rules or
thresholds.

### 9.3 Bootstrap

Use **10,000 bootstrap resamples**.

-   Aggregate metrics: example-level resampling over `N`.
-   Per-rule intervention precision: firing-level resampling over
    `F_rule`.
-   Report 95% percentile bootstrap confidence intervals.
-   If a bootstrap replicate has an undefined denominator for a metric,
    that replicate is excluded for that metric and the number of valid
    replicates is reported.
-   If `I→C + C→I < 20`, intervention precision is flagged **low-power**
    and raw counts are emphasized.

### 9.4 Multiple comparisons

Primary confirmatory interpretation is system-level FinQA and
cross-dataset transfer. Per-rule significance tests are
secondary/descriptive. No claim of independent confirmatory significance
is made from a battery of uncorrected rule-level p-values.

### 9.5 No outcome-driven modification

No dataset filter, prompt, parser, verifier rule, threshold, FCG
relation, statistical test, or metric definition may be modified because
of observed accuracy, p-values, precision, coverage, or harm.

Any analysis invented after outcomes are visible must be labeled
**post-hoc exploratory** and kept separate from primary tables.

------------------------------------------------------------------------

## 10. Required implementation tests

The implementation must pass all tests before full inference.

1.  **`test_blind_interface_no_gold`**\
    Introspect blind input/output dataclass fields. Reject names
    containing gold-like/correctness-like terms including `gold`,
    `actual`, `actual_value`, `target`, `y_true`, `correct`,
    `error_label`.

2.  **`test_blind_verify_signature`**\
    Assert `blind_verify` has exactly one typed input parameter and no
    `**kwargs`.

3.  **`test_blind_verify_rejects_smuggled_gold`**\
    Extra arbitrary gold-bearing objects/dicts cannot alter the result
    and preferably fail type validation.

4.  **`test_blind_stage_runs_without_gold_file`**\
    Rename/remove the gold artifact; the complete blind-intervention
    stage must produce byte-identical output.

5.  **`test_blind_module_has_no_gold_dependency`**\
    Blind intervention and its callees must not import the
    scoring/gold-loading module or read the gold path.

6.  **`test_attribution_chain_counts`**\
    Synthetic multi-rule chain produces separate correction-log entries
    and deterministic shared final-transition attribution.

7.  **`test_zero_intervention_metrics_are_null`**\
    Zero-firing rules yield `null`/`n/a`, never 0% or 100%.

8.  **`test_net_benefit_equals_derived_accuracy`**\
    Frozen metric identity holds exactly.

9.  **`test_ordering_gold_after_intervention`**\
    Integration test persists intervention output before any scoring
    process loads gold.

10. **`test_ledger_hash_immutability`**\
    Identical deterministic fixture inputs yield identical ledger
    SHA-256; a one-record mutation changes it.

11. **`test_finqa_serializer_deterministic`**\
    Pre-text/table/post-text ordering and token-budget truncation are
    deterministic and gold-independent.

12. **`test_tatqa_serializer_deterministic`**\
    Paragraph/table serialization and token-budget truncation are
    deterministic and gold-independent.

13. **`test_parser_fixtures`**\
    Currency, commas, percentages, parentheses, multiple numbers,
    negatives, and parse failures match frozen expected outputs.

14. **`test_fcg_eligibility_gold_independent`**\
    Changing/removing gold does not change FCG structural eligibility.

15. **`test_dataset_id_uniqueness`**\
    Canonical example IDs are present and unique in every ledger.

16. **`test_no_model_input_usage`**\\
    Corrupt `qa.model_input` while leaving `pre_text`, `table`, and `post_text` unchanged. Serialized context must remain byte-identical.

17. **`test_actual_none_adapter`**\\
    Blind verification must never forward a non-`None` gold/reference value into any verification path.

18. **`test_fcg_alias_registry_deterministic`**\\
    Reordering alias definitions must not change FCG eligibility.

------------------------------------------------------------------------

## 11. Frozen execution order

The mandatory sequence is:

1.  Commit this frozen methodology protocol.
2.  Resolve Section 12 provenance mechanically.
3.  Create `PREEXECUTION_PROVENANCE_LOCK.json`.
4.  Verify all provenance gates.
5.  Hash and commit the provenance lock.
6.  Codex/implementation agent implements the protocol without
    redesigning it.
7.  Run unit/integration tests.
8.  Freeze implementation commit hash.
9.  Run a non-outcome smoke test on synthetic fixtures.
10. Generate full FinQA raw ledger.
11. Hash FinQA raw ledger.
12. Generate full TAT-QA raw ledger.
13. Hash TAT-QA raw ledger.
14. Run blind DVL on FinQA with gold unavailable.
15. Hash FinQA intervention ledger.
16. Run blind DVL on TAT-QA with gold unavailable.
17. Hash TAT-QA intervention ledger.
18. Compute FCG structural eligibility on FinQA and TAT-QA without
    gold/outcomes.
19. Freeze FCG eligibility artifacts.
20. Run frozen FCG where structurally eligible.
21. Hash FCG outputs.
22. **Only now** start scoring processes and load gold.
23. Compute frozen metrics.
24. Run frozen bootstrap/McNemar analyses.
25. Produce primary and rule-level tables.
26. Interpret outcomes.
27. Any additional analysis is explicitly post-hoc unless covered by a
    separately frozen amendment.

No full experiment is delegated to an implementation agent merely to
save local execution effort; experiment execution remains a separately
logged research step.

------------------------------------------------------------------------

## 12. Pre-Execution Provenance Lock

This section resolves former D2/D3 and the TAT-QA equivalent **without
reopening methodology**.

Before any outcome-producing execution, create:

`research/protocols/PREEXECUTION_PROVENANCE_LOCK.json`

with at least:

``` json
{
  "protocol_sha256": "...",
  "finqa": {
    "repo": "czyssrs/FinQA",
    "revision": "<immutable commit>",
    "dev_path": "dataset/dev.json",
    "dev_sha256": "<sha256>",
    "raw_count": 0,
    "numeric_eligible_count": 0
  },
  "tatqa": {
    "repo": "<official TAT-QA repository>",
    "revision": "<immutable commit>",
    "dev_paths": ["..."],
    "dev_sha256": ["..."],
    "raw_count": 0,
    "eligible_count": 0
  },
  "base_model": {
    "repo": "mistralai/Mistral-7B-Instruct-v0.3",
    "revision": "<immutable HF commit>"
  },
  "adapter": {
    "repo": "aadi2026/finverify-lora",
    "revision": "<immutable HF commit>"
  },
  "implementation_commit": "<filled only after implementation freeze>",
  "environment": {
    "python": "...",
    "torch": "...",
    "transformers": "...",
    "peft": "...",
    "bitsandbytes": "...",
    "datasets": "...",
    "cuda": "...",
    "gpu": "..."
  }
}
```

### 12.1 Mechanical resolution rules

-   FinQA must come from official `czyssrs/FinQA`, not a mirror.
-   Use an immutable source commit, not `main`.
-   Model and adapter revisions are resolved from the repositories'
    immutable commit SHAs; never use `main`.
-   The adapter revision must exist and load against the pinned base
    model. Incompatibility is a stop condition, not permission to
    silently substitute a different adapter/base.
-   File SHA-256 values are computed from downloaded bytes before
    parsing.
-   All resolved values are committed before inference.
-   No value in this lock may be chosen based on model accuracy or
    verifier outcomes.
-   If any scientific implementation ambiguity remains after protocol freeze, implementation must stop. A pre-execution amendment must be created, hashed, committed, and approved before any outcome-producing execution. Implementation agents may not independently resolve scientific ambiguities.

A public immutable FinQA revision used by existing dataset tooling is
`0f16e2867befa6840783e58be38c9efb9229d742`; the resolver must verify
that this commit exists in the official repository and that its
`dataset/dev.json` satisfies the frozen 873-example gate before locking
it.

The Mistral repository has immutable commit history; the resolver must
pin the exact commit used for loading rather than relying on a moving
branch. The adapter revision must likewise be resolved from its Hugging
Face repository using authenticated access if private/unindexed.

### 12.2 Stop conditions

Stop before inference if any of the following occurs:

-   FinQA filtered count is not 873.
-   Canonical IDs are missing or duplicated.
-   Dataset artifact hash cannot be computed.
-   Model or adapter immutable revision cannot be resolved.
-   Adapter cannot load against the pinned base.
-   Required test fails.
-   Blind stage has any reachable gold dependency.
-   Serializer/parser differs from the committed implementation.
-   Protocol/provenance hashes do not match committed files.

Resolution of a stop condition requires a documented amendment committed
**before** outcomes are produced.

------------------------------------------------------------------------

## 13. Repository structure

``` text
research/
  protocols/
    SELECTIVE_INTERVENTION_PROTOCOL_v1.md
    PREEXECUTION_PROVENANCE_LOCK.json
    PROVENANCE_HASHES.md

  ledger/
    generate_finqa_ledger.py
    generate_tatqa_ledger.py
    provenance.py
    finqa_dev_raw_ledger.jsonl
    finqa_dev_gold.jsonl
    tatqa_dev_raw_ledger.jsonl
    tatqa_dev_gold.jsonl

  intervention/
    blind_dvl.py
    attribution.py
    scoring.py

  fcg/
    feasibility.py
    blind_fcg.py

  stats/
    bootstrap.py
    mcnemar.py

  tests/
    test_blind_interface_no_gold.py
    test_blind_verify_signature.py
    test_blind_verify_rejects_smuggled_gold.py
    test_blind_stage_runs_without_gold_file.py
    test_blind_module_has_no_gold_dependency.py
    test_attribution_chain_counts.py
    test_zero_intervention_metrics_are_null.py
    test_net_benefit_equals_derived_accuracy.py
    test_ordering_gold_after_intervention.py
    test_ledger_hash_immutability.py
    test_finqa_serializer_deterministic.py
    test_tatqa_serializer_deterministic.py
    test_parser_fixtures.py
    test_fcg_eligibility_gold_independent.py
    test_dataset_id_uniqueness.py

  results/
    finqa_intervention_table.json
    tatqa_intervention_table.json
    finqa_fcg_feasibility.json
    tatqa_fcg_feasibility.json
```

Generated ledgers/results are immutable once hashed. Re-runs use
versioned filenames; no result artifact is silently overwritten.

------------------------------------------------------------------------

## 14. Primary paper evidence package

The minimum complete evidence package for the paper is:

### FinQA

-   fresh raw ledger;
-   blind DVL intervention ledger;
-   aggregate transition table;
-   per-rule table;
-   bootstrap CIs;
-   paired McNemar result;
-   FCG structural coverage and applicable FCG analysis.

### TAT-QA

-   fresh raw ledger;
-   blind DVL intervention ledger;
-   identical aggregate metrics;
-   per-rule transfer table;
-   bootstrap CIs;
-   paired McNemar result;
-   FCG structural coverage and applicable FCG analysis.

### Cross-dataset

Report, side-by-side:

-   coverage;
-   successful-correction rate;
-   harm rate;
-   correctness-preserving intervention rate;
-   intervention precision;
-   net benefit;
-   baseline/post accuracy;
-   per-rule firings and transitions;
-   FCG structural coverage;
-   FCG intervention metrics where inferentially eligible.

The intended scientific comparison is **intervention behavior**, not
leaderboard rank.

------------------------------------------------------------------------

## 15. Explicitly out of scope

The primary paper will not claim:

-   that DVL outperforms Chain-of-Thought;
-   a "42×" or similar multiplier;
-   SOTA FinQA performance;
-   that historical 42.61%, 38.50%, 32.00%, 24.00%, or 1.00% values are
    reproduced;
-   that a zero-firing sign rule was empirically validated;
-   FCG generalization from a dataset with fewer than 30 structurally
    eligible examples;
-   human-reviewed labels where no human review occurred.

The 42,354-vote eligibility ensemble, Phase 9C corpus annotation, and
Identity-Aware Verification protocol remain outside this fresh paper's
primary experiments.

------------------------------------------------------------------------

## 16. Freeze statement

The methodological decisions previously labeled D1--D5 are resolved:

-   **D1:** no new sign heuristic; blind sign correction may be
    structurally inactive.
-   **D2:** official FinQA repository only; immutable revision and byte
    hash locked mechanically before execution.
-   **D3:** immutable base-model and adapter revisions locked
    mechanically before execution.
-   **D4:** raw ledgers are self-contained with question and exact
    serialized context, but contain no gold.
-   **D5:** 30 structurally eligible examples per dataset is the
    threshold for inferential/main-table FCG analysis; structural
    coverage is always reported.

Additional frozen decisions:

-   FinQA uses pre-text + table + post-text, not pre-text-only
    historical truncation.
-   TAT-QA uses complete available evidence subject to the same
    token-budget principles, not a historical 2,000-character
    truncation.
-   Bootstrap uses 10,000 resamples.
-   Small-discordance McNemar uses the exact test.
-   "No-op-among-firings" is replaced by **correctness-preserving
    intervention rate**.
-   FinQA, TAT-QA, and FCG are all core components of the study, with
    FCG inferential claims conditional only on the predeclared
    structural sample-size rule.

**After this file is hashed and committed, Sections 1--16 may not be
altered in response to experimental outcomes. Any necessary
methodological change requires a separately named, timestamped, hashed,
and committed amendment made before the affected outcome-producing
run.**

------------------------------------------------------------------------

*End of frozen methodology protocol.*
