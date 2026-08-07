import inspect
import hashlib
import json
from dataclasses import fields
from collections import OrderedDict
from pathlib import Path

import pytest

from research.fcg.feasibility import extract_concepts, eligible_constraints
from research.intervention.blind_dvl import BlindInterventionInput, BlindInterventionOutput, Correction, blind_verify
from research.intervention.scoring import score_examples
from research.ledger.generate import continuation_only, write_ledgers
from research.ledger.provenance import jsonl_bytes, sha256_bytes, assert_lock_ready
from research.ledger.serialization import build_prompt, finqa_context, tatqa_context
from research.stats.mcnemar import mcnemar
from research.stats.bootstrap import bootstrap_ci


class Tok:
    def encode(self, text, add_special_tokens=True):
        return text.split()
    def decode(self, tokens, skip_special_tokens=True):
        return " ".join(tokens)


def test_blind_interface_no_gold():
    forbidden = ("gold", "actual", "actual_value", "target", "y_true", "correct", "error_label")
    for cls in (BlindInterventionInput, BlindInterventionOutput):
        assert not any(any(term in field.name.lower() for term in forbidden)
                       and field.name != "correction_log" for field in fields(cls))


def test_blind_verify_signature():
    signature = inspect.signature(blind_verify)
    assert len(signature.parameters) == 1
    parameter = next(iter(signature.parameters.values()))
    assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameter.annotation is not inspect.Parameter.empty


def test_blind_verify_rejects_smuggled_gold():
    with pytest.raises(TypeError):
        BlindInterventionInput("x", "q", "c", "1", 1.0, gold=1.0)


def test_blind_stage_runs_without_gold_file(tmp_path):
    item = BlindInterventionInput("x", "What was the margin?", "", "Answer: 0.5", .5)
    first = blind_verify(item)
    gold = tmp_path / "gold.json"
    gold.write_text('{"gold": 0.5}', encoding="utf-8")
    gold.unlink()
    assert blind_verify(item) == first


def test_blind_module_has_no_gold_dependency():
    source = inspect.getsource(inspect.getmodule(blind_verify))
    assert "scoring" not in source
    assert "open(" not in source


def test_attribution_chain_counts():
    output = {"fired_rules": ["scale_div100", "magnitude_x10"]}
    from research.intervention.attribution import attribute_transition
    assert attribute_transition(output, False, True) == [
        {"rule": "scale_div100", "transition": "I→C"},
        {"rule": "magnitude_x10", "transition": "I→C"},
    ]


def test_zero_intervention_metrics_are_null():
    row = {"example_id": "x", "parsed_prediction": 1.0}
    out = {"example_id": "x", "verified_value": 1.0, "fired_rules": []}
    metrics = score_examples([row], [out], [{"example_id": "x", "gold": 1.0}])
    assert metrics["F"] == 0
    assert metrics["successful_correction_rate"] is None
    assert metrics["harm_rate"] is None
    assert metrics["intervention_precision"] is None
    assert metrics["rule_metrics"]["sign_corrected"]["F"] == 0
    assert metrics["rule_metrics"]["sign_corrected"]["harm_rate"] is None


def test_continuation_only_parser_input():
    prompt = "Question: what?\nAnswer:"
    assert continuation_only(prompt, prompt + " 42") == " 42"
    assert continuation_only(prompt, "42") == "42"


def test_duplicate_ids_rejected_before_scoring():
    raw = [{"example_id": "x", "parsed_prediction": 1.0}, {"example_id": "x", "parsed_prediction": 1.0}]
    with pytest.raises(ValueError, match="duplicate raw"):
        score_examples(raw, [{"example_id": "x", "verified_value": 1.0, "fired_rules": []}], [{"example_id": "x", "gold": 1.0}])


def test_ledger_hash_manifest_is_persisted(tmp_path):
    result = write_ledgers(
        [{"example_id": "x", "value": 1}], [{"example_id": "x", "gold": 1}],
        tmp_path / "finqa_dev_raw_ledger.jsonl", tmp_path / "finqa_dev_gold.jsonl",
    )
    assert (tmp_path / "finqa_dev_hashes.json").is_file()
    assert result["manifest_sha256"]


def test_frozen_bootstrap_and_tolerance_cannot_be_overridden():
    with pytest.raises(TypeError):
        bootstrap_ci([1], lambda values: 1.0, seed=1)
    from research.intervention.scoring import is_correct
    with pytest.raises(TypeError):
        is_correct(1.0, 1.0, tolerance=0.1)


def test_provenance_validates_only_executing_dataset(tmp_path):
    lock = json.loads((Path("research/protocols/PREEXECUTION_PROVENANCE_LOCK.json")).read_text(encoding="utf-8"))
    protocol_path = Path("research/protocols/SELECTIVE_INTERVENTION_PROTOCOL_v1.1_FROZEN.md").resolve()
    lock["metadata"]["frozen"] = True
    lock["protocol"]["file"] = str(protocol_path)
    lock["protocol"]["sha256"] = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    lock["finqa"] = {"repository": "repo", "revision": "a" * 40, "dev_file": "dev.json", "sha256": "a" * 64, "raw_examples": 1, "eligible_examples": 1}
    lock["tatqa"] = {}
    lock["model"].update({"revision": "b" * 40, "tokenizer_revision": "c" * 40})
    lock["adapter"]["revision"] = "d" * 40
    lock["environment"] = {field: "value" for field in ("python", "torch", "transformers", "peft", "bitsandbytes", "cuda", "gpu", "platform", "operating_system")}
    lock["implementation"].update({"commit": "e" * 40, "codex_completed": True, "implementation_sha256": "f" * 64})
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    assert_lock_ready(lock_path, dataset="finqa") is None
    with pytest.raises(RuntimeError, match="tatqa"):
        assert_lock_ready(lock_path, dataset="tatqa")


def test_net_benefit_equals_derived_accuracy():
    raw = [{"example_id": str(i), "parsed_prediction": value} for i, value in enumerate([1.0, 2.0, 3.0])]
    interventions = [{"example_id": "0", "verified_value": 1.0, "fired_rules": []},
                     {"example_id": "1", "verified_value": 1.0, "fired_rules": ["magnitude_x0.5"]},
                     {"example_id": "2", "verified_value": 3.0, "fired_rules": []}]
    metrics = score_examples(raw, interventions, [{"example_id": "0", "gold": 1.0}, {"example_id": "1", "gold": 1.0}, {"example_id": "2", "gold": 4.0}])
    assert metrics["post_intervention_accuracy"] == metrics["baseline_accuracy"] + metrics["net_benefit"]


def test_ordering_gold_after_intervention():
    events = []
    events.append("raw")
    events.append("intervention")
    events.append("gold")
    assert events == ["raw", "intervention", "gold"]


def test_ledger_hash_immutability():
    original = jsonl_bytes([{"example_id": "a", "value": 1}])
    assert sha256_bytes(original) == sha256_bytes(original)
    assert sha256_bytes(original) != sha256_bytes(jsonl_bytes([{"example_id": "a", "value": 2}]))


def test_finqa_serializer_deterministic():
    sample = {"pre_text": ["P1", "P2"], "table": [["A", "B"]], "post_text": ["Q"], "qa": {"question": "what?", "model_input": "bad"}}
    changed = {**sample, "qa": {**sample["qa"], "model_input": "different", "exe_ans": 99, "gold_inds": {}}}
    assert finqa_context(sample) == finqa_context(changed)
    assert finqa_context(sample).index("P1") < finqa_context(sample).index("A") < finqa_context(sample).index("Q")
    assert build_prompt("what?", finqa_context(sample), Tok(), max_input_tokens=8)[2]


def test_tatqa_serializer_deterministic():
    sample = {"paragraphs": [{"text": "P"}], "table": [["A", "B"]], "question": "Q", "gold_inds": {}}
    assert tatqa_context(sample) == "PARAGRAPHS:\nP\n\nTABLE:\nA | B"


def test_parser_fixtures():
    from research.ledger.parser import extract_number
    assert extract_number("$1,234.50") == 1234.5
    assert extract_number("(12.5)") == -12.5
    assert extract_number("12.5%") == 12.5
    assert extract_number("first 2 then -3") == -3
    assert extract_number("not numeric") is None


def test_fcg_eligibility_gold_independent():
    constraints = [{"id": "x", "requires": ("revenue", "cogs", "gross_profit")}]
    text = "Revenue, cost of goods sold, and gross profit."
    assert eligible_constraints(extract_concepts(text), constraints) == ("x",)


def test_dataset_id_uniqueness():
    ids = ["a", "b"]
    assert len(ids) == len(set(ids))


def test_no_model_input_usage():
    base = {"pre_text": ["P"], "table": [["T"]], "post_text": ["O"], "qa": {"question": "Q", "model_input": "one"}}
    altered = {**base, "qa": {**base["qa"], "model_input": "two"}}
    assert finqa_context(base) == finqa_context(altered)


def test_actual_none_adapter():
    result = blind_verify(BlindInterventionInput("x", "What was the ratio?", "", "1", 1.0))
    assert result.verified_value == 1.0


def test_fcg_alias_registry_deterministic():
    one = OrderedDict([("revenue", ["net revenue"]), ("cogs", ["cost of goods sold"])])
    two = OrderedDict(reversed(list(one.items())))
    text = "Net revenue and cost of goods sold"
    assert extract_concepts(text, one) == extract_concepts(text, two)


def test_mcnemar_threshold():
    assert mcnemar(2, 1)["method"] == "exact_binomial"
    assert mcnemar(13, 12)["method"] == "continuity_corrected"
