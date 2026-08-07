# Research

This directory contains research papers, notebooks, and supplementary material.
Selective-intervention implementation

The frozen protocol implementation is split into gold-independent ledger
serialization/intervention/FCG modules and a separate scoring/statistics
process. Existing application DVL/FCG APIs remain historical, gold-aware or
fuzzy-compatible paths and are not modified by this study implementation.

The provenance lock is plumbing only: unresolved dataset/model revisions and
execution hashes must be populated mechanically before outcome-producing
execution. Generated artifacts are write-once and hashed with SHA-256.

Frozen implementation decisions:

- TAT-QA uses only the canonical development split. An example is eligible
  only when its stored final answer is numeric; span, multi-span, textual,
  yes/no, and other non-numeric answer types are excluded mechanically.
  Eligibility never uses model predictions.
- Bootstrap uses 10,000 resamples with RNG seed `0` and percentile 95% CIs.
- FCG uses exact normalized aliases only. Overlapping aliases resolve to the
  longest non-overlapping match, independent of registry order.
- Ledger generation passes the frozen prompt as a plain string to the text
  generation pipeline. It does not invoke `apply_chat_template`; therefore
  tokenizer chat-template wrapping does not modify the frozen prompt bytes.

Run focused tests from the repository root:

    python -m pytest research/tests

The FinQA/TAT-QA CLI entry points require locally pinned tokenizer/model
artifacts and explicit raw/gold output paths. They do not run automatically.

Example execution commands (after the provenance lock is frozen and the
locally cached revisions have been verified):

    python -m research.ledger.generate_finqa_ledger --data <FinQA>/dataset/dev.json --raw-out research/ledger/finqa_dev_raw_ledger.jsonl --gold-out research/ledger/finqa_dev_gold.jsonl --tokenizer <tokenizer> --base-model <base-model> --adapter <adapter> --lock research/protocols/PREEXECUTION_PROVENANCE_LOCK.json

    python -m research.ledger.generate_tatqa_ledger --data <TAT-QA>/dataset_raw/tatqa_dataset_dev.json --raw-out research/ledger/tatqa_dev_raw_ledger.jsonl --gold-out research/ledger/tatqa_dev_gold.jsonl --tokenizer <tokenizer> --base-model <base-model> --adapter <adapter> --lock research/protocols/PREEXECUTION_PROVENANCE_LOCK.json

Then run the blind stage in its isolated process:

    python -m research.intervention.run_blind --raw research/ledger/finqa_dev_raw_ledger.jsonl --output research/ledger/finqa_dev_intervention_ledger.jsonl
