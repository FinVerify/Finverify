"""
finverify.client — Synchronous FinVerify client
=================================================
::

    from finverify import FinVerify

    client = FinVerify()
    result = client.verify(question="What was Apple's FY2024 revenue?", raw_value=391.0)
    print(result.verified_value, result.trust_score)

    with FinVerify() as client:
        ...
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
from .transport import SyncTransport


class _FundamentalsAPI:
    """Namespace for ``client.fundamentals.*`` — SEC EDGAR data."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def get(self, ticker: str):
        method, path, body, params = fundamentals_res.build_fundamentals_request(ticker)
        data = self._t.request(method, path, json_body=body, params=params)
        return fundamentals_res.parse_fundamentals_response(data)

    def earnings(self, ticker: str):
        method, path, body, params = fundamentals_res.build_earnings_request(ticker)
        data = self._t.request(method, path, json_body=body, params=params)
        return fundamentals_res.parse_earnings_response(data)

    def ingest(self, tickers: Optional[list[str]] = None) -> dict:
        method, path, body, params = fundamentals_res.build_ingest_sec_request(tickers)
        return self._t.request(method, path, json_body=body, params=params)

    def ingest_transcripts(self, tickers: Optional[list[str]] = None) -> dict:
        method, path, body, params = fundamentals_res.build_ingest_transcripts_request(tickers)
        return self._t.request(method, path, json_body=body, params=params)


class _MarketAPI:
    """Namespace for ``client.market.*`` — live quotes and indices."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def quotes(self, symbols: Optional[list[str]] = None) -> dict:
        method, path, body, params = market_res.build_quotes_request(symbols)
        return self._t.request(method, path, json_body=body, params=params)

    def indices(self) -> dict:
        method, path, body, params = market_res.build_indices_request()
        return self._t.request(method, path, json_body=body, params=params)

    def metric(self, symbol: str, metric: str = "profit_margin") -> dict:
        method, path, body, params = market_res.build_verified_metric_request(symbol, metric)
        return self._t.request(method, path, json_body=body, params=params)

    def all_metrics(self, symbol: str) -> dict:
        method, path, body, params = market_res.build_all_metrics_request(symbol)
        return self._t.request(method, path, json_body=body, params=params)


class _RAGAPI:
    """Namespace for ``client.rag.*`` — vector search over ingested filings."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def stats(self) -> dict:
        method, path, body, params = rag_res.build_rag_stats_request()
        return self._t.request(method, path, json_body=body, params=params)

    def query(self, question: str, top_k: int = 5) -> dict:
        method, path, body, params = rag_res.build_rag_query_request(question, top_k)
        return self._t.request(method, path, json_body=body, params=params)

    def seed(self) -> dict:
        method, path, body, params = rag_res.build_rag_seed_request()
        return self._t.request(method, path, json_body=body, params=params)


class _HistoryAPI:
    """Namespace for ``client.history.*`` — Supabase-backed query history."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def get(self, user_id: str, limit: int = 20, trust: Optional[str] = None):
        method, path, body, params = history_res.build_get_history_request(user_id, limit, trust)
        data = self._t.request(method, path, json_body=body, params=params)
        return history_res.parse_get_history_response(data)

    def save(
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
        return self._t.request(method, path, json_body=body, params=params)

    def delete(self, user_id: str) -> dict:
        method, path, body, params = history_res.build_delete_history_request(user_id)
        return self._t.request(method, path, json_body=body, params=params)


class _FCGAPI:
    """Namespace for ``client.fcg.*`` — multi-number constraint verification."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def verify(self, values: dict, normalize: bool = True):
        method, path, body, params = fcg_res.build_fcg_verify_request(values, normalize)
        data = self._t.request(method, path, json_body=body, params=params)
        return fcg_res.parse_fcg_verify_response(data)

    def normalize(self, names: list[str]):
        method, path, body, params = fcg_res.build_fcg_normalize_request(names)
        data = self._t.request(method, path, json_body=body, params=params)
        return fcg_res.parse_fcg_normalize_response(data)

    def constraints(self):
        method, path, body, params = fcg_res.build_fcg_constraints_request()
        data = self._t.request(method, path, json_body=body, params=params)
        return fcg_res.parse_fcg_constraints_response(data)


class FinVerify:
    """
    Synchronous client for the FinVerify DVL API.

    Parameters
    ----------
    api_key : str, optional
        Sent as ``X-FinVerify-Key``. Falls back to the ``FINVERIFY_API_KEY``
        environment variable.
    base_url : str, optional
        API root. Falls back to ``FINVERIFY_BASE_URL``, then the public
        FinVerify endpoint.
    timeout : float, optional
        Per-request timeout in seconds (default: 15).
    max_retries : int, optional
        Retries for 429/5xx responses and transient network errors,
        with exponential backoff (default: 2).

    Examples
    --------
    >>> client = FinVerify()
    >>> result = client.verify(question="What was the P/E ratio?", raw_value=28.5)
    >>> result.trust_score
    'HIGH'
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        *,
        _transport: Optional[SyncTransport] = None,
    ) -> None:
        cfg = ClientConfig.resolve(
            base_url=base_url, api_key=api_key, timeout=timeout, max_retries=max_retries
        )
        self._cfg = cfg
        self._transport = _transport or SyncTransport(cfg)

        self.fundamentals = _FundamentalsAPI(self._transport)
        self.market = _MarketAPI(self._transport)
        self.rag = _RAGAPI(self._transport)
        self.history = _HistoryAPI(self._transport)
        self.fcg = _FCGAPI(self._transport)

    # -- lifecycle -----------------------------------------------------

    def close(self) -> None:
        """Release pooled connections. Safe to call multiple times."""
        self._transport.close()

    def __enter__(self) -> "FinVerify":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # -- core verification ----------------------------------------------

    def verify(
        self,
        question: str,
        raw_value: float,
        model_source: Optional[str] = None,
    ) -> VerifyResult:
        """Verify a single financial number through the DVL API.

        Parameters
        ----------
        question : str
            The financial question (used for ratio/sign keyword detection).
        raw_value : float
            The number to verify, as extracted from an LLM's answer.
        model_source : str, optional
            Identifier for the model that produced ``raw_value`` — passed
            through for FinVerify's own logging, not required.
        """
        method, path, body, params = verify_res.build_verify_request(question, raw_value, model_source)
        data = self._transport.request(method, path, json_body=body, params=params)
        return verify_res.parse_verify_response(data)

    def verify_batch(
        self,
        items: list[dict],
        *,
        max_workers: int = 8,
    ) -> BatchVerifyResult:
        """Verify multiple financial numbers concurrently.

        .. note::
           The backend does not yet expose a native batch endpoint
           (``POST /v1/verify`` accepts one claim per call), so this
           fans requests out across a thread pool rather than sending
           one batched HTTP request. A true server-side batch endpoint
           is tracked as a roadmap item — see the SDK README.

        Parameters
        ----------
        items : list[dict]
            Each dict needs ``question`` and ``raw_value``, and may
            include ``model_source``.
        max_workers : int
            Size of the thread pool used to fan requests out.
        """
        results: list[Optional[VerifyResult]] = [None] * len(items)
        errors: list[Optional[BaseException]] = [None] * len(items)

        def _run(index: int, item: dict) -> None:
            try:
                results[index] = self.verify(
                    question=item["question"],
                    raw_value=item["raw_value"],
                    model_source=item.get("model_source"),
                )
            except BaseException as e:  # noqa: BLE001 - captured per-item, not swallowed
                errors[index] = e

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_run, i, item) for i, item in enumerate(items)]
            for f in futures:
                f.result()

        return BatchVerifyResult(results=results, errors=errors)

    # -- health / discovery ----------------------------------------------

    def health(self):
        method, path, body, params = meta_res.build_health_request()
        data = self._transport.request(method, path, json_body=body, params=params)
        return meta_res.parse_health_response(data)

    def sample_queries(self):
        method, path, body, params = meta_res.build_sample_queries_request()
        data = self._transport.request(method, path, json_body=body, params=params)
        return meta_res.parse_sample_queries_response(data)


__all__ = ["FinVerify"]
