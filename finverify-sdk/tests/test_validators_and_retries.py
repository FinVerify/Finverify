import pytest

from finverify.exceptions import RateLimitError, ValidationError
from finverify.retries import compute_backoff, is_retryable_exception, is_retryable_status
from finverify.validators import (
    require_dict_of_numbers,
    require_number,
    require_str,
    require_ticker,
)


def test_require_str_rejects_empty():
    with pytest.raises(ValidationError):
        require_str("   ", "question")


def test_require_str_accepts_value():
    assert require_str("hi", "question") == "hi"


def test_require_number_rejects_non_number():
    with pytest.raises(ValidationError):
        require_number("not-a-number", "raw_value")


def test_require_number_rejects_bool():
    # bools are ints in Python; the SDK should not silently accept True/False
    with pytest.raises(ValidationError):
        require_number(True, "raw_value")


def test_require_ticker_normalizes_case():
    assert require_ticker("aapl") == "AAPL"


def test_require_dict_of_numbers_coerces_and_skips_invalid():
    with pytest.raises(ValidationError):
        require_dict_of_numbers({"revenue": "not-numeric"}, "values")
    cleaned = require_dict_of_numbers({"revenue": "100"}, "values")
    assert cleaned["revenue"] == 100.0


def test_require_dict_of_numbers_rejects_empty():
    with pytest.raises(ValidationError):
        require_dict_of_numbers({}, "values")


def test_is_retryable_status():
    assert is_retryable_status(429) is True
    assert is_retryable_status(500) is True
    assert is_retryable_status(503) is True
    assert is_retryable_status(404) is False
    assert is_retryable_status(400) is False


def test_is_retryable_exception_respects_class_flag():
    assert is_retryable_exception(RateLimitError("x")) is True
    assert is_retryable_exception(ValidationError("x")) is False


def test_compute_backoff_honors_retry_after():
    assert compute_backoff(0, base=0.5, maximum=8.0, retry_after=3.0) == 3.0


def test_compute_backoff_caps_at_maximum():
    # even with a huge attempt count, jittered backoff never exceeds `maximum`
    for attempt in range(10):
        assert compute_backoff(attempt, base=0.5, maximum=8.0) <= 8.0
