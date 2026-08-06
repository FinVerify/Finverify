"""Synthetic-only tests for the Phase 9C-G eligibility engine."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import verification.eligibility.engine as eligibility_engine
from verification.eligibility.duplicates import canonical_sort_key, identity_key
from verification.eligibility.engine import build_eligibility, expansion_required, load_raw_ledger
from verification.eligibility.models import CHALLENGEABLE_DIMENSIONS, SourceDescriptor
from verification.eligibility.normalization import lexical, normalize_identity, normalized_value_key
from verification.eligibility.serialization import jsonl_bytes
from verification.eligibility.source_groups import build_source_groups, source_group_id
from verification.eligibility.statistics import stratified_fpc_normal_ci


def raw(candidate_id="c1", source_id="S1", value=1, locator="block/0", target="$1"):
    return {
        "candidate_id": candidate_id, "source_id": source_id, "source_sha256": "a" * 64,
        "relative_path": "synthetic.html", "source_format": "html", "source_locator": locator,
        "raw_source_span": "Synthetic value " + target, "target_raw_text": target,
        "target_start": 16, "target_end": 16 + len(target), "numeric_kind": "currency",
        "normalized_value": value, "normalized_unit": "currency", "scale": 1,
        "parser_metadata": {}, "enumeration_status": "ENUMERATED",
    }


def review(candidate_id="c1", **kwargs):
    identity = {"entity": "Example Corp", "concept": "Revenue", "period": "Q1 FY2025", "scope": "company", "accounting_basis": "gaap", "temporal_frame": "actual", "value_role": "current"}
    identity.update(kwargs.pop("identity", {}))
    return {"candidate_id": candidate_id, "eligibility_status": "ELIGIBLE", "identity": identity,
            "evidence": {"type": "prose", "text": "Synthetic evidence."},
            "challengeable_dimensions": list(CHALLENGEABLE_DIMENSIONS),
            "meaningful_challenge_dimensions": ["concept"], "directness_rank": 1,
            "reviewer_id": "R-SYNTHETIC"}


def descriptor(source_id, issuer="example corp", event="Q1-2025", role="release", same_event=None):
    return SourceDescriptor(source_id, issuer, event, "Q1 FY2025", role, same_event)


def test_lexical_unicode_case_and_whitespace_normalization():
    assert lexical("  CAFE\u0301\u00a0  Revenue  ") == "café revenue"


def test_explicit_state_semantics_are_conservative():
    assert normalize_identity({"entity": None})["entity"] == "UNSPECIFIED"
    assert normalize_identity({"entity": "unknown"})["entity"] == "UNKNOWN"
    assert normalize_identity({"entity": "NOT_APPLICABLE"})["entity"] == "NOT_APPLICABLE"
    base = raw()
    assert identity_key(base, type("R", (), {"identity": {"entity": "Example Corp", "concept": "Revenue", "period": "Q1", "scope": "UNKNOWN", "accounting_basis": "gaap", "temporal_frame": "actual", "value_role": "current"}})()) is None


def test_exact_normalized_value_has_no_tolerance():
    assert normalized_value_key("39.3", "currency", 1) != normalized_value_key("39.3000001", "currency", 1)


def test_non_equivalent_identity_dimensions_remain_separate():
    records = [raw("c1"), raw("c2", value=1)]
    reviews = [review("c1"), review("c2", identity={"concept": "Net income"})]
    result = build_eligibility(records, reviews, [descriptor("S1")])
    assert result["eligibility_ledger"][0]["fact_cluster_id"] != result["eligibility_ledger"][1]["fact_cluster_id"]


def test_repeated_equivalent_fact_clusters_and_table_canonical_preference():
    records = [raw("c1", "S1", locator="block/2"), raw("c2", "S2", locator="table/0/cell/1")]
    first = review("c1",); second = review("c2",)
    first.update({"directness_rank": 1, "is_repeated_narrative_restatement": True})
    second.update({"directness_rank": 1, "is_formal_statement_table": True})
    result = build_eligibility(records, [first, second], [descriptor("S1"), descriptor("S2", role="table")])
    rows = result["eligibility_ledger"]
    assert rows[0]["fact_cluster_id"] == rows[1]["fact_cluster_id"]
    assert sum(row["canonical_occurrence"] for row in rows) == 1
    assert next(row for row in rows if row["canonical_occurrence"])["candidate_id"] == "c2"


def test_canonical_source_id_and_locator_tie_breaks():
    records = [raw("z", "S2", locator="block/9"), raw("a", "S1", locator="block/9"), raw("b", "S1", locator="block/1")]
    reviews = [review("z"), review("a"), review("b")]
    result = build_eligibility(records, reviews, [descriptor("S1"), descriptor("S2")])
    canonical = next(row for row in result["eligibility_ledger"] if row["canonical_occurrence"])
    assert canonical["candidate_id"] == "b"


def test_source_group_same_event_roles_and_transitivity():
    groups = build_source_groups([
        descriptor("A", role="release"), descriptor("B", role="presentation", same_event="amended-Q1"),
        descriptor("C", event="other", same_event="amended-Q1"), descriptor("D", event="other-2", same_event="different-event"),
    ])
    assert groups["A"] == groups["B"] == groups["C"]
    assert groups["A"] != groups["D"]
    assert source_group_id(["A", "B", "C"]) == groups["A"]


def test_source_group_different_issuer_and_event_remain_separate():
    groups = build_source_groups([descriptor("A"), descriptor("B", issuer="Other Corp"), descriptor("C", event="Q2-2025")])
    assert len(set(groups.values())) == 3


def test_controlled_parent_subset_and_phase9d_independence():
    candidate = raw()
    decision = review(identity={"scope": None, "accounting_basis": None, "temporal_frame": None, "value_role": None})
    decision["challengeable_dimensions"] = ["entity", "concept", "period"]
    decision["meaningful_challenge_dimensions"] = ["concept"]
    result = build_eligibility([candidate], [decision], [descriptor("S1")])
    row = result["controlled_parent_pool"][0]
    assert row["challengeable_dimensions"] == ["concept", "entity", "period"]
    assert row["controlled_parent_eligible"] is True
    assert "Phase 9D" not in row


def test_natural_eligible_but_not_controlled_without_meaningful_challenge():
    decision = review()
    decision["meaningful_challenge_dimensions"] = []
    result = build_eligibility([raw()], [decision], [descriptor("S1")])
    assert result["eligible_natural_pool"][0]["natural_eligible"] is True
    assert result["controlled_parent_pool"] == []


@pytest.mark.parametrize("natural,parent,expected", [(60, 15, False), (59, 15, True), (60, 14, True), (59, 14, True)])
def test_expansion_trigger(natural, parent, expected):
    assert expansion_required(natural, parent) is expected


def test_deterministic_serialization_and_hash():
    records = [raw("b"), raw("a")]
    first = jsonl_bytes(sorted(records, key=lambda item: item["candidate_id"]))
    second = jsonl_bytes(sorted(records, key=lambda item: item["candidate_id"]))
    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_production_run2_rejected_by_default(tmp_path):
    path = tmp_path / "data" / "verification" / "enumeration" / "raw_candidate_ledger_run2.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(PermissionError):
        load_raw_ledger(path)


def test_run2_authorization_can_never_succeed(tmp_path):
    """Run-2 is permanently retired: allow_production=True can never authorize it,
    unlike Run-3 where authorization still requires exact hash/schema validation."""
    path = tmp_path / "data" / "verification" / "enumeration" / "raw_candidate_ledger_run2.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(PermissionError):
        load_raw_ledger(path, allow_production=True)


def test_production_run3_rejected_by_default(tmp_path):
    path = tmp_path / "data" / "verification" / "enumeration" / "raw_candidate_ledger_run3.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(PermissionError):
        load_raw_ledger(path)


def _authorized_synthetic_run3(tmp_path, monkeypatch):
    ledger_path = tmp_path / "data" / "verification" / "enumeration" / "raw_candidate_ledger_run3.jsonl"
    freeze_path = tmp_path / "data" / "verification" / "enumeration" / "THIRD_RUN_FREEZE.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_bytes = (json.dumps(raw("fvq2_c1"), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ledger_path.write_bytes(ledger_bytes)
    parse_bytes = b""
    parse_sha = hashlib.sha256(parse_bytes).hexdigest()
    commit = "b" * 40
    freeze = {
        "phase": "9C-R3", "enumerator_commit": commit, "enumeration_schema_version": "fvq2-raw-v1",
        "candidate_count": 1, "unique_candidate_id_count": 1,
        "raw_candidate_ledger": {"relative_path": "data/verification/enumeration/raw_candidate_ledger_run3.jsonl", "byte_size": len(ledger_bytes), "sha256": hashlib.sha256(ledger_bytes).hexdigest()},
        "parse_issue_ledger": {"relative_path": "data/verification/enumeration/parse_issues_run3.jsonl", "byte_size": 0, "sha256": parse_sha},
        "supersedes_for_scientific_use": "SECOND_RUN_FREEZE.json",
        "historical_provenance_policy": {"run2_remains_immutable_historical_provenance": True, "run2_is_never_a_scientific_fallback": True},
        "source_corpus_provenance": {"source_corpus_unchanged_from_run2": True},
        "repair_scope": {
            "candidate_identity_changed": True, "segment_index_added_to_identity": True,
            "source_corpus_changed": False, "parsing_changed": False, "segmentation_changed": False,
            "eligibility_policy_changed": False, "production_annotation_had_started": False,
            "annotation_outcomes_created_before_repair": False,
        },
    }
    freeze_bytes = (json.dumps(freeze, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    freeze_path.write_bytes(freeze_bytes)
    monkeypatch.setattr(eligibility_engine, "RUN3_SHA256", hashlib.sha256(ledger_bytes).hexdigest())
    monkeypatch.setattr(eligibility_engine, "RUN3_COMMIT", commit)
    monkeypatch.setattr(eligibility_engine, "RUN3_COUNT", 1)
    monkeypatch.setattr(eligibility_engine, "RUN3_FREEZE_PATH", freeze_path)
    monkeypatch.setattr(eligibility_engine, "RUN3_FREEZE_SHA256", hashlib.sha256(freeze_bytes).hexdigest())
    monkeypatch.setattr(eligibility_engine, "RUN3_LEDGER_BYTES", len(ledger_bytes))
    monkeypatch.setattr(eligibility_engine, "RUN3_PARSE_ISSUE_SHA256", parse_sha)
    return ledger_path, freeze_path, commit


def test_authorized_run_requires_exact_freeze_hash_and_parse_metadata(tmp_path, monkeypatch):
    ledger_path, freeze_path, commit = _authorized_synthetic_run3(tmp_path, monkeypatch)
    assert len(load_raw_ledger(ledger_path, allow_production=True, freeze_metadata_path=freeze_path, implementation_commit=commit)) == 1
    freeze_path.write_bytes(freeze_path.read_bytes().replace(b"9C-R3", b"9C-X3"))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_raw_ledger(ledger_path, allow_production=True, freeze_metadata_path=freeze_path, implementation_commit=commit)


def test_authorized_run_rejects_missing_or_unrecorded_implementation_commit(tmp_path, monkeypatch):
    ledger_path, freeze_path, _ = _authorized_synthetic_run3(tmp_path, monkeypatch)
    for commit in (None, "UNRECORDED"):
        with pytest.raises(PermissionError, match="implementation commit"):
            load_raw_ledger(ledger_path, allow_production=True, freeze_metadata_path=freeze_path, implementation_commit=commit)


def test_no_verifier_model_or_network_dependency():
    package = "\n".join(path.read_text(encoding="utf-8") for path in (Path(__file__).parents[1] / "verification" / "eligibility").glob("*.py"))
    assert "core.engine" not in package
    assert "transformers" not in package
    assert "requests" not in package


def test_stratified_fpc_normal_ci_is_exact_and_repeatable():
    strata = {"A": (8471, 20, 15), "B": (5647, 20, 10), "C": (0, 0, 0)}
    first = stratified_fpc_normal_ci(strata)
    second = stratified_fpc_normal_ci(strata)
    assert first == second
    assert first["status"] == "ESTIMATED"
    assert first["per_stratum"] == {"A": 0.75, "B": 0.5}
    weight_a = 8471 / 14118
    weight_b = 5647 / 14118
    point_estimate = weight_a * 0.75 + weight_b * 0.5
    assert first["point_estimate"] == pytest.approx(point_estimate)
    variance = (weight_a**2) * (1 - 20 / 8471) * 0.75 * 0.25 / 19
    variance += (weight_b**2) * (1 - 20 / 5647) * 0.5 * 0.5 / 19
    assert first["variance"] == pytest.approx(variance)
    assert first["standard_error"] == pytest.approx(variance**0.5)
    assert first["ci_lower"] == pytest.approx(max(0.0, point_estimate - 1.959963984540054 * variance**0.5))
    assert first["ci_upper"] == pytest.approx(min(1.0, point_estimate + 1.959963984540054 * variance**0.5))


@pytest.mark.parametrize("agreements, expected", [(0, (0.0, 0.0)), (20, (1.0, 1.0))])
def test_stratified_fpc_normal_ci_handles_unit_interval_boundaries(agreements, expected):
    result = stratified_fpc_normal_ci({"A": (14118, 20, agreements)})
    assert result["status"] == "ESTIMATED"
    assert (result["ci_lower"], result["ci_upper"]) == expected


def test_stratified_fpc_normal_ci_marks_underpowered_cells_without_bounds():
    result = stratified_fpc_normal_ci({"A": (100, 19, 10), "B": (14018, 20, 10)})
    assert result["status"] == "NOT_ESTIMATED"
    assert result["per_stratum"] == {"A": 10 / 19, "B": 0.5}
    assert result["variance"] is None
    assert result["standard_error"] is None
    assert result["ci_lower"] is None
    assert result["ci_upper"] is None
