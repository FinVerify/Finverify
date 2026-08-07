"""CLI for the frozen TAT-QA raw/gold ledger pair."""

import argparse
from typing import Any, Mapping

from .generate import generate_ledgers, load_json, write_ledgers
from .provenance import assert_lock_ready


def flatten_tatqa(documents: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Flatten official document/question TAT-QA records deterministically."""

    flattened: list[dict[str, Any]] = []

    for document in documents:
        table = document["table"]

        # Support both:
        # Official dataset:
        #   {"table": {"uid": "...", "table": [[...], ...]}}
        #
        # Test fixtures:
        #   {"table": [[...], ...]}
        if isinstance(table, Mapping):
            table = table["table"]

        paragraphs = document["paragraphs"]

        for question in document["questions"]:
            flattened.append(
                {
                    "uid": question["uid"],
                    "question": question["question"],
                    "answer": question["answer"],
                    "answer_type": question["answer_type"],
                    "table": table,
                    "paragraphs": paragraphs,
                }
            )

    return flattened


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--data", required=True)
    parser.add_argument("--raw-out", required=True)
    parser.add_argument("--gold-out", required=True)

    parser.add_argument(
        "--tokenizer",
        required=True,
        help="pinned local tokenizer directory",
    )

    parser.add_argument(
        "--base-model",
        required=True,
        help="pinned local base model directory",
    )

    parser.add_argument(
        "--adapter",
        required=True,
        help="pinned local adapter directory",
    )

    parser.add_argument(
        "--lock",
        required=True,
        help="frozen provenance lock",
    )

    args = parser.parse_args()

    assert_lock_ready(args.lock, dataset="tatqa")

    from .model import load_generator

    tokenizer, generator = load_generator(
        args.base_model,
        args.adapter,
        args.tokenizer,
    )

    documents = load_json(args.data)

    raw, gold, meta = generate_ledgers(
        flatten_tatqa(documents),
        "tatqa",
        tokenizer,
        lambda p: generator(
            p,
            max_new_tokens=30,
            do_sample=False,
        )[0]["generated_text"],
    )

    print(meta)
    print(write_ledgers(raw, gold, args.raw_out, args.gold_out))


if __name__ == "__main__":
    main()