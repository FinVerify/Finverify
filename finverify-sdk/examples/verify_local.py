"""Run: python examples/verify_local.py

verify_local() runs the same DVL correction rules used by the API,
entirely in-process — no network call, no API key, no rate limit.
Useful for unit tests, offline batch jobs, or as a fallback when the
API is unreachable.
"""

from finverify import verify_local


def main() -> None:
    cases = [
        ("What was the profit margin?", 0.2531),   # scale correction expected
        ("What was the P/E ratio?", 28.5),          # left alone
        ("What was the revenue growth?", -0.08),    # sign correction expected
    ]

    for question, raw_value in cases:
        result = verify_local(question, raw_value)
        marker = "corrected" if result.was_corrected else "unchanged"
        print(f"{question!r}: {raw_value} -> {result.verified_value} "
              f"[{result.trust_score}, {marker}]")


if __name__ == "__main__":
    main()
