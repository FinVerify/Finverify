"""Run: python examples/async_verify.py

Same as verify.py, but using the async client — useful inside an
already-async app (FastAPI route, Discord bot, etc.) so verification
doesn't block the event loop.
"""

import asyncio

from finverify import AsyncFinVerify, FinVerifyError


async def main() -> None:
    async with AsyncFinVerify() as client:
        try:
            result = await client.verify(
                question="What was the company's profit margin?",
                raw_value=0.2531,
            )
        except FinVerifyError as e:
            print(f"Verification failed: {e}")
            return

        print(f"Verified value: {result.verified_value}")
        print(f"Trust score:    {result.trust_score}")


if __name__ == "__main__":
    asyncio.run(main())
