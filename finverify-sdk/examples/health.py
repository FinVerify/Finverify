"""Run: python examples/health.py

Checks whether the FinVerify API, its DVL, and its fine-tuned model
are up before sending real traffic — useful in a startup probe.
"""

from finverify import FinVerify, FinVerifyError


def main() -> None:
    with FinVerify() as client:
        try:
            status = client.health()
        except FinVerifyError as e:
            print(f"Could not reach FinVerify API: {e}")
            return

        print(f"status: {status.status}")
        print(f"dvl:    {status.dvl}")
        print(f"llm:    {status.llm}")
        print(f"model:  {status.model}")
        print(f"healthy: {status.is_healthy}")


if __name__ == "__main__":
    main()
