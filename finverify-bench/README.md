# FinVerifyBench

**A benchmark for structured numerical hallucinations in financial language models.**

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Benchmark v1.0](https://img.shields.io/badge/benchmark-v1.0-green.svg)](https://github.com/your-org/finverifybench)

---

## Motivation

Financial LLMs make numerical errors that are **statistically structured rather than random** (χ²=41.97, p<0.001). Errors cluster into three dominant classes — scale confusion (0.27% ↔ 27%), sign reversal (+5% ↔ −5%), and magnitude mismatch (millions ↔ billions) — making them amenable to deterministic correction rather than requiring more reasoning compute.

This finding, from the paper *"Structured Numerical Hallucinations in Financial LLMs: Deterministic Verification Outperforms Chain-of-Thought Prompting"* (ACL ARR May 2026), motivated FinVerifyBench: a publicly available, mathematically verified benchmark for evaluating and improving numerical reliability in financial AI systems.

---

## Dataset at a Glance

| Split | Samples |
|-------|---------|
| Train | 350     |
| Dev   | 75      |
| Test  | 75      |
| **Total** | **500** |

**Error categories:** scale_error · sign_error · magnitude_error · arithmetic_error · ratio_error · percentage_error · aggregation_error · unit_conversion · reasoning_error · rounding_error · context_confusion

**Source types:** SEC 10-K · SEC 10-Q · Earnings releases · Investor presentations · Balance sheets · Income statements · Cash flow statements

**Difficulty levels:** easy · medium · hard

---

## Quick Start

```python
import json
from benchmark.evaluator import evaluate, print_report

# Load dataset
with open("data/processed/test.json") as f:
    dataset = json.load(f)

# Load your model predictions
predictions = [
    {"id": s["id"], "prediction": your_model(s["question"], s["context"])}
    for s in dataset
]

# Evaluate
report = evaluate(dataset, predictions)
print_report(report)
```

**Output:**
```
============================================================
  FinVerifyBench Evaluation Report
============================================================
  Samples evaluated : 75 / 75
  Tolerance         : 5% relative

  Overall Accuracy  : XX.XX%
  Mean Rel. Error   : XX.X%

  Bias Analysis (wrong predictions only):
    Underestimation : XX.X%  (paper: 60.9%)
    ...
```

---

## Sample Format

```json
{
  "id": "fvb_000001",
  "domain": "finance",
  "question": "What is the gross profit margin percentage?",
  "context": "Income Statement (in millions)\nRevenue: $45,230.0\nCost of Revenue: $33,245.0\nGross Profit: $11,985.0",
  "ground_truth": 26.5,
  "unit": "percent",
  "error_category": ["scale_error"],
  "difficulty": "easy",
  "reasoning_type": ["margin_calculation"],
  "source_type": "income_statement",
  "split": "train"
}
```

---

## Error Taxonomy

FinVerifyBench uses a 12-class taxonomy organized under the DVL paper's decomposition:

**ε(ŷ, y) = ε_scale + ε_sign + ε_magnitude + ε_residual**

| Group     | Categories                                                    |
|-----------|---------------------------------------------------------------|
| Scale     | `scale_error`, `percentage_error`                             |
| Sign      | `sign_error`                                                  |
| Magnitude | `magnitude_error`, `unit_conversion`, `aggregation_error`     |
| Residual  | `arithmetic_error`, `ratio_error`, `reasoning_error`, `rounding_error`, `context_confusion`, `extraction_error` |

---

## Evaluation Metrics

| Metric | Description |
|--------|-------------|
| Execution Accuracy | % correct within 5% relative tolerance (FinQA protocol) |
| Mean Relative Error | Average |pred − gt| / |gt| |
| Underestimation Rate | % of wrong predictions where pred < gt |
| Per-category Accuracy | Accuracy broken down by error_category |
| Per-difficulty Accuracy | Accuracy by easy/medium/hard |
| Calibration | Error distribution across magnitude bins |

---

## Baseline Results

| Baseline | Accuracy | Underest. Rate |
|----------|----------|---------------|
| Random | ~1.3% | ~55% |
| Scale-confused | ~34.7% | ~57% |
| Sign-confused | ~74.7% | ~42% |
| Magnitude-confused | ~28.0% | ~39% |
| Arithmetic (CoT drift) | ~78.7% | ~19% |
| Oracle DVL | ~69.3% | ~44% |
| **Paper: Mistral-7B + DVL + FT** | **42.61%** | **60.9%** |

---

## Repository Structure

```
finverifybench/
├── benchmark/
│   ├── __init__.py
│   ├── evaluator.py       # Main evaluate() entry point
│   ├── metrics.py         # All metrics implementation
│   ├── taxonomy.py        # Error taxonomy, enums, DVL mapping
│   └── validators.py      # Schema validation
├── data/
│   ├── processed/
│   │   ├── train.json     # 350 samples
│   │   ├── dev.json       # 75 samples
│   │   ├── test.json      # 75 samples
│   │   └── all.json       # Combined
│   └── hf_export/         # Hugging Face format
├── scripts/
│   ├── create_dataset.py        # Dataset generator
│   ├── validate_dataset.py      # Schema validation
│   ├── verify_calculations.py   # Math verification
│   ├── generate_statistics.py   # Stats & reports
│   ├── generate_baselines.py    # Baseline predictions
│   └── export_huggingface.py    # HF export
├── examples/
│   └── *_predictions.json       # Baseline prediction files
├── tests/
│   └── test_benchmark.py        # Unit tests
├── BENCHMARK_DESIGN.md
├── benchmark_card.md
├── requirements.txt
└── README.md
```

---

## Installation

```bash
git clone https://github.com/your-org/finverifybench
cd finverifybench
pip install -r requirements.txt
```

**Requirements:** Python 3.8+ · No ML framework required (evaluator is pure Python)

---

## Reproducing Baselines

```bash
# Generate dataset
python scripts/create_dataset.py

# Validate
python scripts/validate_dataset.py

# Generate baseline predictions + accuracy table
python scripts/generate_baselines.py

# Full statistics report
python scripts/generate_statistics.py
```

---

## DVL Integration

To evaluate your model with the DVL correction layer from the paper:

```python
from benchmark.taxonomy import classify_dvl_rules, RATIO_KEYWORDS, NEGATION_KEYWORDS

def apply_dvl(prediction: float, question: str, context: str) -> float:
    """Minimal DVL implementation matching Algorithm 1 from paper."""
    import re
    yhat = prediction
    q = question.lower()

    # Rule 1: Scale correction
    ratio_kws = RATIO_KEYWORDS
    if any(kw in q for kw in ratio_kws):
        if abs(yhat) > 100:
            yhat = yhat / 100
        elif abs(yhat) < 1 and yhat != 0:
            yhat = yhat * 100

    # Rule 2: Sign correction
    neg_kws = NEGATION_KEYWORDS
    if any(kw in q for kw in neg_kws) and yhat > 0:
        yhat = -abs(yhat)

    # Rule 3: Magnitude correction (parse unit header)
    unit_map = {"in millions": 1e6, "in thousands": 1e3, "in billions": 1e9}
    for pattern, scale in unit_map.items():
        if pattern in context.lower():
            log_ratio = abs(math.log10(abs(yhat) / scale)) if yhat != 0 else 99
            if log_ratio > 1.5:
                yhat = yhat * scale  # correction factor
            break

    return yhat
```

---

## Citation

```bibtex
@misc{finverifybench2026,
  title     = {{FinVerifyBench}: A Benchmark for Structured Numerical Hallucinations
               in Financial {LLMs}},
  author    = {Anonymous},
  year      = {2026},
  url       = {https://github.com/your-org/finverifybench},
  note      = {v1.0. Motivated by ACL ARR May 2026 submission \#2935.}
}
```

If using this benchmark, please also cite the motivating paper:

```bibtex
@inproceedings{finverify2026,
  title     = {Structured Numerical Hallucinations in Financial {LLMs}: 
               Deterministic Verification Outperforms Chain-of-Thought Prompting},
  author    = {Anonymous},
  booktitle = {Proceedings of the 64th Annual Meeting of the Association for 
               Computational Linguistics},
  year      = {2026}
}
```

---

## License

Dataset: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)  
Code: [MIT](https://opensource.org/licenses/MIT)

All samples are synthetically generated in the style of SEC financial filings. No proprietary or copyrighted financial data is included.

---

## Contact

For questions, open a GitHub issue or reach out via the paper's contact information.
