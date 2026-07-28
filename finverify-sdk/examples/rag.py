"""Run: python examples/rag.py

Vector search over ingested SEC filings / transcripts.
"""

from finverify import FinVerify, FinVerifyError


def main() -> None:
    with FinVerify() as client:
        try:
            stats = client.rag.stats()
            print("RAG index stats:", stats)

            results = client.rag.query("What did management say about margins?", top_k=3)
            print("Query results:", results)
        except FinVerifyError as e:
            print(f"RAG request failed: {e}")


if __name__ == "__main__":
    main()
