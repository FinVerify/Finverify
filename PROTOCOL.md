FinVerify Identity-Aware Verification
Experimental Protocol — v3 (Final pre-result candidate)
Study: Identity-Aware Verification of Numerical Financial Claims
Working paper title: Beyond Numerical Coincidence: Identity-Aware Verification of AI-Generated Financial Claims
Protocol lineage: v3 supersedes v2 after the implementation audit that distinguished enforced verification semantics from extracted-only identity metadata and identified the need for Phase 7G canonical verification consolidation.
Status: FINAL CANDIDATE — freeze only after Phase 7G passes re-audit and all placeholders in Section 10 are recorded.
1. Purpose and Scientific Scope
This protocol pre-specifies the evaluation of semantic numerical coincidence in financial claim verification: cases in which a claim and candidate evidence numerically agree while referring to different financial facts. Its purpose is to constrain researcher degrees of freedom before central TEST execution.
The study asks one narrow question:
When does numerical agreement constitute valid evidence for an AI-generated financial claim, and how do the financial identity constraints actually enforced by frozen FinVerify affect false verification and verification coverage?
The study is explicitly designed so that FinVerify can fail. No expected performance value, minimum effect size, minimum coverage, or acceptance-oriented target is specified.
The study does not claim that FinVerify solves financial hallucination generally.
It does not claim deterministic verification is universally superior to learned verification.
It does not claim state-of-the-art financial question answering.
It does not claim that all represented identity dimensions are enforced by the current verifier.
It does not treat post-hoc correction as evidence that the original model output was correct.
It does not require positive results for the study to be reportable.
2. Core Definitions
2.1 Semantic numerical coincidence
Semantic numerical coincidence occurs when claim and evidence satisfy the frozen numerical agreement rule while failing to refer to the same financial fact. Controlled adversarial pairs deliberately hold the numerical value constant so numeric matching alone cannot distinguish SUPPORT from identity mismatch.
2.2 Claim-evidence support
The verification task is: Does the supplied evidence independently support the specific financial assertion represented by the claim? It is not: Are the numbers equal? It is also not: Is the claim globally true somewhere else?
2.3 Gold labels
Label
Definition
SUPPORT
The supplied evidence independently establishes the claim for the relevant financial fact and value.
REJECT
The supplied evidence establishes an explicit incompatibility or a different financial fact.
INSUFFICIENT
The supplied evidence does not establish SUPPORT, but does not establish an explicit incompatibility strongly enough for REJECT.


2.4 System outputs
Output
Meaning
VERIFIED
The original/raw claim value is supported by compatible evidence under frozen enforced semantics.
VERIFIED_WITH_CORRECTION
The raw value is not verified; an actual post-hoc correction is supported by compatible evidence.
REJECTED
An explicit incompatibility is detected under an enforced comparison.
UNRESOLVED
The verifier cannot establish support or explicit rejection.
EVIDENCE_UNAVAILABLE
Required evidence is unavailable.
UNMAPPED
The claim cannot be mapped into the required verification representation.


3. Implementation Reality: Frozen Scientific Boundary
Protocol v3 distinguishes what the frozen system enforces from what it merely extracts or represents. The paper must never describe an extracted-only attribute as an implemented claim-evidence gate.
Dimension
Frozen role after 7G
Permitted scientific use
Value
ENFORCED
Primary verification and numeric baseline.
Concept
ENFORCED
Primary identity ablation and controlled challenge.
Period
ENFORCED
Primary identity ablation and controlled challenge.
Raw vs corrected provenance
ENFORCED, but NOT an identity gate
Separate provenance experiment.
Scope
EXTRACTED/REPRESENTED; not independent claim-evidence enforcement
Extraction evaluation and diagnostic challenge.
Accounting basis
EXTRACTED/REPRESENTED; not independent enforcement
Extraction evaluation and diagnostic challenge.
Temporal frame
EXTRACTED/REPRESENTED; not independent enforcement
Extraction evaluation and diagnostic challenge.
Value role
EXTRACTED/REPRESENTED; not independent enforcement
Extraction evaluation and diagnostic challenge.
Entity
NOT an independent frozen verification gate
Gold/dataset diagnostic analysis only unless re-audit proves pre-existing canonical enforcement without adding new semantics.


No new Entity, Scope, Accounting-Basis, Temporal-Frame, or Value-Role claim-evidence gate may be added for this study after protocol freeze. Diagnostic failures in these dimensions are results, not implementation tickets.
4. Research Questions
RQ
Question
RQ1 — Primary
Does enforced financial identity verification (Value + Concept + Period) reduce false verification relative to numerical agreement alone on controlled semantic numerical coincidences?
RQ2 — Utility
What happens to control retention, verification recall, coverage, and abstention as enforced identity constraints are added?
RQ3 — Enforced dimensions
What incremental behavior is attributable to Concept and Period enforcement?
RQ4 — Diagnostic dimensions
Which same-number mismatches remain unresolved or falsely verified in dimensions not independently enforced by the frozen verifier (Entity, Scope, Accounting Basis, Temporal Frame, Value Role)?
RQ5 — Pipeline realization
How much performance is lost when Concept/Period information is obtained from the frozen extraction pipeline rather than supplied from adjudicated gold metadata, where the experiment interface validly permits both conditions?
RQ6 — Ecological validity
Do false verification and identity-related failures occur in naturally sampled financial claim-evidence pairs?
RQ7 — Provenance
How does separating original-output verification from successful post-hoc correction change reported verification behavior?
RQ8 — Extraction
How reliably does frozen 7F recover the identity/context attributes on which verification and diagnostic analysis depend?


5. Hypotheses and Primary Estimand
5.1 H1 — Primary
On Controlled TEST REJECT examples belonging to the primary enforced challenge, A2 (Value + Concept + Period) will have lower False Verification Rate than A0 (Value only).
Primary estimand: ΔFVR = FVR_A2 - FVR_A0. Negative values favor enforced identity verification.
5.2 H2 — Utility trade-off
Any reduction in false verification may be accompanied by reduced control retention, verification recall, or coverage and/or increased abstention. No direction or magnitude is assumed.
5.3 H3 — Pipeline loss
Where a valid Gold-vs-Extracted condition can be constructed without inventing new verifier semantics, extraction errors may reduce the benefit observed under gold Concept/Period metadata. This is secondary.
5.4 H4 — Diagnostic boundary
Frozen FinVerify may remain vulnerable to semantic numerical coincidences in identity dimensions that it represents but does not independently enforce. These results are descriptive boundary evidence, not failed ablation rows.
5.5 H5 — Provenance
Collapsing VERIFIED_WITH_CORRECTION into VERIFIED will overstate original model correctness whenever successful corrections occur.
6. Interpretation of Outcomes
Strong enforced-identity evidence: A2 reduces FVR relative to A0 with useful control retention and compatible Natural Set evidence.
Safety-through-abstention: FVR falls but coverage/control retention falls materially; report the trade-off without calling it an unqualified improvement.
Pipeline bottleneck: gold Concept/Period verification is stronger than extracted end-to-end behavior.
Controlled-only evidence: strong controlled effect but weak/inconclusive Natural Set behavior; restrict ecological claims.
Diagnostic boundary: non-enforced dimensions remain important false-verification modes; report them as current limitations/future verification targets.
Inconclusive: effect estimate favors A2 but uncertainty includes no reduction.
Unsupported/contradicted: A2 produces little reduction or higher FVR. The primary hypothesis is not supported.
7. Phase 7G Pre-Freeze Requirement
Phase 7G is the final permitted pre-paper correctness phase. It must consolidate already-existing 7C/7D/7E semantics into a canonical evidence-backed verification path. It must not implement new identity capabilities.
VERIFIED must require independently obtained evidence, frozen value matching, concept compatibility, and period compatibility.
The raw value is checked first.
A supported raw value yields VERIFIED even if a later correction is unnecessary or wrong.
A raw mismatch followed by an actual supported correction yields VERIFIED_WITH_CORRECTION.
Unsupported raw and corrected values do not yield VERIFIED.
Evidence unavailability cannot be converted into verification merely because DVL produced a numeric value.
The production/canonical path and transcript verification path must share the same meaning of verification.
7G must add no Entity, Scope, Accounting-Basis, Temporal-Frame, or Value-Role enforcement.
If 7G cannot meet these conditions without inventing new retrieval or identity semantics, protocol freeze stops and the blocker is documented before dataset construction.
8. Code Freeze Rule
After the Phase 7G research commit is frozen, TEST failures are experimental observations by default. FinVerify must not be modified merely because an individual TEST example performs poorly.
8.1 Permitted post-freeze correction
A field specified by frozen semantics is accidentally dropped during transport.
An implementation comparison is inverted.
The runner evaluates a different field/configuration than specified.
A deterministic crash prevents execution of already-frozen semantics.
A reproducible implementation defect causes the code to violate the frozen protocol.
8.2 Forbidden post-freeze optimization
Adding a concept because TEST exposes an unsupported concept.
Adding a regex because TEST extraction failed.
Adding any diagnostic identity gate because its challenge results are poor.
Changing UNKNOWN behavior, tolerance, thresholds, mapping, or retrieval to improve TEST.
Removing difficult TEST examples or reclassifying them based on system behavior.
8.3 Bug procedure
Preserve the original run and commit.
Document the defect and why it violates frozen semantics.
Implement the smallest correction in a new commit.
Do not change the dataset.
Rerun the entire affected evaluation.
Preserve pre-fix and post-fix artifacts.
Record the deviation in PROTOCOL_DEVIATIONS.md and disclose it where material.
9. Verification Semantics
9.1 Tri-state identity comparison
For enforced identity dimensions, comparison state is MATCH, MISMATCH, or UNKNOWN.
MATCH: available information establishes compatibility.
MISMATCH: available information establishes incompatibility.
UNKNOWN: available information is insufficient to establish compatibility.
UNKNOWN + UNKNOWN is not MATCH.
A required UNKNOWN cannot yield raw VERIFIED.
9.2 Missing information
Known enforced mismatch -> REJECTED
Required enforced identity unknown -> UNRESOLVED
All required enforced identities match + value matches -> VERIFIED
Raw unsupported + actual supported correction -> VERIFIED_WITH_CORRECTION
9.3 Numerical agreement
A0 and all verifier configurations must use the exact frozen FinVerify evidence-value comparison rule, including tolerance, normalization, and near-zero behavior. The experiment code must call or exactly reuse the canonical frozen implementation rather than silently approximating it.
The exact rule and function path must be recorded after 7G re-audit.
10. Freeze Manifest — Must Be Completed Before Dataset Construction
Item
Required recorded value
FinVerify commit SHA
TBD after 7G
FinVerify research tag
paper-identity-v1 or final recorded tag
Full regression output
TBD; must include all existing + 7G tests, 0 failures
Python version
TBD
Dependency lock/hash
TBD
Freeze timestamp (IST/UTC recorded)
TBD
Canonical verification function/module
TBD after 7G
Frozen numeric tolerance semantics
TBD after 7G
Concept UNKNOWN semantics
TBD after 7G
Period UNKNOWN semantics
TBD after 7G
Protocol SHA256
TBD after final review
Protocol Git commit
TBD


Dataset construction must not begin until all implementation-dependent TBD fields above are resolved and the protocol is hashed/committed.
11. Primary Enforced Identity Ablation
The cumulative enforcement experiment is deliberately limited to semantics the frozen verifier actually enforces.
Configuration
Required conditions
A0 — Numeric
Value agreement only.
A1 — + Concept
Value agreement AND Concept compatibility.
A2 — + Period (Primary full enforced configuration)
Value agreement AND Concept compatibility AND Period compatibility.


A0 vs A2 is the single primary comparison. A1 is the pre-specified intermediate ablation. Provenance is not A3 and diagnostic identity dimensions are not appended to this ladder.
If Phase 7G re-audit shows that A0/A1/A2 cannot be implemented as toggles without altering production semantics, the experiment harness may implement faithful evaluation configurations outside production code, provided each configuration exactly applies the frozen comparison functions and is independently tested.
12. Provenance Experiment
Provenance is scientifically distinct from identity alignment.
Condition
Interpretation
Raw-supported
Original value matches compatible evidence -> VERIFIED.
Corrected-supported
Original value fails; actual correction matches compatible evidence -> VERIFIED_WITH_CORRECTION.
Neither supported
Neither raw nor valid corrected value is supported -> non-verified status.


The paper must never merge raw correctness and corrected success without explicitly naming the combined operational measure.
Correction Precision = valid VERIFIED_WITH_CORRECTION / all VERIFIED_WITH_CORRECTION, undefined if denominator is zero.
13. Controlled Challenge Set
13.1 Purpose
The Controlled Set isolates semantic numerical coincidence. For adversarial examples, the numerical value is held constant while exactly one target identity dimension changes.
13.2 Source claims
Select approximately 15–20 independent real source claims before observing central TEST results. Every source claim receives a stable source_group_id. Split source groups before perturbation generation.
13.3 Matched controls
Every source claim used for adversarial variants must have at least one legitimate SUPPORT control with the same underlying financial fact.
13.4 Primary Enforced Challenge
The primary controlled challenge contains only dimensions directly enforced by A1/A2:
Concept shift
Period shift
These examples support the causal primary analysis.
13.5 Diagnostic Challenge
A separate diagnostic set may contain financially meaningful same-number shifts in:
Entity
Scope
Accounting Basis
Temporal Frame (e.g., actual vs guidance)
Value Role (e.g., current vs comparison)
Diagnostic examples must not be presented as tests of corresponding FinVerify gates. They ask where the frozen system remains vulnerable.
13.6 Transformation integrity
Numerical value remains unchanged.
Exactly one target identity dimension changes for single-dimension analysis.
Non-target dimensions remain invariant unless an unavoidable dependency is documented.
Evidence remains grammatical and financially interpretable.
The transformation creates a genuine SUPPORT -> REJECT transition.
No artificial lexical marker is inserted merely to reveal the label.
Source provenance remains traceable.
13.7 Controlled validation
Automated validation covers 100% of generated pairs: value invariance, target change, non-target invariance where applicable, schema validity, duplicate IDs, source-group integrity, and split integrity.
Manual construction validation covers 100% of source templates/matched controls and at least 20% of generated adversarial variants selected with a fixed seed. This validation occurs before central TEST execution and concerns dataset correctness, not FinVerify performance.
14. Controlled DEV/TEST Split
Split by source_group_id BEFORE perturbation generation. No variants from the same source claim may cross splits.
Target DEV: approximately 30–40% of source groups.
Target TEST: approximately 60–70% of source groups.
Candidate deterministic seed: 20260804.
Avoid manual stratification unless a split is catastrophically concentrated; any reassignment must occur before perturbation generation and be recorded.
Once TEST is frozen, record dataset SHA256, number of examples, source groups, construction-script commit, seed, and timestamp. TEST cannot be edited based on system behavior.
15. Natural Financial Claim Set
15.1 Purpose
The Natural Set evaluates ecological validity on unperturbed financial material and must not be constructed solely from previously observed FinVerify failures.
15.2 Frozen source universe
Initial company universe: AAPL, TSLA, JPM, NVDA, MSFT, GS — the companies already used during pre-study development. Exact source documents must be frozen before sampling.
For each document record company, ticker, document type, document date, stable source identifier/reference, and document hash.
15.3 Sampling rule
Freeze source documents.
Identify candidate numerical financial claims using a pre-defined procedure independent of eventual FinVerify success.
Apply content-level eligibility criteria.
Associate candidate evidence using the frozen evidence-construction/retrieval procedure.
Assign source_group_id.
Apply any pre-declared DEV/TEST designation if Natural examples are used for development.
Sample using the frozen seed/procedure.
Human-annotate the resulting pairs.
Only after gold labels are frozen run final Natural TEST evaluation.
Natural eligibility must not require numeric agreement, successful concept/period extraction, successful 7F tagging, successful mapping, or FinVerify success.
15.4 Eligibility
The claim makes a numerical financial assertion.
The claim originates from a frozen source.
Candidate evidence can be represented and shown to annotators.
The pair is intelligible to a qualified annotator using supplied material.
The example is not a duplicate.
Evaluation does not require inaccessible private information.
15.5 Exclusions
Exclude only for pre-defined content/data reasons: non-numerical claim, corrupted source text, duplicate pair, unavailable evidence span due to data corruption, unintelligible pair even with supplied context, or a claim requiring external information not included in annotation material.
Do not exclude because FinVerify fails, abstains, cannot map/extract identity, values differ, the example is difficult, or annotators disagree.
15.6 Size
Target approximately 60–100 Natural pairs. No expansion is permitted merely because TEST results are weak. Any later collection is a separately declared replication/extension set.
16. Natural DEV/TEST Policy
If the Natural Set is used only for frozen end-to-end evaluation and no parameter, prompt, threshold, rule, or code is tuned on it, it may be treated as an independent evaluation set. If any Natural examples are used for development, they must be designated DEV before such use and excluded from Natural TEST.
The final dataset manifest must state which policy was used.
17. Human Annotation
17.1 Scope
Human annotation is primarily required for the Natural Set. Controlled labels arise from validated transformation rules, though controlled construction integrity is manually checked.
17.2 Annotation question
Does the supplied evidence independently support the financial claim?
Annotators choose exactly one: SUPPORT, REJECT, INSUFFICIENT.
17.3 Instructions
Evaluate only the supplied claim/evidence/context.
Do not search the web to determine whether the claim is true elsewhere.
SUPPORT requires enough evidence to establish the claim.
REJECT requires evidence of incompatibility or a different financial fact.
INSUFFICIENT means support is not established but explicit incompatibility is also not established.
17.4 Reason field
For REJECT or INSUFFICIENT, annotators may select all applicable descriptive reasons: Entity, Concept, Period, Scope, Accounting Basis, Temporal Frame, Value Role, Value, Missing Information, Other. Reasons do not determine the primary label.
17.5 Blinding
Annotators must not see FinVerify outputs, gold/extracted metadata, perturbation labels, expected gate failures, prior system failures, or paper results.
17.6 Recruitment and assignment
Preferred participants have exposure to finance, accounting, financial analysis, FinTech, economics with statement familiarity, or CA/CFA-oriented study.
Target >=3 independent valid annotations per Natural example.
Google Forms or equivalent may use batches of approximately 10 examples.
Continue recruitment until each example reaches the frozen minimum or the pre-declared annotation deadline is reached.
Do not selectively obtain extra annotations only for inconvenient disagreements.
Additional valid responses received before a form closes are retained.
17.7 Agreement
Primary agreement statistic: Krippendorff's alpha, nominal, three-class (SUPPORT/REJECT/INSUFFICIENT), computed on independent raw annotations before adjudication. Also report raw exact agreement. Binary SUPPORT vs NON-SUPPORT agreement may be descriptive only.
17.8 Gold aggregation
Primary aggregation is majority vote. If no majority exists, use blinded adjudication. The adjudicator must not see FinVerify predictions. Preserve raw annotations, majority result, adjudicated result, and reason selections separately.
17.9 Annotation QC
Provide a concise instruction page and training examples not present in evaluation. Exclude responses only under pre-defined validity criteria such as incomplete/invalid submissions or compromised independence. Never exclude an annotator because they disagree with researchers.
18. Gold and Extracted Identity
18.1 Gold metadata
Gold identity/context fields are derived from dataset construction and adjudicated source interpretation independently of FinVerify predictions. They may include entity, concept, period, scope, accounting_basis, temporal_frame, and value_role.
18.2 Gold-vs-Extracted restriction
Gold metadata does NOT create verifier capabilities that do not exist. The primary Gold-vs-Extracted pipeline comparison is restricted to Concept and Period, and only where the frozen experiment interface can supply these fields without changing verification semantics.
Entity/Scope/Basis/Frame/Value-Role gold fields remain useful for annotation, controlled diagnostic construction, extraction scoring, and error analysis, but are not injected as fictional enforcement gates.
18.3 Pipeline gap
For a metric M, Δ_pipeline = M_Gold(C,P) - M_Extracted(C,P). This is secondary/descriptive unless a specific inferential test is frozen before TEST.
19. Extraction Evaluation
Use approximately 100 real financial sentences/spans sampled independently of extraction success. Gold annotations cover applicable numeric value, entity, concept, period, scope, accounting basis, temporal frame, and value role.
Field
Primary reporting
Numeric claim/value
Instance-level precision, recall, F1.
Entity
Representation-appropriate exact/span/categorical metric; explicitly note if FinVerify does not independently extract entity.
Concept
Exact canonical-concept accuracy among gold claim instances + missing/unmapped rate.
Period
Structured period match rate + UNKNOWN rate.
Scope
Accuracy, macro-F1 where meaningful, UNKNOWN rate.
Accounting basis
Accuracy, macro-F1 where meaningful, UNKNOWN rate.
Temporal frame
Accuracy, macro-F1 where meaningful, UNKNOWN rate.
Value role
Accuracy, macro-F1 where meaningful, UNKNOWN rate.
Pipeline exact match
All-required-extracted-fields exact match, with the included field set explicitly stated.


Do not force meaningless P/R/F1 formulations merely for table symmetry.
20. Primary Metrics
20.1 False Verification Rate — primary
For Controlled primary REJECT examples: FVR = N(Gold REJECT and System VERIFIED) / N(Gold REJECT).
Only raw VERIFIED counts as positive verification in the primary provenance-preserving FVR. VERIFIED_WITH_CORRECTION is reported separately.
20.2 Unsafe Support Rate — secondary
USR = N(Gold in {REJECT, INSUFFICIENT} and System VERIFIED) / N(Gold in {REJECT, INSUFFICIENT}).
20.3 Verification Precision
VP = N(Gold SUPPORT and System VERIFIED) / N(System VERIFIED). If no VERIFIED outputs occur, VP is undefined, not 0 or 1.
20.4 Verification Recall
VR = N(Gold SUPPORT and System VERIFIED) / N(Gold SUPPORT). Corrected verification is excluded.
20.5 Raw decision coverage
Coverage_raw = [N(VERIFIED) + N(REJECTED)] / N_total.
20.6 Abstention
Raw abstention statuses are UNRESOLVED, EVIDENCE_UNAVAILABLE, and UNMAPPED. Report each separately and their combined rate. Because VERIFIED_WITH_CORRECTION is a separate provenance path, do not assert AR = 1 - Coverage_raw unless using a separately defined mutually exhaustive operational grouping.
20.7 Strict Attack Rejection
SAR = N(Controlled REJECT and System REJECTED) / N(Controlled REJECT).
20.8 Safe Non-Verification
SNVR = N(Controlled REJECT not marked VERIFIED) / N(Controlled REJECT). Under complete primary raw statuses, FVR = 1 - SNVR.
20.9 Control Retention
CR = N(Matched SUPPORT control and System VERIFIED) / N(Matched SUPPORT controls). VERIFIED_WITH_CORRECTION does not count as retained raw verification.
20.10 Status distribution
Every major evaluation reports counts/rates for VERIFIED, VERIFIED_WITH_CORRECTION, REJECTED, UNRESOLVED, EVIDENCE_UNAVAILABLE, and UNMAPPED.
21. Primary Statistical Inference
The single primary comparison is A0 vs A2 on Controlled TEST REJECT examples. The primary outcome is ΔFVR = FVR_A2 - FVR_A0.
21.1 Source-cluster bootstrap
Use source_group_id as the resampling unit.
Sample source groups with replacement.
Include all controlled examples belonging to each selected group.
Compute FVR_A0 and FVR_A2.
Compute paired ΔFVR.
Repeat 10,000 times.
Report the 95% bootstrap interval for ΔFVR.
The primary conclusion is based on effect magnitude and uncertainty, not an arbitrary p-value threshold.
21.2 CI interpretation
Interval entirely below zero: evidence supports reduced FVR under A2.
Interval overlaps zero: inconclusive at the current sample size; not evidence of equivalence.
Interval entirely above zero: evidence that A2 increases FVR relative to A0.
21.3 Other confidence intervals
Controlled metrics use source-cluster bootstrap. Natural metrics use the appropriate document/source grouping whenever multiple examples share a source unit. Target 10,000 bootstrap replicates and 95% intervals.
21.4 McNemar
Standard McNemar may be reported only as a secondary sensitivity analysis if the unit-of-analysis assumptions are defensible. No improvised 'cluster-adjusted McNemar' is permitted.
21.5 Multiple comparisons
There is one primary comparison. A1, diagnostic dimensions, Natural comparisons, baselines, Gold-vs-Extracted, extraction analyses, and provenance analyses are secondary/exploratory unless explicitly promoted before TEST execution.
22. Baselines
22.1 Numeric baseline
A0 is the primary numeric baseline and uses the same frozen value-matching rule as FinVerify.
22.2 Embedding baseline
Use one fixed named sentence-embedding model selected and recorded before TEST execution. Input is claim text + evidence text; similarity is cosine; prediction is SUPPORT vs NON-SUPPORT.
Threshold tau is selected only on DEV using Balanced Accuracy over SUPPORT vs NON-SUPPORT (REJECT + INSUFFICIENT). Freeze tau_DEV. No TEST retuning.
The exact model identifier/revision, pooling, normalization, library version, and threshold must be recorded before central TEST.
22.3 LLM Judge — secondary/optional
If included, use one pre-specified strong model with a frozen neutral prompt asking whether the supplied evidence independently supports the claim and requiring SUPPORT/REJECT/INSUFFICIENT. Do not enumerate FinVerify's identity gates in the prompt.
Temperature 0 where supported.
One primary run per example.
Freeze provider/model/version/date/API parameters/prompt hash/parser before TEST.
Malformed outputs follow a frozen parser rule, not manual repair.
Omission due to time/API constraints does not invalidate the primary study and must be disclosed.
LLM Judge inclusion decision deadline: before the first central TEST run. Once central TEST begins, do not substitute a different model because results are inconvenient.
23. Diagnostic Identity Challenge
The diagnostic challenge is deliberately non-primary. It measures semantic numerical coincidences outside current enforced Concept/Period semantics.
For each diagnostic dimension report, where sample size permits: FVR/unsafe verification, SAR, SNVR, control retention for associated controls, status distribution, and qualitative error examples.
Do not describe improvement/failure as the effect of a nonexistent gate. The correct interpretation is whether frozen FinVerify already handles or remains vulnerable to that mismatch through its existing semantics.
24. Natural Evaluation
Run frozen end-to-end FinVerify on Natural TEST only after annotation/gold labels are frozen. Report the complete status distribution plus VP, VR, FVR on Gold REJECT, USR over NON-SUPPORT, coverage, abstention, and bootstrap intervals using the appropriate source cluster.
Every Natural TEST false verification must be inspected and included in error analysis. Do not fix the system in response.
25. Error Analysis
For every Natural TEST false verification record example_id, claim, evidence, gold label, system output, gold metadata, extracted metadata, primary failure category, and notes.
Pre-defined categories: Entity, Concept, Period, Scope, Accounting Basis, Temporal Frame, Value Role, Value, Extraction Failure, Evidence Failure, Mapping Failure, Provenance Failure, Other.
OTHER is retained so unforeseen failures are not forced into an inappropriate category. Frequencies are descriptive.
26. FinVerifyBench-Numeric Continuity Track
The existing 500-example numerical track remains frozen as a historical benchmark artifact: Train 350 / Dev 75 / Test 75, subject to committed-file hashes.
Do not modify/re-stratify existing samples.
Do not claim all categories occur in all splits.
Do not repair known generator discrepancies in place during this study.
Historical synthetic fixtures such as random, scale_confused, sign_confused, magnitude_confused, arithmetic, and oracle_dvl must not be represented as empirical model/FinVerify results.
Any paper result on this track must come from an actual reproducible run.
The term oracle_dvl must not be reused for Gold Identity.
This track is secondary continuity evidence and cannot support the primary identity claim by itself.
27. Optional Downstream Evaluations
27.1 FinQA
Optional. Run only if prediction provenance is reliable or clean fresh inference can be performed. No new fine-tuning is required. FinQA cannot become the headline result.
27.2 TAT-QA
Optional with a strict two-hour integration budget. If integration requires architectural gymnastics or distracts from the central study, drop it and report that it was not included.
28. Result Provenance and Artifacts
Every quantitative paper result must trace from paper table/figure -> generated artifact -> CSV/JSON result -> runner -> dataset manifest/hash -> code commit.
No manually typed experimental number may be the sole source of a paper result.
28.1 Required run metadata
run_id and timestamp
git commit and dirty status
dataset hash and split
source-group manifest
random seed
Python version and dependency/environment identifier
system/ablation configuration
baseline model identifier/revision where applicable
prompt hash/API parameters where applicable
28.2 Expected result artifacts
results/
  enforced_identity_ablation.json
  enforced_identity_ablation.csv
  controlled_primary.csv
  controlled_diagnostic.csv
  natural_evaluation.csv
  natural_errors.csv
  provenance_evaluation.csv
  gold_vs_extracted.csv
  extraction_evaluation.csv
  numeric_benchmark.json
  embedding_baseline.json
  llm_judge.json                 # if included
  annotation_agreement.json
  annotation_raw.csv
  bootstrap_ci.json
  statistical_tests.json
  run_manifest.json
28.3 Generated paper artifacts
paper/generated/
  table_main.tex
  table_ablation.tex
  table_diagnostic.tex
  table_natural.tex
  table_extraction.tex
  table_baselines.tex
  table_provenance.tex
Manual LaTeX formatting is permitted only if numerical cells remain programmatically sourced.
29. Researcher Degrees of Freedom — Frozen Before TEST
Research questions and hypotheses
Primary comparison A0 vs A2
Primary outcome ΔFVR
Enforced-vs-diagnostic dimension classification
Gold label definitions
System-output mapping
UNKNOWN semantics
Frozen numeric tolerance
Controlled transformation rules
Source-group split procedure and seed
Natural eligibility/exclusion rules
Annotation instructions, minimum labels, stopping rule, aggregation and agreement statistic
Gold-vs-Extracted restriction to valid consumed fields
Embedding model and DEV threshold objective
LLM Judge inclusion decision/model/prompt if used
Cluster-bootstrap procedure
Error-analysis taxonomy
Result artifact schema
30. Explicitly Forbidden Practices
Changing TEST because FinVerify fails.
Changing FinVerify because TEST FVR is high.
Adding a diagnostic identity gate after seeing diagnostic failures.
Adding extraction rules because TEST extraction is poor.
Removing Natural examples because they are difficult, unmapped, abstained, value-mismatched, or disagreement-heavy.
Requiring successful extraction/mapping/value agreement for Natural eligibility.
Treating UNKNOWN + UNKNOWN as MATCH.
Treating abstention as explicit rejection.
Reporting FVR without coverage/control-retention/status context.
Merging VERIFIED and VERIFIED_WITH_CORRECTION without disclosure.
Treating corrected output as original model correctness.
Using Gold metadata to fabricate gates absent from frozen FinVerify.
Retuning embedding thresholds on TEST.
Changing perturbation rules after central TEST.
Selectively recruiting extra annotators only for inconvenient examples.
Overwriting raw annotations after adjudication.
Using AI-generated labels as human annotation.
Representing historical synthetic fixtures as empirical results.
Manually altering experimental numbers in the manuscript.
Promoting exploratory analyses because they look stronger.
Silently changing statistical methods after results are observed.
31. Protocol Deviations
Any post-freeze deviation must be recorded in PROTOCOL_DEVIATIONS.md with date, original rule, deviation, reason, whether results had been observed, affected examples/runs, old/new commits or hashes, and analysis impact.
Material deviations must be disclosed in the paper or supplement.
32. Pre-Result Claim Discipline
Before TEST, the following remain hypotheses:
Concept/Period identity enforcement may reduce false verification relative to numeric agreement.
Any reduction may trade off against coverage/control retention.
Extraction may limit end-to-end realization.
Semantic numerical coincidence may occur in Natural financial evidence.
Non-enforced identity dimensions may remain failure modes.
Provenance isolation may materially change the interpretation of verification success.
After experiments, wording such as demonstrates, proves, substantially, significantly, robust, and effective must be justified by observed evidence and the declared statistical analysis.
33. Dataset Construction Gate
PHASE 7G COMPLETE
        ↓
FULL REGRESSION + MANUAL CHECKS
        ↓
INDEPENDENT 7G RE-AUDIT
        ↓
FINVERIFY CODE FREEZE
        ↓
PROTOCOL v3 BLOCKER-ONLY REVIEW
        ↓
ACCEPTED CORRECTIONS
        ↓
PROTOCOL SHA256 + COMMIT
        ↓
DATASET CONSTRUCTION
No central TEST result may be observed before this gate is complete.
34. Experiment Execution Gate
FinVerify frozen
+ Protocol frozen
+ Controlled TEST frozen
+ Natural TEST frozen
+ Gold labels frozen
+ Annotation agreement computed
+ DEV-only baseline tuning complete
+ LLM Judge inclusion/model decision frozen
= CENTRAL TEST EXECUTION
Once central TEST execution begins, methodological changes are protocol deviations.
35. Required Primary Reporting Regardless of Outcome
The study commits to reporting FVR_A0, FVR_A2, ΔFVR with a 95% source-cluster bootstrap interval, together with A1, Control Retention, Strict Attack Rejection, Safe Non-Verification, Verification Recall, raw coverage, abstention/status distribution, and the diagnostic challenge boundary results.
Natural Set findings and provenance findings are reported separately and cannot be silently substituted for the primary result.
36. Scientific Decision Rule
H1 is supported by the Controlled Set when estimated FVR_A2 is lower than FVR_A0 and the source-cluster bootstrap interval for ΔFVR supports a reduction not readily explained by sampling uncertainty.
If the interval overlaps zero, describe the result as inconclusive, not equivalent. If the effect is near zero or favors A0, describe H1 as unsupported or contradicted as appropriate.
The Natural Set determines the strength of ecological-generalization claims separately. Diagnostic challenge results determine the documented boundary of current enforcement, not whether H1 is retroactively redefined.
37. Final Pre-Dataset Freeze Checklist
System
Phase 7G completed without adding new identity gates.
Full regression suite passes with 0 failures.
Manual canonical cases inspected.
Independent re-audit confirms canonical evidence-backed VERIFIED semantics.
Commit SHA/tag/environment/tolerance/UNKNOWN semantics recorded.
Protocol
A0/A1/A2 definitions frozen.
Provenance experiment separated.
Primary vs diagnostic challenge distinction frozen.
Primary metric and bootstrap frozen.
Embedding model selected and recorded.
LLM Judge inclusion rule/deadline frozen.
Protocol SHA256 and Git commit recorded.
Controlled data
Source-claim eligibility frozen.
Source groups split before perturbation.
Primary Concept/Period perturbations frozen.
Diagnostic perturbation dimensions frozen.
Transformation validators implemented.
Manual construction-validation rule frozen.
Natural data
Source documents and hashes frozen.
Sampling procedure frozen.
Eligibility/exclusion criteria frozen.
No extraction-success/value-agreement requirement.
Annotation
Google Form instructions finalized.
SUPPORT/REJECT/INSUFFICIENT definitions frozen.
Reason field frozen.
>=3 independent labels/example target frozen.
Recruitment stopping/deadline rule frozen.
Krippendorff alpha and adjudication procedure frozen.
Provenance
Dataset hashing implemented.
Run manifest implemented.
Raw annotations preserved.
Protocol deviation log exists.
Generated-table pipeline specified.
38. Final Principle
A number matching evidence is not equivalent to the financial claim being verified.
This study tests the narrower, implementation-faithful proposition that enforcing the financial identity constraints FinVerify actually supports — Concept and Period, in addition to Value — changes false-verification behavior under semantic numerical coincidence.
It separately measures provenance, extraction reliability, natural end-to-end behavior, and diagnostic identity failures that the current frozen verifier does not independently enforce.
The protocol is designed to reveal both what FinVerify solves and what it does not.
39. Freeze Status
PROTOCOL v3 STATUS: FINAL CANDIDATE — NOT YET HASH-FROZEN.
Required before hash freeze:
Complete Phase 7G.
Run full regression and manual canonical checks.
Perform independent 7G re-audit.
Fill Section 10 implementation-dependent values.
Select and record the exact embedding model/revision.
Run one blocker-only methodology review of this v3; accept only validity-critical corrections.
Decide/freeze LLM Judge inclusion and model before central TEST.
Commit the final protocol and record SHA256 + Git commit.
