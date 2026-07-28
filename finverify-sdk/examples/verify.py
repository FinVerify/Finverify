"""Run: python examples/verify.py

Verifies a single financial number through the FinVerify DVL API.
"""

from finverify import FinVerify, FinVerifyError


def main() -> None:
    with FinVerify() as client:
        try:
            result = client.verify(
                question="What was Apple's FY2024 total revenue?",
                raw_value=391.0,
            )
        except FinVerifyError as e:
            print(f"Verification failed: {e}")
            return

        print(f"Question:        {result.question}")
        print(f"Raw value:       {result.raw_value}")
        print(f"Verified value:  {result.verified_value}")
        print(f"Trust score:     {result.trust_score} ({result.trust_color})")
        print(f"Was corrected:   {result.was_corrected}")
        if result.was_corrected:
            print(f"Correction rule: {result.correction_applied}")


if __name__ == "__main__":
    main()
