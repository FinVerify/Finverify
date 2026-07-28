"""Run: python examples/history.py

Saves a verification result to a user's history, lists it back, then
cleans up. Uses a throwaway user_id so it's safe to run repeatedly.
"""

from finverify import FinVerify, FinVerifyError


def main() -> None:
    user_id = "sdk-example-user"

    with FinVerify() as client:
        try:
            client.history.save(
                user_id=user_id,
                question="What was the profit margin?",
                raw_value=0.2531,
                verified_value=25.31,
                trust="MEDIUM",
                display_value="25.31%",
                correction_log=["scale_mul100"],
            )

            entries = client.history.get(user_id, limit=5)
            print(f"{len(entries)} entries for {user_id}:")
            for e in entries:
                print(f"  - {e.question} -> {e.verified_value} ({e.trust})")

            client.history.delete(user_id)
            print("Deleted history for", user_id)
        except FinVerifyError as e:
            print(f"History request failed: {e}")


if __name__ == "__main__":
    main()
