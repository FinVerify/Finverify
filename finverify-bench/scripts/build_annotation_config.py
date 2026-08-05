#!/usr/bin/env python3
"""Build and freeze annotation_config.lock.json from a JSON spec file.

Input JSON shape:
{
  "implementation_commit": "<40-hex>",
  "evaluation_model_families": ["family-x", "family-y"],
  "decoding": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 512},
  "failure_handling": {"timeout_seconds": 60, "retry_count": 2},
  "annotators": [
    {"annotator_id": "a1", "model_family": "family-a", "model_version": "2026-01",
     "prompt": "<verbatim prompt text>"},
    ...
  ]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verification.eligibility.annotation_config import (
    AnnotationConfig, AnnotatorSpec, DecodingSettings, FailureHandling,
)
from verification.eligibility.serialization import write_new


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="path for annotation_config.lock.json")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    annotators = tuple(
        AnnotatorSpec(a["annotator_id"], a["model_family"], a["model_version"], a["prompt"])
        for a in spec["annotators"]
    )
    config = AnnotationConfig(
        annotators=annotators,
        decoding=DecodingSettings(**spec["decoding"]),
        failure_handling=FailureHandling(**spec["failure_handling"]),
        evaluation_model_families=tuple(spec["evaluation_model_families"]),
        implementation_commit=spec.get("implementation_commit", "UNRECORDED"),
    )
    digest = write_new(args.output, config.lock_bytes())
    print("froze annotation_config.lock.json sha256=%s" % digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
