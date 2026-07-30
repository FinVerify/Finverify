# Smoke Benchmark

This is a lightweight regression benchmark that runs in a few seconds. It ensures the core verification engine produces **stable outputs** for a small set of well‑known cases.

## Purpose

- Catch regressions during refactors.
- Ensure new features don't break existing behaviour.
- Serve as the acceptance criteria for major changes (e.g., Phase 2 TrustEngine).

## Dataset

The dataset in `smoke.json` is curated **only** from:

- Existing `tests/test_dvl.py` regression cases.
- Historically fixed bugs.
- Manually verified examples from FinVerify's own regression suite.

⚠️ **Do not add cases from FinQA or other external benchmarks** – that is the role of the separate `FinVerifyBench` research project. This smoke benchmark is purely for engineering regression.

Each case includes:
- A unique `id` and a `category` (`scale`, `sign`, `magnitude`, `noop`, etc.).
- A `reason` explaining why the case exists.
- The question and raw LLM value.
- The **expected verified value** (frozen) and the **expected correction rule names** (stable identifiers like `scale`, `sign`, `magnitude`).
- Optional `workflow` metadata for non-DVL regression paths such as filing-based financial reasoning.

## Usage

```bash
# Run the benchmark (default: ignore labels)
python bench/runner.py

# Also verify trust labels (compatibility mode)
python bench/runner.py --check-labels

# Export results for historical tracking
python bench/runner.py --export results/latest.json
```

The export command creates the parent `results/` directory automatically when needed.
