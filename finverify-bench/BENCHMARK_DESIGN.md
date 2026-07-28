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

## 5. Statistical Balance Requirements

- No single error_category may exceed 20% of total samples
- No single reasoning_type may exceed 18% of total samples  
- Difficulty distribution must fall within ±5pp of targets
- Underestimation/overestimation baseline ratio should be ~60/40 (matching paper's 60.9%)
- Ground-truth value distribution: log10(|gt|) should span [-2, 6] (from 0.01 to 1M)

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

| Step | Method |
|------|--------|
| Automated schema validation | `validate_dataset()` — blocks invalid samples |
| Mathematical verification   | `verify_calculations.py` — re-derives every answer |
| Duplicate detection         | Cosine similarity on (question + context) pairs |
| Template overlap detection  | Structural fingerprinting of context format |
| Class balance check         | Chi-squared test on category distribution |
| Human review                | 10% random sample reviewed by second annotator |

---

## 8. Inter-Annotator Agreement

- **Label set:** error_category (multi-label), difficulty (3-class)
- **Metric:** Krippendorff's α for error_category; Cohen's κ for difficulty
- **Target:** α ≥ 0.70 (substantial), κ ≥ 0.65
- **Process:** 50-sample adjudication set annotated by two annotators; disagreements resolved by majority + documented rationale
- **Reported in paper:** Table of IAA statistics per category

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
