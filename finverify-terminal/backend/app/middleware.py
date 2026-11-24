"""
Request-ID propagation and per-request logging context middleware.

Assigns a unique correlation ID (from incoming X-Request-ID header or a fresh
UUID4) to every HTTP request via contextvars so concurrent async handlers and
downstream calls (/query -> DVL -> market/RAG) emit traceable logs without
colliding.
"""

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

logger = logging.getLogger("finverify.request")

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the active correlation ID for the current async execution context."""
    return request_id_ctx.get()


class RequestIDLogFilter(logging.Filter):
    """Logging filter that attaches `request_id` to every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def install_request_id_logging() -> None:
    """Attach RequestIDLogFilter to the root logger and all existing handlers.

    Idempotent: safe to call multiple times at startup or in tests.
    """
    root_logger = logging.getLogger()
    if not any(isinstance(f, RequestIDLogFilter) for f in root_logger.filters):
        root_logger.addFilter(RequestIDLogFilter())

    for handler in root_logger.handlers:
        if not any(isinstance(f, RequestIDLogFilter) for f in handler.filters):
            handler.addFilter(RequestIDLogFilter())

    # Ensure even newly created handlers/loggers get `request_id` on LogRecord
    old_factory = logging.getLogRecordFactory()
    if not getattr(old_factory, "_has_request_id", False):
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            if not hasattr(record, "request_id"):
                record.request_id = get_request_id()
            return record

        record_factory._has_request_id = True  # type: ignore[attr-defined]
        logging.setLogRecordFactory(record_factory)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generates or propagates X-Request-ID per request and echoes it in response headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_id = request.headers.get(REQUEST_ID_HEADER, "").strip()
        req_id = incoming_id or str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = req_id
            logger.info(
                "%s %s -> %d (%.1f ms)",
                request.method,
                request.url.path,
                response.status_code,
                (time.perf_counter() - start) * 1000,
            )
            return response
        finally:
            request_id_ctx.reset(token)