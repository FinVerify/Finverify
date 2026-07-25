"""Keep the smoke benchmark aligned with the frozen legacy DVL reference."""

import json
from pathlib import Path

from app.dvl import full_verify
from core.engine import verify
from core.models import Claim


SMOKE_DATASET = Path(__file__).resolve().parents[2] / "bench" / "smoke.json"


def test_smoke_benchmark_cases_match_legacy_dvl_and_core_engine():
    data = json.loads(SMOKE_DATASET.read_text(encoding="utf-8"))

    for case in data["cases"]:
        legacy_value, legacy_log, _legacy_label, _legacy_color = full_verify(
            case["question"],
            case["raw_value"],
        )
        result = verify(Claim(question=case["question"], raw_value=case["raw_value"]))

        expected_value = case["expected_verified"]
        expected_rules = case.get("expected_corrections", [])

        assert legacy_value == expected_value, f"{case['id']} drifted from app.dvl.full_verify()"
        assert [entry["rule"] for entry in legacy_log] == expected_rules, f"{case['id']} corrections drifted from app.dvl.full_verify()"

        assert result.verified_value == expected_value, f"{case['id']} drifted in core.engine.verify()"
        assert [entry["rule"] for entry in result.correction_log] == expected_rules, f"{case['id']} corrections drifted in core.engine.verify()"

        if "expected_label" in case:
            assert result.trust_score.label == case["expected_label"], f"{case['id']} trust label drifted in core.engine.verify()"
