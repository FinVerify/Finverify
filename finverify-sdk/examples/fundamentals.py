"""Run: python examples/fundamentals.py

Pulls SEC EDGAR-sourced fundamentals and an earnings-call verification
report for a ticker.
"""

from finverify import FinVerify, FinVerifyError


def main() -> None:
    with FinVerify() as client:
        try:
            fundamentals = client.fundamentals.get("AAPL")
        except FinVerifyError as e:
            print(f"Fundamentals lookup failed: {e}")
            return

        print(f"Ticker:  {fundamentals.ticker}")
        print(f"Source:  {fundamentals.source}")
        print(f"Metrics: {fundamentals.metrics_count}")
        for name, value in fundamentals.metrics.items():
            print(f"  {name}: {value}")

        try:
            earnings = client.fundamentals.earnings("AAPL")
            print(f"\nEarnings report keys: {list(earnings.raw.keys())}")
        except FinVerifyError as e:
            print(f"Earnings lookup failed (may need /v1/ingest/transcripts first): {e}")


if __name__ == "__main__":
    main()
