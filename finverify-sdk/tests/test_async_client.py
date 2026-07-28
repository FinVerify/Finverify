import httpx
import pytest
import respx

from finverify import AsyncFinVerify
from finverify.exceptions import ServerError

BASE = "https://test.finverify.local"

pytestmark = pytest.mark.asyncio


@respx.mock
async def test_async_verify_success():
    respx.post(f"{BASE}/v1/verify").mock(
        return_value=httpx.Response(
            200,
            json={
                "question": "P/E ratio",
                "raw_value": 28.5,
                "verified_value": 28.5,
                "trust_score": "HIGH",
                "trust_color": "#00ff88",
                "delta_pct": 0.0,
            },
        )
    )
    async with AsyncFinVerify(base_url=BASE) as client:
        result = await client.verify(question="P/E ratio", raw_value=28.5)
    assert result.trust_score == "HIGH"
    assert result.was_corrected is False


@respx.mock
async def test_async_verify_batch():
    respx.post(f"{BASE}/v1/verify").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "question": "a",
                    "raw_value": 1.0,
                    "verified_value": 1.0,
                    "trust_score": "HIGH",
                    "trust_color": "#00ff88",
                    "delta_pct": 0.0,
                },
            ),
            httpx.Response(500, json={"detail": "fail"}),
        ]
    )
    async with AsyncFinVerify(base_url=BASE, max_retries=0) as client:
        batch = await client.verify_batch(
            [{"question": "a", "raw_value": 1.0}, {"question": "b", "raw_value": 2.0}]
        )
    assert len(batch.succeeded) == 1
    assert batch.failed_count == 1
    assert isinstance(batch.errors[1], ServerError)


@respx.mock
async def test_async_market_quotes():
    respx.get(f"{BASE}/market/quotes").mock(
        return_value=httpx.Response(200, json={"AAPL": {"price": 200.1}})
    )
    async with AsyncFinVerify(base_url=BASE) as client:
        quotes = await client.market.quotes(["AAPL"])
    assert quotes["AAPL"]["price"] == 200.1
