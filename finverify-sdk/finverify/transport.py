"""
finverify.transport — HTTP transport layer
=============================================
Everything network-shaped lives here: connection pooling, retries with
backoff, timeouts, and mapping HTTP responses to typed exceptions.
``client.py`` and ``async_client.py`` both build on this so the retry
and error-handling logic is written exactly once.

httpx is used (rather than stdlib ``urllib``) because it gives us
connection pooling and one API surface shared between sync and async —
the same reason the OpenAI and Anthropic Python SDKs use it.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from .auth import build_headers
from .config import ClientConfig
from .exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    ConnectionError as FinVerifyConnectionError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    TimeoutError as FinVerifyTimeoutError,
    ValidationError,
)
from .retries import compute_backoff, is_retryable_status
from .version import __version__

logger = logging.getLogger("finverify")

_USER_AGENT = f"finverify-python/{__version__}"


def _raise_for_error_status(
    status_code: int,
    body: Any,
    *,
    request_id: Optional[str],
    retry_after: Optional[float],
) -> None:
    message = _extract_message(body) or f"FinVerify API returned HTTP {status_code}"
    kwargs = dict(status_code=status_code, request_id=request_id, body=body)

    if status_code == 401:
        raise AuthenticationError(message, **kwargs)
    if status_code == 403:
        raise PermissionDeniedError(message, **kwargs)
    if status_code == 404:
        raise NotFoundError(message, **kwargs)
    if status_code in (400, 422):
        raise ValidationError(message, **kwargs)
    if status_code == 429:
        raise RateLimitError(message, retry_after=retry_after, **kwargs)
    if status_code >= 500:
        raise ServerError(message, **kwargs)
    raise APIError(message, **kwargs)


def _extract_message(body: Any) -> Optional[str]:
    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list) and detail:
            # FastAPI/Pydantic 422 validation errors
            first = detail[0]
            if isinstance(first, dict) and "msg" in first:
                loc = ".".join(str(p) for p in first.get("loc", []))
                return f"{loc}: {first['msg']}" if loc else first["msg"]
        if "error" in body:
            return str(body["error"])
    return None


def _parse_retry_after(response: httpx.Response) -> Optional[float]:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


class SyncTransport:
    """Synchronous HTTP transport with retries and connection pooling."""

    def __init__(self, cfg: ClientConfig, *, client: Optional[httpx.Client] = None) -> None:
        self.cfg = cfg
        self._client = client or httpx.Client(
            base_url=cfg.base_url,
            timeout=cfg.timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SyncTransport":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Any:
        headers = build_headers(self.cfg.api_key, self.cfg.user_agent or _USER_AGENT)
        last_exc: Optional[BaseException] = None

        for attempt in range(self.cfg.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    path,
                    json=json_body,
                    params=params,
                    headers=headers,
                )
            except httpx.TimeoutException as e:
                last_exc = FinVerifyTimeoutError(
                    f"Request to {path} timed out after {self.cfg.timeout}s"
                )
                last_exc.__cause__ = e
            except httpx.ConnectError as e:
                last_exc = FinVerifyConnectionError(
                    f"Cannot connect to FinVerify API at {self.cfg.base_url}: {e}"
                )
                last_exc.__cause__ = e
            except httpx.HTTPError as e:
                last_exc = APIConnectionError(f"Transport error calling {path}: {e}")
                last_exc.__cause__ = e
            else:
                if response.status_code < 400:
                    return _parse_body(response)

                body = _parse_body(response)
                request_id = response.headers.get("X-Request-Id")
                retry_after = _parse_retry_after(response)
                if not is_retryable_status(response.status_code) or attempt == self.cfg.max_retries:
                    _raise_for_error_status(
                        response.status_code, body, request_id=request_id, retry_after=retry_after
                    )
                logger.debug(
                    "Retryable HTTP %s from %s (attempt %d/%d)",
                    response.status_code, path, attempt + 1, self.cfg.max_retries,
                )
                last_exc = None
                sleep_for = compute_backoff(
                    attempt,
                    base=self.cfg.backoff_base,
                    maximum=self.cfg.backoff_max,
                    retry_after=retry_after,
                )
                time.sleep(sleep_for)
                continue

            if attempt == self.cfg.max_retries:
                raise last_exc
            sleep_for = compute_backoff(attempt, base=self.cfg.backoff_base, maximum=self.cfg.backoff_max)
            time.sleep(sleep_for)

        if last_exc is not None:  # pragma: no cover - defensive
            raise last_exc
        raise APIConnectionError(f"Request to {path} failed with no response")  # pragma: no cover


class AsyncTransport:
    """Async HTTP transport with retries and connection pooling."""

    def __init__(self, cfg: ClientConfig, *, client: Optional[httpx.AsyncClient] = None) -> None:
        self.cfg = cfg
        self._client = client or httpx.AsyncClient(
            base_url=cfg.base_url,
            timeout=cfg.timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncTransport":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Any:
        import asyncio

        headers = build_headers(self.cfg.api_key, self.cfg.user_agent or _USER_AGENT)
        last_exc: Optional[BaseException] = None

        for attempt in range(self.cfg.max_retries + 1):
            try:
                response = await self._client.request(
                    method,
                    path,
                    json=json_body,
                    params=params,
                    headers=headers,
                )
            except httpx.TimeoutException as e:
                last_exc = FinVerifyTimeoutError(
                    f"Request to {path} timed out after {self.cfg.timeout}s"
                )
                last_exc.__cause__ = e
            except httpx.ConnectError as e:
                last_exc = FinVerifyConnectionError(
                    f"Cannot connect to FinVerify API at {self.cfg.base_url}: {e}"
                )
                last_exc.__cause__ = e
            except httpx.HTTPError as e:
                last_exc = APIConnectionError(f"Transport error calling {path}: {e}")
                last_exc.__cause__ = e
            else:
                if response.status_code < 400:
                    return _parse_body(response)

                body = _parse_body(response)
                request_id = response.headers.get("X-Request-Id")
                retry_after = _parse_retry_after(response)
                if not is_retryable_status(response.status_code) or attempt == self.cfg.max_retries:
                    _raise_for_error_status(
                        response.status_code, body, request_id=request_id, retry_after=retry_after
                    )
                logger.debug(
                    "Retryable HTTP %s from %s (attempt %d/%d)",
                    response.status_code, path, attempt + 1, self.cfg.max_retries,
                )
                last_exc = None
                sleep_for = compute_backoff(
                    attempt,
                    base=self.cfg.backoff_base,
                    maximum=self.cfg.backoff_max,
                    retry_after=retry_after,
                )
                await asyncio.sleep(sleep_for)
                continue

            if attempt == self.cfg.max_retries:
                raise last_exc
            sleep_for = compute_backoff(attempt, base=self.cfg.backoff_base, maximum=self.cfg.backoff_max)
            await asyncio.sleep(sleep_for)

        if last_exc is not None:  # pragma: no cover - defensive
            raise last_exc
        raise APIConnectionError(f"Request to {path} failed with no response")  # pragma: no cover


__all__ = ["SyncTransport", "AsyncTransport"]
