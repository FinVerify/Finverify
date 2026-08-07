# Pre-execution implementation freeze notes

These notes document implementation decisions without populating any
execution-dependent provenance hashes.

## TAT-QA eligibility

The canonical development split is the only permitted split. Eligibility is
mechanical: the stored final answer must parse as numeric and the answer type
must be absent or explicitly arithmetic/numeric. Span, multi-span, textual,
yes/no, and all other non-numeric answer types are excluded. Model
predictions, model outputs, and derivation metadata cannot affect eligibility.

## Bootstrap

The bootstrap uses 10,000 resamples, percentile 95% confidence intervals,
and deterministic RNG seed `0`. The seed is an implementation reproducibility
parameter and is not selected from outcomes.

## Prompt/chat-template check

Ledger generation constructs the frozen prompt string and passes it directly
to the text-generation pipeline. The code does not call
`tokenizer.apply_chat_template` or any equivalent chat-template method. No
chat wrapper is added and the frozen prompt bytes are unchanged.

## FCG alias matching

FCG concept extraction uses only `METRIC_ALIASES` after Unicode
normalization, case folding, and whitespace collapsing. Matching is exact and
bounded. If aliases overlap, the longest non-overlapping alias wins. Sorting
aliases and canonical names makes extraction independent of registry order.
