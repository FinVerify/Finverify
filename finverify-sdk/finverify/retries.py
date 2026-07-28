"""
finverify.retries — Retry policy
==================================
Pure functions with no I/O, so both the sync and async transports share
one definition of "what counts as retryable" and "how long to wait."
"""

from __future__ import annotations

import random
from typing import Optional

from .exceptions import APIError


def is_retryable_status(status_code: int) -> bool:
    """429 and 5xx are retryable; everything else is a client error."""
    return status_code == 429 or status_code >= 500


def is_retryable_exception(exc: BaseException) -> bool:
    if isinstance(exc, APIError):
        return exc.retryable
    # Bare connection resets / transient network errors are retried;
    # the transport layer is responsible for wrapping these as
    # finverify.exceptions.ConnectionError before this is checked
    # anywhere the SDK boundary matters, but during raw socket/HTTP
    # library exceptions we still want a chance to retry.
    return True


def compute_backoff(
    attempt: int,
    *,
    base: float,
    maximum: float,
    retry_after: Optional[float] = None,
) -> float:
    """Exponential backoff with full jitter, honoring a server-provided
    Retry-After value when present.

    Parameters
    ----------
    attempt : int
        0-indexed retry attempt number (0 = first retry).
    """
    if retry_after is not None:
        return min(retry_after, maximum)
    exp = min(base * (2 ** attempt), maximum)
    return random.uniform(0, exp)


__all__ = ["is_retryable_status", "is_retryable_exception", "compute_backoff"]
