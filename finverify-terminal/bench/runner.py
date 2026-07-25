"""Run a small local regression benchmark directly against the core engine."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from core import Claim, verify


def run(dataset: Path) -> dict:
    cases = json.loads(dataset.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        result = verify(Claim(question=case["question"], raw_value=case["raw_value"]))
        expected = case.get("expected_verified_value")
        passed = expected is None or abs((result.verified_value or 0) - expected) < 1e-9
        results.append({
            "question": case["question"],
            "verified_value": result.verified_value,
            "trust": result.trust_score.label,
            "passed": passed,
        })
    return {"total": len(results), "passed": sum(r["passed"] for r in results), "results": results}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    print(json.dumps(run(root / "datasets" / "smoke.json"), indent=2))
