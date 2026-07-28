"""finverify.resources.market — live quotes, indices, DVL-verified metrics."""

from __future__ import annotations

from typing import Optional


def build_quotes_request(symbols: Optional[list[str]] = None) -> tuple[str, str, None, dict]:
    params = {}
    if symbols:
        params["symbols"] = ",".join(s.upper() for s in symbols)
    return "GET", "/market/quotes", None, params


def build_indices_request() -> tuple[str, str, None, None]:
    return "GET", "/market/indices", None, None


def build_verified_metric_request(symbol: str, metric: str) -> tuple[str, str, None, dict]:
    params = {"symbol": symbol.upper(), "metric": metric}
    return "GET", "/market/verified-metrics", None, params


def build_all_metrics_request(symbol: str) -> tuple[str, str, None, dict]:
    params = {"symbol": symbol.upper()}
    return "GET", "/market/all-metrics", None, params


__all__ = [
    "build_quotes_request",
    "build_indices_request",
    "build_verified_metric_request",
    "build_all_metrics_request",
]
