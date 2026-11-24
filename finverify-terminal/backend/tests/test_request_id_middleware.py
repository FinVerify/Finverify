import asyncio
import logging
import uuid

import httpx
import pytest

from app.main import app
from app.middleware import get_request_id


@pytest.mark.asyncio
async def test_generates_request_id_when_header_missing():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    req_id = resp.headers.get("X-Request-ID")
    assert req_id is not None
    parsed = uuid.UUID(req_id, version=4)
    assert str(parsed) == req_id


@pytest.mark.asyncio
async def test_propagates_incoming_request_id_and_binds_to_logs(caplog):
    custom_id = "req-trace-abc-999"
    transport = httpx.ASGITransport(app=app)
    with caplog.at_level(logging.INFO):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/verify",
                json={"question": "What was revenue?", "raw_number": 100.0},
                headers={"X-Request-ID": custom_id},
            )

    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == custom_id
    assert any(getattr(rec, "request_id", None) == custom_id for rec in caplog.records)
    assert get_request_id() == "-"


@pytest.mark.asyncio
async def test_concurrent_requests_have_distinct_non_colliding_request_ids(caplog):
    test_logger = logging.getLogger("test.concurrency")
    captured: dict[str, list[str]] = {"req_a": [], "req_b": []}

    @app.get("/_test/concurrent-trace")
    async def _concurrent_probe(tag: str):
        first_id = get_request_id()
        test_logger.info("start %s", tag)
        await asyncio.sleep(0.03)
        second_id = get_request_id()
        test_logger.info("end %s", tag)
        captured[tag] = [first_id, second_id]
        return {"tag": tag, "request_id": second_id}

    try:
        transport = httpx.ASGITransport(app=app)
        with caplog.at_level(logging.INFO, logger="test.concurrency"):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                resp_a, resp_b = await asyncio.gather(
                    client.get("/_test/concurrent-trace", params={"tag": "req_a"}),
                    client.get("/_test/concurrent-trace", params={"tag": "req_b"}),
                )

        id_a = resp_a.headers["X-Request-ID"]
        id_b = resp_b.headers["X-Request-ID"]

        assert id_a != id_b
        assert captured["req_a"] == [id_a, id_a]
        assert captured["req_b"] == [id_b, id_b]

        logs_a = [r.request_id for r in caplog.records if "req_a" in r.getMessage()]
        logs_b = [r.request_id for r in caplog.records if "req_b" in r.getMessage()]
        assert logs_a == [id_a, id_a]
        assert logs_b == [id_b, id_b]
    finally:
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", None) != "/_test/concurrent-trace"
        ]