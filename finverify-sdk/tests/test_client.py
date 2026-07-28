import httpx
import pytest
import respx

from finverify import FinVerify
from finverify.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

BASE = "https://test.finverify.local"


@respx.mock
def test_verify_success():
    respx.post(f"{BASE}/v1/verify").mock(
        return_value=httpx.Response(
            200,
            json={
                "question": "profit margin",
                "raw_value": 0.2531,
                "verified_value": 25.31,
                "correction_applied": "scale_mul100",
                "trust_score": "MEDIUM",
                "trust_color": "#fbbf24",
                "delta_pct": 9902.7678,
                "dvl_version": "1.0.0",
                "timestamp": "2026-05-22T12:00:00+00:00",
            },
        )
    )
    with FinVerify(base_url=BASE) as client:
        result = client.verify(question="profit margin", raw_value=0.2531)

    assert result.verified_value == 25.31
    assert result.trust_score == "MEDIUM"
    assert result.was_corrected is True
    assert result.is_high_trust is False


@respx.mock
def test_verify_sends_model_source_only_when_given():
    route = respx.post(f"{BASE}/v1/verify").mock(
        return_value=httpx.Response(
            200,
            json={
                "question": "q",
                "raw_value": 1.0,
                "verified_value": 1.0,
                "trust_score": "HIGH",
                "trust_color": "#00ff88",
                "delta_pct": 0.0,
            },
        )
    )
    with FinVerify(base_url=BASE) as client:
        client.verify(question="q", raw_value=1.0)

    sent_body = route.calls[0].request.content
    assert b"model_source" not in sent_body


@respx.mock
def test_verify_validation_error_before_network_call():
    route = respx.post(f"{BASE}/v1/verify")
    with FinVerify(base_url=BASE) as client:
        with pytest.raises(ValidationError):
            client.verify(question="", raw_value=1.0)
    assert route.call_count == 0


@pytest.mark.parametrize(
    "status,exc_cls",
    [
        (401, AuthenticationError),
        (404, NotFoundError),
        (422, ValidationError),
        (500, ServerError),
    ],
)
@respx.mock
def test_verify_maps_status_codes_to_exceptions(status, exc_cls):
    respx.post(f"{BASE}/v1/verify").mock(
        return_value=httpx.Response(status, json={"detail": "boom"})
    )
    with FinVerify(base_url=BASE, max_retries=0) as client:
        with pytest.raises(exc_cls):
            client.verify(question="q", raw_value=1.0)


@respx.mock
def test_rate_limit_retries_then_succeeds():
    route = respx.post(f"{BASE}/v1/verify")
    route.side_effect = [
        httpx.Response(429, json={"detail": "slow down"}, headers={"Retry-After": "0"}),
        httpx.Response(
            200,
            json={
                "question": "q",
                "raw_value": 1.0,
                "verified_value": 1.0,
                "trust_score": "HIGH",
                "trust_color": "#00ff88",
                "delta_pct": 0.0,
            },
        ),
    ]
    with FinVerify(base_url=BASE, max_retries=2) as client:
        result = client.verify(question="q", raw_value=1.0)
    assert result.verified_value == 1.0
    assert route.call_count == 2


@respx.mock
def test_rate_limit_exhausts_retries_and_raises():
    respx.post(f"{BASE}/v1/verify").mock(
        return_value=httpx.Response(429, json={"detail": "slow down"})
    )
    with FinVerify(base_url=BASE, max_retries=1) as client:
        with pytest.raises(RateLimitError):
            client.verify(question="q", raw_value=1.0)


@respx.mock
def test_health():
    respx.get(f"{BASE}/health").mock(
        return_value=httpx.Response(
            200, json={"status": "ok", "dvl": "online", "llm": "online", "model": "x"}
        )
    )
    with FinVerify(base_url=BASE) as client:
        health = client.health()
    assert health.is_healthy is True


@respx.mock
def test_verify_batch_collects_results_and_errors():
    respx.post(f"{BASE}/v1/verify").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "question": "a",
                    "raw_value": 1.0,
                    "verified_value": 1.0,
                    "trust_score": "HIGH",
                    "trust_color": "#00ff88",
                    "delta_pct": 0.0,
                },
            ),
            httpx.Response(500, json={"detail": "fail"}),
        ]
    )
    with FinVerify(base_url=BASE, max_retries=0) as client:
        batch = client.verify_batch(
            [
                {"question": "a", "raw_value": 1.0},
                {"question": "b", "raw_value": 2.0},
            ]
        )
    assert len(batch) == 2
    assert len(batch.succeeded) == 1
    assert batch.failed_count == 1


@respx.mock
def test_fundamentals_get():
    respx.get(f"{BASE}/v1/fundamentals/AAPL").mock(
        return_value=httpx.Response(
            200,
            json={"ticker": "AAPL", "source": "sec_edgar", "metrics_count": 2, "metrics": {"revenue": 391}},
        )
    )
    with FinVerify(base_url=BASE) as client:
        result = client.fundamentals.get("aapl")
    assert result.ticker == "AAPL"
    assert result.metrics["revenue"] == 391


@respx.mock
def test_fcg_verify():
    respx.post(f"{BASE}/v1/fcg/verify").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "ok",
                "input_count": 2,
                "normalized_count": 2,
                "constraint_result": {"passed": True},
            },
        )
    )
    with FinVerify(base_url=BASE) as client:
        result = client.fcg.verify({"revenue": 100, "cogs": 40})
    assert result.constraint_result["passed"] is True
