#!/usr/bin/env python3
"""
FinVerifyBench — Hugging Face Dataset Exporter (Phase 5)
Produces a HF-compatible dataset_dict.json and README.
"""

import json
import os


HF_FIELDS = [
    "id", "domain", "question", "context",
    "ground_truth", "unit", "error_category",
    "difficulty", "reasoning_type", "source_type", "split"
]


def clean_sample(s: dict) -> dict:
    """Strip internal fields not intended for HF release."""
    return {k: s[k] for k in HF_FIELDS if k in s}


def export_hf(output_dir: str = "data/hf_export"):
    os.makedirs(output_dir, exist_ok=True)

    for split in ["train", "dev", "test"]:
        src = f"data/processed/{split}.json"
        if not os.path.exists(src):
            print(f"  Skipping {split} — file not found")
            continue
        with open(src) as f:
            samples = json.load(f)
        cleaned = [clean_sample(s) for s in samples]
        out = f"{output_dir}/{split}.json"
        with open(out, "w") as f:
            json.dump(cleaned, f, indent=2)
        print(f"  Exported {len(cleaned)} samples → {out}")

    # Write dataset_info.json (HF metadata)
    info = {
        "dataset_name": "finverifybench",
        "description": (
            "FinVerifyBench: A benchmark for structured numerical hallucinations "
            "in financial language models. Motivated by findings that LLM numerical "
            "errors are statistically structured (χ²=41.97, p<0.001) rather than random."
        ),
        "version": "1.0.0",
        "license": "cc-by-4.0",
        "splits": {
            "train": {"n": 350, "path": "train.json"},
            "dev":   {"n": 75,  "path": "dev.json"},
            "test":  {"n": 75,  "path": "test.json"},
        },
        "features": {
            "id":             {"dtype": "string"},
            "domain":         {"dtype": "string"},
            "question":       {"dtype": "string"},
            "context":        {"dtype": "string"},
            "ground_truth":   {"dtype": "float64"},
            "unit":           {"dtype": "string"},
            "error_category": {"dtype": "list<string>"},
            "difficulty":     {"dtype": "string"},
            "reasoning_type": {"dtype": "list<string>"},
            "source_type":    {"dtype": "string"},
            "split":          {"dtype": "string"},
        },
        "citation": (
            "@misc{finverifybench2026,\n"
            "  title={{FinVerifyBench}: A Benchmark for Structured Numerical "
            "Hallucinations in Financial {LLM}s},\n"
            "  author={Anonymous},\n"
            "  year={2026},\n"
            "  url={https://github.com/your-org/finverifybench}\n"
            "}"
        ),
        "homepage": "https://github.com/your-org/finverifybench",
    }
    with open(f"{output_dir}/dataset_info.json", "w") as f:
        json.dump(info, f, indent=2)
    print(f"  Wrote {output_dir}/dataset_info.json")


if __name__ == "__main__":
    export_hf()
    print("\n  HF export complete.")