"""finverify.resources.meta — GET /health, GET /sample-queries"""

from __future__ import annotations

from ..models import HealthStatus, SampleQuery


def build_health_request() -> tuple[str, str, None, None]:
    return "GET", "/health", None, None


def parse_health_response(data: dict) -> HealthStatus:
    return HealthStatus.from_dict(data)


def build_sample_queries_request() -> tuple[str, str, None, None]:
    return "GET", "/sample-queries", None, None


def parse_sample_queries_response(data: list) -> list[SampleQuery]:
    return [SampleQuery.from_dict(item) for item in data]


__all__ = [
    "build_health_request",
    "parse_health_response",
    "build_sample_queries_request",
    "parse_sample_queries_response",
]
