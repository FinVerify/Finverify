"""Gold-loaded scoring process; never imported by blind_dvl."""

from collections import Counter
from typing import Iterable, Mapping

CORRECTNESS_TOLERANCE = 0.05
FROZEN_RULES = ("scale_div100", "scale_mul100", "sign_corrected", "magnitude_x10", "magnitude_x100", "magnitude_x1000", "magnitude_x0.1", "magnitude_x0.01", "magnitude_x0.001")


def is_correct(prediction: float | None, gold: float | None) -> bool:
    if prediction is None or gold is None:
        return False
    if gold == 0:
        return abs(prediction) < 0.01
    return abs(prediction - gold) / abs(gold) <= CORRECTNESS_TOLERANCE


def _unique_records(records: Iterable[Mapping], label: str) -> dict[str, Mapping]:
    result: dict[str, Mapping] = {}
    for record in records:
        example_id = str(record["example_id"])
        if example_id in result:
            raise ValueError(f"duplicate {label} example_id: {example_id}")
        result[example_id] = record
    return result


def score_examples(raw_records: Iterable[Mapping], intervention_records: Iterable[Mapping], gold_records: Iterable[Mapping]) -> dict:
    raw = _unique_records(raw_records, "raw")
    interventions = _unique_records(intervention_records, "intervention")
    gold_records_by_id = _unique_records(gold_records, "gold")
    gold = {example_id: record["gold"] for example_id, record in gold_records_by_id.items()}
    ids = list(raw)
    if len(ids) != len(set(ids)) or set(ids) != set(interventions) or set(ids) != set(gold):
        raise ValueError("ledger IDs must be unique and joined exactly")
    transitions = Counter()
    fired = 0
    rules = []
    for example_id in ids:
        before = raw[example_id].get("parsed_prediction")
        after = interventions[example_id].get("verified_value")
        baseline = is_correct(before, gold[example_id])
        post = is_correct(after, gold[example_id])
        if before != after:
            fired += 1
            transition = ("C" if baseline else "I") + "→" + ("C" if post else "I")
            transitions[transition] += 1
            rules.extend({"rule": rule, "transition": transition} for rule in interventions[example_id].get("fired_rules", []))
    n = len(ids)
    ic, ci = transitions["I→C"], transitions["C→I"]
    baseline_accuracy = sum(is_correct(raw[i].get("parsed_prediction"), gold[i]) for i in ids) / n if n else 0.0
    net_benefit = (ic - ci) / n if n else 0.0
    def rate(num, den): return num / den if den else None
    return {"N": n, "F": fired, "I→C": ic, "C→I": ci, "I→I": transitions["I→I"], "C→C": transitions["C→C"],
            "coverage": rate(fired, n), "successful_correction_rate": rate(ic, fired), "harm_rate": rate(ci, fired),
            "correctness_preserving_intervention_rate": rate(transitions["I→I"] + transitions["C→C"], fired),
            "intervention_precision": rate(ic, ic + ci), "net_benefit": net_benefit,
            "baseline_accuracy": baseline_accuracy, "post_intervention_accuracy": baseline_accuracy + net_benefit,
            "rule_firings": rules, "rule_metrics": score_rule_firings(rules)}


def score_rule_firings(rule_firings: Iterable[Mapping]) -> dict[str, dict]:
    """Return frozen per-rule counts/rates; zero denominators stay null."""
    grouped = {rule: [] for rule in FROZEN_RULES}
    for row in rule_firings:
        grouped.setdefault(str(row["rule"]), []).append(row)
    result = {}
    for rule, rows in sorted(grouped.items()):
        counts = Counter((row["transition"] for row in rows))
        fired = len(rows)
        ic, ci = counts["I→C"], counts["C→I"]
        result[rule] = {"F": fired, "I→C": ic, "C→I": ci, "I→I": counts["I→I"], "C→C": counts["C→C"],
                        "successful_correction_rate": ic / fired if fired else None,
                        "harm_rate": ci / fired if fired else None,
                        "correctness_preserving_intervention_rate": (counts["I→I"] + counts["C→C"]) / fired if fired else None,
                        "intervention_precision": ic / (ic + ci) if ic + ci else None}
    return result
