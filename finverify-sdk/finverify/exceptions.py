"""
finverify.exceptions — SDK exception hierarchy
===============================================
Every error the SDK raises inherits from :class:`FinVerifyError`, so a
caller can always do::

    try:
        client.verify(question="...", raw_value=1.0)
    except FinVerifyError as e:
        ...

More specific subclasses let callers branch on failure mode (retry,
surface to the user, log and continue, etc.).
"""

from __future__ import annotations

from typing import Any, Optional


class FinVerifyError(Exception):
    """Base class for all errors raised by the FinVerify SDK."""


# ---------------------------------------------------------------------------
# Network / transport-level errors
# ---------------------------------------------------------------------------

class ConnectionError(FinVerifyError):
    """Raised when the SDK cannot reach the FinVerify API at all.

    This covers DNS failures, refused connections, and TLS errors —
    i.e. cases where no HTTP response was ever received.
    """


class TimeoutError(FinVerifyError):
    """Raised when a request exceeds the configured timeout."""


# ---------------------------------------------------------------------------
# HTTP-response-level errors
# ---------------------------------------------------------------------------

class APIError(FinVerifyError):
    """Base class for errors returned by the FinVerify API itself.

    Attributes
    ----------
    status_code : int | None
        The HTTP status code returned by the server, if any.
    request_id : str | None
        Correlation id echoed back by the server, if the API provides one.
    body : Any
        The parsed (or raw) response body, for debugging.
    """

    #: Whether the SDK's built-in retry logic should retry this error class.
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.body = body

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"(HTTP {self.status_code})")
        if self.request_id:
            parts.append(f"[request_id={self.request_id}]")
        return " ".join(parts)


class AuthenticationError(APIError):
    """Raised on HTTP 401 — missing or invalid credentials."""

    retryable = False


class PermissionDeniedError(APIError):
    """Raised on HTTP 403 — credentials valid but not authorized."""

    retryable = False


class NotFoundError(APIError):
    """Raised on HTTP 404 — the resource does not exist."""

    retryable = False


class ValidationError(APIError):
    """Raised on HTTP 400/422 — the request payload was rejected.

    Distinct from Python's built-in exceptions to avoid clashing with
    stdlib ``ValidationError``-shaped code elsewhere in a caller's app.
    """

    retryable = False


class RateLimitError(APIError):
    """Raised on HTTP 429 — the 100 requests/minute limit was hit.

    Attributes
    ----------
    retry_after : float | None
        Seconds to wait before retrying, parsed from a ``Retry-After``
        header when the server sends one.
    """

    retryable = True

    def __init__(self, *args: Any, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ServerError(APIError):
    """Raised on HTTP 5xx — a problem on FinVerify's side."""

    retryable = True


class APIConnectionError(ConnectionError, APIError):
    """Raised when a connection is established but the response is malformed
    (e.g. non-JSON body where JSON was expected)."""

    retryable = True


__all__ = [
    "FinVerifyError",
    "ConnectionError",
    "TimeoutError",
    "APIError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "APIConnectionError",
]
