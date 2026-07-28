"""Run: python examples/batch_verify.py

Verifies several claims concurrently.

NOTE: the FinVerify backend does not expose a native batch endpoint —
this sends one HTTP request per item over a thread pool. See
docs/roadmap.md for the tracked "real" batch endpoint proposal.
"""

from finverify import FinVerify


def main() -> None:
    claims = [
        {"question": "What was the profit margin?", "raw_value": 0.2531},
        {"question": "What was the P/E ratio?", "raw_value": 28.5},
        {"question": "What was the revenue growth rate?", "raw_value": 0.0623},
    ]

    with FinVerify() as client:
        batch = client.verify_batch(claims, max_workers=4)

    print(f"{len(batch.succeeded)}/{len(batch)} succeeded, {batch.failed_count} failed\n")

    for item, result, error in zip(claims, batch.results, batch.errors):
        if result is not None:
            print(f"OK   {item['question']!r} -> {result.verified_value} ({result.trust_score})")
        else:
            print(f"FAIL {item['question']!r} -> {error}")


if __name__ == "__main__":
    main()
