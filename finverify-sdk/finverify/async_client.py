"""
finverify.async_client — Async FinVerify client
=================================================
::

    import asyncio
    from finverify import AsyncFinVerify

    async def main():
        async with AsyncFinVerify() as client:
            result = await client.verify(question="P/E ratio", raw_value=28.5)
            print(result.trust_score)

    asyncio.run(main())
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from .config import ClientConfig
from .models import BatchVerifyResult, VerifyResult
from .resources import fcg as fcg_res
from .resources import fundamentals as fundamentals_res
from .resources import history as history_res
from .resources import market as market_res
from .resources import meta as meta_res
from .resources import rag as rag_res
from .resources import verify as verify_res
from .transport import AsyncTransport


class _AsyncFundamentalsAPI:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def get(self, ticker: str):
        method, path, body, params = fundamentals_res.build_fundamentals_request(ticker)
        data = await self._t.request(method, path, json_body=body, params=params)
        return fundamentals_res.parse_fundamentals_response(data)

    async def earnings(self, ticker: str):
        method, path, body, params = fundamentals_res.build_earnings_request(ticker)
        data = await self._t.request(method, path, json_body=body, params=params)
        return fundamentals_res.parse_earnings_response(data)

    async def ingest(self, tickers: Optional[list[str]] = None) -> dict:
        method, path, body, params = fundamentals_res.build_ingest_sec_request(tickers)
        return await self._t.request(method, path, json_body=body, params=params)

    async def ingest_transcripts(self, tickers: Optional[list[str]] = None) -> dict:
        method, path, body, params = fundamentals_res.build_ingest_transcripts_request(tickers)
        return await self._t.request(method, path, json_body=body, params=params)


class _AsyncMarketAPI:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def quotes(self, symbols: Optional[list[str]] = None) -> dict:
        method, path, body, params = market_res.build_quotes_request(symbols)
        return await self._t.request(method, path, json_body=body, params=params)

    async def indices(self) -> dict:
        method, path, body, params = market_res.build_indices_request()
        return await self._t.request(method, path, json_body=body, params=params)

    async def metric(self, symbol: str, metric: str = "profit_margin") -> dict:
        method, path, body, params = market_res.build_verified_metric_request(symbol, metric)
        return await self._t.request(method, path, json_body=body, params=params)

    async def all_metrics(self, symbol: str) -> dict:
        method, path, body, params = market_res.build_all_metrics_request(symbol)
        return await self._t.request(method, path, json_body=body, params=params)


class _AsyncRAGAPI:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def stats(self) -> dict:
        method, path, body, params = rag_res.build_rag_stats_request()
        return await self._t.request(method, path, json_body=body, params=params)

    async def query(self, question: str, top_k: int = 5) -> dict:
        method, path, body, params = rag_res.build_rag_query_request(question, top_k)
        return await self._t.request(method, path, json_body=body, params=params)

    async def seed(self) -> dict:
        method, path, body, params = rag_res.build_rag_seed_request()
        return await self._t.request(method, path, json_body=body, params=params)


class _AsyncHistoryAPI:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def get(self, user_id: str, limit: int = 20, trust: Optional[str] = None):
        method, path, body, params = history_res.build_get_history_request(user_id, limit, trust)
        data = await self._t.request(method, path, json_body=body, params=params)
        return history_res.parse_get_history_response(data)

    async def save(
        self,
        user_id: str,
        question: str,
        raw_value: Optional[float] = None,
        verified_value: Optional[float] = None,
        trust: str = "HIGH",
        display_value: str = "",
        correction_log: Optional[list] = None,
    ) -> dict:
        method, path, body, params = history_res.build_save_history_request(
            user_id, question, raw_value, verified_value, trust, display_value, correction_log
        )
        return await self._t.request(method, path, json_body=body, params=params)

    async def delete(self, user_id: str) -> dict:
        method, path, body, params = history_res.build_delete_history_request(user_id)
        return await self._t.request(method, path, json_body=body, params=params)


class _AsyncFCGAPI:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def verify(self, values: dict, normalize: bool = True):
        method, path, body, params = fcg_res.build_fcg_verify_request(values, normalize)
        data = await self._t.request(method, path, json_body=body, params=params)
        return fcg_res.parse_fcg_verify_response(data)

    async def normalize(self, names: list[str]):
        method, path, body, params = fcg_res.build_fcg_normalize_request(names)
        data = await self._t.request(method, path, json_body=body, params=params)
        return fcg_res.parse_fcg_normalize_response(data)

    async def constraints(self):
        method, path, body, params = fcg_res.build_fcg_constraints_request()
        data = await self._t.request(method, path, json_body=body, params=params)
        return fcg_res.parse_fcg_constraints_response(data)


class AsyncFinVerify:
    """Async client for the FinVerify DVL API. See :class:`finverify.FinVerify`
    for the full parameter and endpoint documentation — the two clients
    are kept in lockstep so anything true of one is true of the other."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        *,
        _transport: Optional[AsyncTransport] = None,
    ) -> None:
        cfg = ClientConfig.resolve(
            base_url=base_url, api_key=api_key, timeout=timeout, max_retries=max_retries
        )
        self._cfg = cfg
        self._transport = _transport or AsyncTransport(cfg)

        self.fundamentals = _AsyncFundamentalsAPI(self._transport)
        self.market = _AsyncMarketAPI(self._transport)
        self.rag = _AsyncRAGAPI(self._transport)
        self.history = _AsyncHistoryAPI(self._transport)
        self.fcg = _AsyncFCGAPI(self._transport)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncFinVerify":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()

    async def verify(
        self,
        question: str,
        raw_value: float,
        model_source: Optional[str] = None,
    ) -> VerifyResult:
        method, path, body, params = verify_res.build_verify_request(question, raw_value, model_source)
        data = await self._transport.request(method, path, json_body=body, params=params)
        return verify_res.parse_verify_response(data)

    async def verify_batch(
        self,
        items: list[dict],
        *,
        max_concurrency: int = 8,
    ) -> BatchVerifyResult:
        """Async counterpart to :meth:`FinVerify.verify_batch` — see there
        for the note on this being client-side fan-out, not a native
        backend batch endpoint."""
        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[Optional[VerifyResult]] = [None] * len(items)
        errors: list[Optional[BaseException]] = [None] * len(items)

        async def _run(index: int, item: dict) -> None:
            async with semaphore:
                try:
                    results[index] = await self.verify(
                        question=item["question"],
                        raw_value=item["raw_value"],
                        model_source=item.get("model_source"),
                    )
                except BaseException as e:  # noqa: BLE001
                    errors[index] = e

        await asyncio.gather(*(_run(i, item) for i, item in enumerate(items)))
        return BatchVerifyResult(results=results, errors=errors)

    async def health(self):
        method, path, body, params = meta_res.build_health_request()
        data = await self._transport.request(method, path, json_body=body, params=params)
        return meta_res.parse_health_response(data)

    async def sample_queries(self):
        method, path, body, params = meta_res.build_sample_queries_request()
        data = await self._transport.request(method, path, json_body=body, params=params)
        return meta_res.parse_sample_queries_response(data)


__all__ = ["AsyncFinVerify"]
