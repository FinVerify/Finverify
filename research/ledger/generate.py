"""Shared deterministic ledger generation; model execution is injectable."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .provenance import jsonl_bytes, write_once
from .serialization import build_prompt, finqa_context, serialize_gold_record, serialize_raw_record, tatqa_context


def numeric_value(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    from .parser import extract_number
    return extract_number(str(value))


def finqa_eligible(example: Mapping[str, Any]) -> tuple[bool, str]:
    value = example.get("qa", {}).get("exe_ans")
    return (numeric_value(value) is not None, "numeric_execution_answer" if numeric_value(value) is not None else "non_numeric_execution_answer")


def tatqa_eligible(example: Mapping[str, Any]) -> tuple[bool, str]:
    """Return eligibility for the canonical TAT-QA development split.

    Only a numeric final ``answer`` is eligible. Span, multi-span, textual,
    yes/no, and every other non-numeric ``answer_type`` are excluded. The
    decision uses only the stored final answer/type and never model
    predictions, ``gold_inds``, ``program``, or derivation metadata.
    """
    # TAT-QA schemas use answer_type plus answer. This remains mechanical and
    # never consults gold_inds/program/derivation for context construction.
    answer_type = str(example.get("answer_type", "")).casefold()
    value = example.get("answer")
    numeric = numeric_value(value)
    if answer_type and answer_type not in {"arithmetic", "numeric"}:
        return False, "non_arithmetic_answer_type"
    return (numeric is not None, "numeric_answer" if numeric is not None else "non_numeric_answer")


def _example_id(example: Mapping[str, Any]) -> str:
    for key in ("id", "uid", "example_id"):
        if key in example and example[key] is not None:
            return str(example[key])
    raise ValueError("example has no canonical ID")


def continuation_only(prompt: str, generated_text: str) -> str:
    """Remove the exact prompt prefix returned by text-generation pipelines."""
    if generated_text.startswith(prompt):
        return generated_text[len(prompt):]
    return generated_text


def generate_ledgers(examples: Iterable[Mapping[str, Any]], dataset: str, tokenizer: Any,
                     generate_text: Callable[[str], str], *, max_input_tokens: int = 1024) -> tuple[list[dict], list[dict], dict]:
    raw, gold, reasons = [], [], {}
    eligibility = finqa_eligible if dataset == "finqa" else tatqa_eligible
    for example in examples:
        allowed, reason = eligibility(example)
        reasons[reason] = reasons.get(reason, 0) + 1
        if not allowed:
            continue
        example_id = _example_id(example)
        question = example.get("qa", {}).get("question", example.get("question", ""))
        context = finqa_context(example) if dataset == "finqa" else tatqa_context(example)
        prompt, input_tokens, truncated = build_prompt(question, context, tokenizer, max_input_tokens=max_input_tokens)
        generation = continuation_only(prompt, generate_text(prompt))
        from .parser import extract_number
        parsed = extract_number(generation)
        raw.append(serialize_raw_record(example_id, question, prompt[len("You are a financial analyst. Use the document below to answer the question with ONLY the final number.\n\nDOCUMENT:\n"):].rsplit("\n\nQuestion:", 1)[0], generation, parsed, input_tokens, truncated))
        answer = example.get("qa", {}).get("exe_ans", example.get("answer"))
        gold.append(serialize_gold_record(example_id, numeric_value(answer)))
    if len({r["example_id"] for r in raw}) != len(raw) or len({r["example_id"] for r in gold}) != len(gold):
        raise ValueError("duplicate canonical example_id")
    return raw, gold, {"raw_count": sum(reasons.values()), "eligible_count": len(raw), "exclusion_counts": reasons}


def write_ledgers(raw: list[dict], gold: list[dict], raw_path: str | Path, gold_path: str | Path,
                  manifest_path: str | Path | None = None) -> dict:
    if len({str(r["example_id"]) for r in raw}) != len(raw):
        raise ValueError("duplicate raw ledger example_id")
    if len({str(r["example_id"]) for r in gold}) != len(gold):
        raise ValueError("duplicate gold ledger example_id")
    raw_hash = write_once(raw_path, jsonl_bytes(raw))
    gold_hash = write_once(gold_path, jsonl_bytes(gold))
    raw_target, gold_target = Path(raw_path), Path(gold_path)
    if manifest_path is None:
        manifest_path = raw_target.with_name(raw_target.stem.replace("_raw_ledger", "_hashes") + ".json")
    from .provenance import canonical_json_bytes
    manifest = {"schema_version": "1.0", "hash_algorithm": "SHA-256",
                "artifacts": {"raw_ledger": {"path": raw_target.name, "sha256": raw_hash},
                              "gold_ledger": {"path": gold_target.name, "sha256": gold_hash}}}
    manifest_hash = write_once(manifest_path, canonical_json_bytes(manifest))
    return {"raw_path": str(raw_path), "raw_sha256": raw_hash, "gold_path": str(gold_path),
            "gold_sha256": gold_hash, "manifest_path": str(manifest_path), "manifest_sha256": manifest_hash}


def load_json(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)
