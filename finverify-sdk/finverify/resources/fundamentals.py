"""finverify.resources.fundamentals — SEC EDGAR fundamentals + earnings."""

from __future__ import annotations

from typing import Optional

from ..models import EarningsReport, FundamentalsResult
from ..validators import require_ticker


def build_fundamentals_request(ticker: str) -> tuple[str, str, None, None]:
    ticker = require_ticker(ticker)
    return "GET", f"/v1/fundamentals/{ticker}", None, None


def parse_fundamentals_response(data: dict) -> FundamentalsResult:
    return FundamentalsResult.from_dict(data)


def build_earnings_request(ticker: str) -> tuple[str, str, None, None]:
    ticker = require_ticker(ticker)
    return "GET", f"/v1/earnings/{ticker}", None, None


def parse_earnings_response(data: dict) -> EarningsReport:
    return EarningsReport.from_dict(data)


def build_ingest_sec_request(tickers: Optional[list[str]] = None) -> tuple[str, str, None, dict]:
    params = {}
    if tickers:
        params["tickers"] = ",".join(t.upper() for t in tickers)
    return "POST", "/v1/ingest/sec", None, params


def build_ingest_transcripts_request(tickers: Optional[list[str]] = None) -> tuple[str, str, None, dict]:
    params = {}
    if tickers:
        params["tickers"] = ",".join(t.upper() for t in tickers)
    return "POST", "/v1/ingest/transcripts", None, params


__all__ = [
    "build_fundamentals_request",
    "parse_fundamentals_response",
    "build_earnings_request",
    "parse_earnings_response",
    "build_ingest_sec_request",
    "build_ingest_transcripts_request",
]
