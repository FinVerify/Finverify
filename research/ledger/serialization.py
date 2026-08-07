"""Frozen, gold-independent FinQA and TAT-QA serialization."""

from __future__ import annotations

import json
import unicodedata
from typing import Any, Callable, Mapping, Sequence


PROMPT_PREFIX = (
    "You are a financial analyst. Use the document below to answer the question with ONLY the final number.\n\n"
    "DOCUMENT:\n"
)
PROMPT_SUFFIX = "\n\nQuestion: {question}\nAnswer:"


def _lines(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, str):
        return values
    return "\n".join(str(item) for item in values)


def _table(table: Any) -> str:
    rows = []
    for row in table or []:
        if isinstance(row, Mapping):
            rows.append(" | ".join(str(v) for v in row.values()))
        else:
            rows.append(" | ".join(str(cell) for cell in row))
    return "\n".join(rows)


def finqa_context(example: Mapping[str, Any]) -> str:
    """Use only pre_text, table, and post_text; never QA metadata."""
    return "PRE-TEXT:\n{}\n\nTABLE:\n{}\n\nPOST-TEXT:\n{}".format(
        _lines(example.get("pre_text", [])),
        _table(example.get("table", [])),
        _lines(example.get("post_text", [])),
    )


def tatqa_context(example: Mapping[str, Any]) -> str:
    paragraphs = example.get("paragraphs", example.get("pre_text", []))
    if paragraphs and isinstance(paragraphs[0], Mapping):
        paragraphs = [p.get("text", "") for p in paragraphs]
    return "PARAGRAPHS:\n{}\n\nTABLE:\n{}".format(
        _lines(paragraphs), _table(example.get("table", []))
    )


def _encode(tokenizer: Any, text: str) -> list[int]:
    encoded = tokenizer.encode(text, add_special_tokens=True)
    return list(encoded)


def _decode(tokenizer: Any, tokens: Sequence[int]) -> str:
    return tokenizer.decode(list(tokens), skip_special_tokens=True)


def build_prompt(
    question: str,
    context: str,
    tokenizer: Any,
    *,
    max_input_tokens: int = 1024,
) -> tuple[str, int, bool]:
    """Build the exact prompt and deterministically budget context tokens.

    The table receives priority. Remaining context capacity is divided
    between prose regions in their serialized order. This function accepts a
    tokenizer protocol (``encode``/``decode``), making the policy testable
    without loading a model.
    """
    full = PROMPT_PREFIX + context + PROMPT_SUFFIX.format(question=question)
    tokens = _encode(tokenizer, full)
    if len(tokens) <= max_input_tokens:
        return full, len(tokens), False

    # Preserve the prompt/question and allocate the available context by
    # tokenizing complete labelled regions. The context labels remain stable.
    sections = context.split("\n\n")
    table_i = next((i for i, s in enumerate(sections) if s.startswith("TABLE:")), None)
    ordered = ([table_i] if table_i is not None else []) + [i for i in range(len(sections)) if i != table_i]
    empty_context = PROMPT_PREFIX + "" + PROMPT_SUFFIX.format(question=question)
    overhead = len(_encode(tokenizer, empty_context))
    capacity = max(0, max_input_tokens - overhead)
    selected: dict[int, str] = {i: "" for i in range(len(sections))}

    # Table first; then split remaining capacity approximately evenly among
    # non-table sections while retaining document order in the final output.
    table_tokens = _encode(tokenizer, sections[table_i]) if table_i is not None else []
    take_table = min(len(table_tokens), capacity)
    if table_i is not None:
        selected[table_i] = _decode(tokenizer, table_tokens[:take_table])
    remaining = capacity - take_table
    prose = [i for i in range(len(sections)) if i != table_i]
    if prose and remaining:
        for pos, i in enumerate(prose):
            slots = len(prose) - pos
            part = _encode(tokenizer, sections[i])
            take = min(len(part), (remaining + slots - 1) // slots)
            selected[i] = _decode(tokenizer, part[:take])
            remaining -= take

    kept = "\n\n".join(selected[i] for i in range(len(sections)) if selected[i])
    prompt = PROMPT_PREFIX + kept + PROMPT_SUFFIX.format(question=question)
    final_tokens = _encode(tokenizer, prompt)
    if len(final_tokens) > max_input_tokens:
        # A tokenizer may add boundary tokens after decoding. Final trimming
        # is context-only and leaves the question/instructions untouched.
        prompt = PROMPT_PREFIX + _decode(tokenizer, _encode(tokenizer, kept)[:max(0, capacity)]) + PROMPT_SUFFIX.format(question=question)
        final_tokens = _encode(tokenizer, prompt)
    return prompt, len(final_tokens), True


def serialize_raw_record(example_id: str, question: str, context: str,
                         raw_generation: str, parsed_prediction: float | None,
                         input_tokens: int, context_truncated: bool) -> dict[str, Any]:
    return {"example_id": str(example_id), "question": question, "context": context,
            "raw_generation": raw_generation, "parsed_prediction": parsed_prediction,
            "input_tokens": input_tokens, "context_truncated": context_truncated}


def serialize_gold_record(example_id: str, gold: float | None) -> dict[str, Any]:
    return {"example_id": str(example_id), "gold": gold}
