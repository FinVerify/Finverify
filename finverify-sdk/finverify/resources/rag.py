"""finverify.resources.rag — vector-search endpoints.

These return the backend's raw JSON as a ``dict`` rather than a typed
model: the RAG result shape is intentionally open-ended (arbitrary
metadata per matched chunk) and wrapping it would only strip
information without adding safety, unlike the fixed-shape ``/v1/verify``
response.
"""

from __future__ import annotations

from ..validators import require_str


def build_rag_stats_request() -> tuple[str, str, None, None]:
    return "GET", "/v1/rag/stats", None, None


def build_rag_query_request(question: str, top_k: int = 5) -> tuple[str, str, dict, None]:
    question = require_str(question, "question")
    body = {"question": question, "top_k": min(top_k, 20)}
    return "POST", "/v1/rag/query", body, None


def build_rag_seed_request() -> tuple[str, str, None, None]:
    return "POST", "/v1/rag/seed", None, None


__all__ = ["build_rag_stats_request", "build_rag_query_request", "build_rag_seed_request"]
