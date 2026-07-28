"""finverify.resources.verify — POST /v1/verify"""

from __future__ import annotations

from typing import Optional

from ..models import VerifyResult
from ..validators import require_number, require_str


def build_verify_request(
    question: str,
    raw_value: float,
    model_source: Optional[str] = None,
) -> tuple[str, str, dict, None]:
    question = require_str(question, "question")
    raw_value = require_number(raw_value, "raw_value")

    body: dict = {"question": question, "raw_value": raw_value}
    if model_source:
        body["model_source"] = model_source
    return "POST", "/v1/verify", body, None


def parse_verify_response(data: dict, *, request_id: Optional[str] = None) -> VerifyResult:
    return VerifyResult.from_dict(data, request_id=request_id)


__all__ = ["build_verify_request", "parse_verify_response"]
