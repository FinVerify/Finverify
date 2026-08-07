"""CLI for the frozen FinQA raw/gold ledger pair."""

import argparse
from .generate import generate_ledgers, load_json, write_ledgers
from .provenance import assert_lock_ready


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--raw-out", required=True)
    parser.add_argument("--gold-out", required=True)
    parser.add_argument("--tokenizer", required=True, help="pinned local tokenizer directory")
    parser.add_argument("--base-model", required=True, help="pinned local base model directory")
    parser.add_argument("--adapter", required=True, help="pinned local adapter directory")
    parser.add_argument("--lock", required=True, help="frozen provenance lock")
    args = parser.parse_args()
    assert_lock_ready(args.lock)
    from .model import load_generator
    tokenizer, generator = load_generator(args.base_model, args.adapter, args.tokenizer)
    raw, gold, meta = generate_ledgers(load_json(args.data), "finqa", tokenizer, lambda p: generator(p, max_new_tokens=30, do_sample=False)[0]["generated_text"])
    print(meta)
    print(write_ledgers(raw, gold, args.raw_out, args.gold_out))


if __name__ == "__main__":
    main()
