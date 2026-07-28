"""Run: python examples/market.py

Live quotes, index snapshots, and a single DVL-verified metric.
"""

from finverify import FinVerify, FinVerifyError


def main() -> None:
    with FinVerify() as client:
        try:
            quotes = client.market.quotes(["AAPL", "MSFT"])
            print("Quotes:", quotes)

            indices = client.market.indices()
            print("Indices:", indices)

            metric = client.market.metric("AAPL", "profit_margin")
            print("Verified metric:", metric)
        except FinVerifyError as e:
            print(f"Market data request failed: {e}")


if __name__ == "__main__":
    main()
