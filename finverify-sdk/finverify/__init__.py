"""
FinVerify — Official Python SDK
=================================
Deterministic verification for financial LLM outputs. Wraps the
FinVerify DVL API (https://aadi2026-finverify-api.hf.space) with a
typed, retrying, sync + async client.

Quick start
-----------
    from finverify import FinVerify

    client = FinVerify()
    result = client.verify(question="What was Apple's FY2024 revenue?", raw_value=391.0)
    print(result.verified_value)
    print(result.trust_score)

Async
-----
    import asyncio
    from finverify import AsyncFinVerify

    async def main():
        async with AsyncFinVerify() as client:
            result = await client.verify(question="P/E ratio", raw_value=28.5)
            print(result.trust_score)

    asyncio.run(main())

Local, zero-network verification
---------------------------------
    from finverify import verify_local

    result = verify_local("profit margin", 0.2531)
    print(result.verified_value)  # 25.31
"""

from .async_client import AsyncFinVerify
from .client import FinVerify
from .dvl import DVLResult, verify_local
from .exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    ConnectionError,
    FinVerifyError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from .models import (
    BatchVerifyResult,
    Constraint,
    CorrectionEntry,
    EarningsReport,
    FCGVerifyResult,
    FundamentalsResult,
    HealthStatus,
    HistoryEntry,
    NormalizeResult,
    SampleQuery,
    VerifyResult,
)
from .normalizer import normalize_metric_name
from .version import __version__

__all__ = [
    "__version__",
    # Clients
    "FinVerify",
    "AsyncFinVerify",
    # Local (no network) verification
    "verify_local",
    "DVLResult",
    "normalize_metric_name",
    # Models
    "VerifyResult",
    "BatchVerifyResult",
    "CorrectionEntry",
    "HealthStatus",
    "FundamentalsResult",
    "EarningsReport",
    "FCGVerifyResult",
    "NormalizeResult",
    "Constraint",
    "SampleQuery",
    "HistoryEntry",
    # Exceptions
    "FinVerifyError",
    "ConnectionError",
    "TimeoutError",
    "APIError",
    "APIConnectionError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
]
