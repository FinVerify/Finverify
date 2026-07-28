"""Run: python examples/fcg.py

The Financial Constraint Graph (FCG) checks a *set* of related numbers
against each other (e.g. gross margin = (revenue - cogs) / revenue),
rather than verifying one number in isolation like verify() does.
"""

from finverify import FinVerify, FinVerifyError


def main() -> None:
    with FinVerify() as client:
        try:
            constraints = client.fcg.constraints()
            print(f"{len(constraints)} constraints available:")
            for c in constraints:
                print(f"  - {c.id}: {c.description} (severity={c.severity})")

            normalized = client.fcg.normalize(["net revenues", "cost of goods sold"])
            print("\nNormalized names:", normalized.mapped)

            result = client.fcg.verify({"revenue": 391.0, "cogs": 210.0, "gross_margin": 46.3})
            print("\nConstraint check:", result.constraint_result)
        except FinVerifyError as e:
            print(f"FCG request failed: {e}")


if __name__ == "__main__":
    main()
