# FinVerifyBench — Benchmark Design Document
**Version:** 1.0  
**Status:** Public Release Candidate  
**Grounded in:** "Structured Numerical Hallucinations in Financial LLMs: Deterministic Verification Outperforms Chain-of-Thought Prompting" (ACL ARR May 2026, #2935)

---

## 1. Target Sample Count by Error Category

Total: **500 samples**

| Error Category       | Target n | Rationale                                                        |
|----------------------|----------|------------------------------------------------------------------|
| scale_error          | 75       | Most common DVL-correctable error (% ↔ decimal)                 |
| sign_error           | 75       | Second most common; high impact (directional reversals)         |
| magnitude_error      | 90       | Dominant in FinQA (52.4% of DVL corrections); millions/billions |
| arithmetic_error     | 60       | Multi-step drift; distinct from scale                           |
| ratio_error          | 55       | margin/ROE/ROA/P-E — financially critical                       |
| percentage_error     | 55       | YoY%, CAGR, growth rate calculations                            |
| aggregation_error    | 30       | Sum/avg/max over table rows                                     |
| unit_conversion      | 30       | Millions→Billions→Thousands cross-unit                          |
| reasoning_error      | 30       | Multi-step drift, cross-step context loss                       |

**Note:** Samples can carry multiple error labels (avg 1.4 labels/sample).

> **Design-target disclaimer:** The table above records the *original design targets* used to parameterize the generator. The actual realized distribution differs materially from these targets — in particular, `scale_error` and `ratio_error` are significantly overrepresented. See **§5a** for the realized distribution and root cause.

---

## 2. Target Sample Count by Difficulty

| Difficulty | Target n | Definition                                                       |
|------------|----------|------------------------------------------------------------------|
| easy       | 150      | Single-step, unambiguous unit, one error class                  |
| medium     | 200      | Two-step, possible scale ambiguity, 1–2 error classes           |
| hard       | 150      | Multi-step, cross-table, unit conversion, 2+ error classes      |

---

## 3. Target Sample Count by Reasoning Type

| Reasoning Type           | Target n |
|--------------------------|----------|
| percentage_change        | 80       |
| multi_step_arithmetic    | 70       |
| ratio_calculation        | 70       |
| aggregation              | 50       |
| yoy_change               | 60       |
| margin_calculation       | 60       |
| growth_rate              | 40       |
| unit_conversion          | 30       |
| single_lookup            | 25       |
| comparative              | 15       |

---

## 4. Train / Dev / Test Split Strategy

| Split | n   | % | Purpose                                          |
|-------|-----|---|--------------------------------------------------|
| train | 350 | 70 | Model fine-tuning and DVL rule learning          |
| dev   | 75  | 15 | Hyperparameter tuning, intermediate evaluation   |
| test  | 75  | 15 | Final held-out evaluation — do not overfit       |

**Split rules:**
- Stratify by error_category to ensure all categories appear in all splits
- No template reuse across splits (checked by cosine similarity of context strings)
- test split released without ground_truth in public leaderboard mode

---

## 5. Statistical Balance Requirements (Original Targets)

The following balance constraints were the *original design targets* for the generator. They are retained here as documentation of intent, **not** as a claim that they are met by the current 500-sample release.

- **Target:** No single error_category may exceed 20% of total samples
- **Target:** No single reasoning_type may exceed 18% of total samples  
- **Target:** Difficulty distribution must fall within ±5pp of targets
- Underestimation/overestimation baseline ratio should be ~60/40 (matching paper's 60.9%)
- Ground-truth value distribution: log10(|gt|) should span [-2, 6] (from 0.01 to 1M)

### §5a — Actual Realized Distribution

The current 500-sample dataset does **not** meet the ≤20% / ≤18% balance targets stated above. The actual distributions, reproduced from [`data/processed/statistics.md`](data/processed/statistics.md), are as follows:

**Error Category Distribution (actual):**

| Category | Count | % | Target | Δ from target |
|----------|-------|---|--------|---------------|
| scale_error | 170 | 34.0% | 75 (15.0%) | +19.0pp ⚠️ |
| ratio_error | 165 | 33.0% | 55 (11.0%) | +22.0pp ⚠️ |
| sign_error | 95 | 19.0% | 75 (15.0%) | +4.0pp |
| percentage_error | 75 | 15.0% | 55 (11.0%) | +4.0pp |
| aggregation_error | 75 | 15.0% | 30 (6.0%) | +9.0pp |
| arithmetic_error | 70 | 14.0% | 60 (12.0%) | +2.0pp |
| magnitude_error | 40 | 8.0% | 90 (18.0%) | −10.0pp |
| unit_conversion | 30 | 6.0% | 30 (6.0%) | 0pp |
| rounding_error | 10 | 2.0% | — | — |
| context_confusion | 5 | 1.0% | — | — |

*Multi-label — samples carry more than one category (avg ~1.4 labels/sample), so percentages sum to >100%.*

**Difficulty Distribution (actual):**

| Difficulty | Count | % | Target | Δ from target |
|------------|-------|---|--------|---------------|
| easy | 230 | 46.0% | 150 (30.0%) | +16.0pp |
| medium | 185 | 37.0% | 200 (40.0%) | −3.0pp |
| hard | 85 | 17.0% | 150 (30.0%) | −13.0pp |

**Reasoning Type Distribution (actual):**

| Reasoning Type | Count | % |
|----------------|-------|---|
| ratio_calculation | 140 | 28.0% |
| margin_calculation | 100 | 20.0% |
| yoy_change | 85 | 17.0% |
| multi_step_arithmetic | 80 | 16.0% |
| single_lookup | 70 | 14.0% |
| aggregation | 60 | 12.0% |
| percentage_change | 55 | 11.0% |
| unit_conversion | 40 | 8.0% |
| growth_rate | 20 | 4.0% |

`ratio_calculation` at 28.0% exceeds the original ≤18% target.

**Root cause:** The imbalance is a consequence of generator template weighting in `scripts/create_dataset.py`. The generator uses fixed-size blocks of factory calls (e.g., 40 gross-margin samples, 25 operating-margin samples, 20 net-profit-margin samples, etc.). Many template families — particularly margin and ratio calculations — co-tag `scale_error` and `ratio_error` because those error types are intrinsic to how percentage-vs-decimal and ratio-calculation errors manifest. The large number of ratio/margin template families (ROE, ROA, current ratio, D/E, P/E, interest coverage, dividend yield, inventory turnover, etc.) collectively produce many more `ratio_error` and `scale_error` labels than the per-category targets anticipated. This is a generator design choice (more templates for financially common ratio calculations), not a post-hoc filtering failure.

**χ² statistic:** The reported `error_category χ² = 406.84` in `statistics.md` is a descriptive measure of deviation from uniform distribution across the 10 error categories. For reference: under a uniform null (equal expected count per category), with df = 9, this value corresponds to p ≪ 0.001, confirming the distribution is far from uniform. This χ² value quantifies the imbalance documented above; it should not be read as evidence that the balance requirement was met.

---

## 6. Annotation Guidelines

Each sample requires:

```
question     — natural financial English, ≥ 10 words
context      — realistic statement excerpt with units in header
ground_truth — mathematically verified, finite float
unit         — canonical unit from Unit enum
error_category — list; at least one from taxonomy
difficulty   — infer_difficulty() or human override
reasoning_type — list; at least one step
```

**Verification protocol:**
1. Compute ground_truth independently using Python (show workings in `_derivation` field during creation)
2. Cross-check against context numbers — all operands must appear in context
3. Validate with `validate_sample()` — zero tolerance for schema errors

---

## 7. Quality-Control Process

> **Status note:** Automated schema validation (`validate_dataset()`) and mathematical verification (`verify_calculations.py`) have been run and pass at 100% for all 500 samples. These checks are enforced as part of the generation and release workflow. The human-review process described in the last row of the table below (10% random sample reviewed by a second annotator) has **not yet been executed** on the current 500-sample release. When human review is conducted, raw annotation data and inter-annotator statistics should be checked into a new `annotation/` subdirectory within `finverify-bench/`, not just summarized in prose.

| Step | Method | Status |
|------|--------|--------|
| Automated schema validation | `validate_dataset()` — blocks invalid samples | ✅ Executed |
| Mathematical verification   | `verify_calculations.py` — re-derives every answer | ✅ Executed |
| Duplicate detection         | Cosine similarity on (question + context) pairs | ✅ Executed |
| Template overlap detection  | Structural fingerprinting of context format | ✅ Executed |
| Class balance check         | Chi-squared test on category distribution | ✅ Executed (see §5a for results) |
| Human review                | 10% random sample reviewed by second annotator | ⏳ Planned — not yet executed |

---

## 8. Inter-Annotator Agreement (Planned — Not Yet Executed)

> **This section describes a planned quality-assurance process. It has not been executed on the current 500-sample release.** No annotation logs, computed α/κ values, or adjudication records currently exist in the repository. When this process is conducted, results and raw data should be checked into `finverify-bench/annotation/`.

- **Label set:** error_category (multi-label), difficulty (3-class)
- **Metric:** Krippendorff's α for error_category; Cohen's κ for difficulty
- **Target:** α ≥ 0.70 (substantial), κ ≥ 0.65
- **Process:** 50-sample adjudication set annotated by two annotators; disagreements resolved by majority + documented rationale
- **Reported in paper:** Table of IAA statistics per category (when available)

---

## 9. Dataset Card Outline

1. Dataset Summary
2. Supported Tasks and Leaderboards
3. Languages (English)
4. Dataset Structure (fields, types, example)
5. Dataset Creation — Source Data, Annotations, Curation
6. Considerations for Using the Data (biases, limitations)
7. Citation
8. License

---

## 10. Benchmark Paper Outline

1. **Introduction** — motivation, FinVerify findings, benchmark gap
2. **Related Work** — FinQA, TAT-QA, DROP, MathBench, FinBench
3. **Benchmark Design** — taxonomy, collection, validation
4. **Statistical Analysis** — class distribution, difficulty analysis, IAA
5. **Baseline Models** — random, DVL, GPT-3.5, GPT-4, Llama-3
6. **Results** — accuracy by category, difficulty, reasoning type
7. **Error Analysis** — per-category failure modes
8. **Limitations and Future Work**
9. **Conclusion**
