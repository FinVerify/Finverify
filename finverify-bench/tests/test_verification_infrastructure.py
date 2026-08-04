"""Focused Phase 8 tests using synthetic fixtures only."""

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from verification.annotations import export_annotation_rows, import_annotations, write_annotation_csv
from verification.freeze import build_freeze_manifest, sha256_file, write_freeze_manifest
from verification.natural import eligible_natural_pair, ingest_natural_pairs
from verification.perturbations import make_matched_control, perturb_pair
from verification.schema import (
    ClaimEvidence, PairLabel, PairType, ShiftDimension, SourceProvenance, VerificationPair,
    validate_pair_shape,
)
from verification.splitting import split_by_source_group
from verification.summary import summarize_pairs
from verification.validators import validate_dataset


def source(group="S001"):
    return SourceProvenance("doc-" + group, "hash-" + group, "claim-" + group, ticker="NVDA", document_type="release")


def pair(group="S001", number=100.0):
    record = ClaimEvidence("Revenue was $100.", number, "NVDA", "Revenue", "Q4_FY2025", None, "company", "actual", "current")
    return VerificationPair("pair-" + group, group, record, replace(record), PairLabel.SUPPORT, PairType.NATURAL, source(group))


def test_valid_natural_and_controlled_pair_schema():
    natural = pair()
    assert validate_pair_shape(natural) == []
    control = make_matched_control(natural)
    derivative = perturb_pair(control, ShiftDimension.CONCEPT, "NetIncome")
    assert derivative.label == PairLabel.REJECT
    assert derivative.parent_pair_id == control.id
    assert derivative.source_group_id == control.source_group_id
    assert derivative.claim.value == derivative.evidence.value
    assert validate_pair_shape(derivative) == []


def test_invalid_label_identity_category_and_number_are_rejected():
    bad = pair()
    bad.claim.scope = "division"
    bad.claim.value = float("nan")
    errors = validate_pair_shape(bad)
    assert any("scope" in error for error in errors)
    assert any("finite number" in error for error in errors)
    with pytest.raises(ValueError):
        VerificationPair.from_dict(dict(bad.to_dict(), label="NOT_A_LABEL"))


def test_perturbation_is_single_dimension_and_reproducible():
    control = make_matched_control(pair())
    first = perturb_pair(control, ShiftDimension.PERIOD, "Q3_FY2025")
    second = perturb_pair(control, ShiftDimension.PERIOD, "Q3_FY2025")
    assert first.id == second.id
    changed = []
    for side in ("claim", "evidence"):
        before = getattr(control, side).identity()
        after = getattr(first, side).identity()
        changed.extend(field for field in before if before[field] != after[field])
    assert changed == ["period"]


def test_validator_rejects_malformed_multi_dimension_derivative():
    control = make_matched_control(pair())
    valid = perturb_pair(control, ShiftDimension.CONCEPT, "OperatingIncome")
    assert validate_dataset([control, valid]) == []

    malformed = replace(
        valid,
        evidence=replace(valid.evidence, concept="OperatingIncome", period="FY2025"),
    )
    errors = validate_dataset([control, malformed])
    assert any("expected only concept to change" in error for error in errors)


def test_split_is_source_group_safe_and_deterministic():
    pairs = []
    for index in range(6):
        control = make_matched_control(pair("S%03d" % index))
        pairs.extend([control, perturb_pair(control, ShiftDimension.CONCEPT, "NetIncome")])
    first, manifest = split_by_source_group(pairs, test_ratio=0.5, seed=20260804)
    second, manifest2 = split_by_source_group(pairs, test_ratio=0.5, seed=20260804)
    assert [item.split for item in first] == [item.split for item in second]
    assert manifest["dev_source_groups"] == manifest2["dev_source_groups"]
    for group in manifest["dev_source_groups"]:
        assert all(item.split == "dev" for item in first if item.source_group_id == group)
    for group in manifest["test_source_groups"]:
        assert all(item.split == "test" for item in first if item.source_group_id == group)
    _, other_manifest = split_by_source_group(pairs, test_ratio=0.5, seed=20260805)
    assert manifest["test_source_groups"] != other_manifest["test_source_groups"]


def test_natural_ingestion_is_structural_and_independent():
    natural = pair()
    kept = ingest_natural_pairs([natural], eligibility=eligible_natural_pair)
    assert kept == [natural]
    with pytest.raises(ValueError):
        ingest_natural_pairs([make_matched_control(natural)])


def test_leakage_validator_catches_cross_split_group_and_duplicate_id():
    control = make_matched_control(pair())
    contaminated = replace(perturb_pair(control, ShiftDimension.CONCEPT, "NetIncome"), split="test")
    control = replace(control, split="dev")
    errors = validate_dataset([control, contaminated, replace(control, id="duplicate") , replace(control, id="duplicate")])
    assert any("crosses splits" in error for error in errors)
    assert any("duplicate pair id" in error for error in errors)


def test_freeze_hash_and_manifest_are_read_only(tmp_path):
    data = tmp_path / "pairs.jsonl"
    data.write_text("fixture\n", encoding="utf-8")
    before = data.read_bytes()
    digest = sha256_file(data)
    manifest = build_freeze_manifest(
        [data],
        seed=20260804,
        creation_command="fixture-freeze --seed 20260804",
        split_manifest={"dev_source_groups": ["S001"], "test_source_groups": ["S002"]},
    )
    assert manifest["schema_version"] == "verify-v1"
    assert manifest["seed"] == 20260804
    assert manifest["creation_command"] == "fixture-freeze --seed 20260804"
    assert manifest["verifier_freeze_commit"] == "f1ff63e06c0751218dfbcf2071cbb434aa8fa873"
    assert manifest["protocol_reference"] == "PROTOCOL.md"
    assert manifest["spec_reference"] == "EXPERIMENT_SPEC_v1.md"
    assert manifest["split"]["dev_source_groups"] == ["S001"]
    assert manifest["files"][0]["sha256"] == digest
    assert data.read_bytes() == before
    output = tmp_path / "freeze.json"
    write_freeze_manifest(output, manifest)
    with pytest.raises(FileExistsError):
        write_freeze_manifest(output, manifest)


def test_annotation_export_is_blinded_and_mapping_survives_shuffle(tmp_path):
    control = make_matched_control(pair())
    derivative = perturb_pair(control, ShiftDimension.ENTITY, "AAPL")
    rows, mapping = export_annotation_rows([control, derivative], seed=7)
    public_csv = tmp_path / "public_annotations.csv"
    write_annotation_csv(public_csv, rows)
    with public_csv.open(newline="", encoding="utf-8") as handle:
        reader = __import__("csv").DictReader(handle)
        csv_headers = set(reader.fieldnames or [])
        csv_rows = list(reader)
    public_headers = csv_headers
    forbidden_headers = {
        "prediction", "system_status", "expected_result", "label", "shift_dimension",
        "pair_type", "parent_pair_id", "control_pair_id", "derivative_pair_id",
    }
    assert public_headers.isdisjoint(forbidden_headers)
    public_payload = json.dumps(csv_rows, sort_keys=True)
    assert control.id not in public_payload
    assert derivative.id not in public_payload
    assert set(mapping.values()) == {control.id, derivative.id}
    assert set(mapping[row["annotation_item_id"]] for row in rows) == {control.id, derivative.id}
    assert all("SUPPORT" in row["allowed_decisions"] for row in rows)


def test_annotation_import_preserves_annotators_and_rejects_duplicates(tmp_path):
    input_file = tmp_path / "responses.csv"
    input_file.write_text(
        "annotation_item_id,annotator_id,decision,reason_fields\n"
        "ann_000001,a1,SUPPORT,NONE\n"
        "ann_000001,a2,REJECT,CONCEPT\n",
        encoding="utf-8",
    )
    raw = tmp_path / "raw.jsonl"
    annotations = import_annotations(input_file, item_ids={"ann_000001"}, raw_output=raw)
    assert [item.annotator_id for item in annotations] == ["a1", "a2"]
    assert len(raw.read_text(encoding="utf-8").splitlines()) == 2
    input_file.write_text(input_file.read_text(encoding="utf-8") + "ann_000001,a1,SUPPORT,NONE\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        import_annotations(input_file, item_ids={"ann_000001"})


def test_summary_counts_dataset_qa_only():
    control = make_matched_control(pair())
    derivative = perturb_pair(control, ShiftDimension.SCOPE, "segment")
    summary = summarize_pairs([control, derivative])
    assert summary["total_pairs"] == 2
    assert summary["labels"]["SUPPORT"] == 1
    assert summary["shift_dimensions"]["scope"] == 1
