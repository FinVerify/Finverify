"""finverify.resources.history — Supabase-backed query history."""

from __future__ import annotations

from typing import Optional

from ..models import HistoryEntry
from ..validators import require_str


def build_get_history_request(
    user_id: str,
    limit: int = 20,
    trust: Optional[str] = None,
) -> tuple[str, str, None, dict]:
    user_id = require_str(user_id, "user_id")
    params: dict = {"limit": min(limit, 100)}
    if trust:
        params["trust"] = trust
    return "GET", f"/v1/history/{user_id}", None, params


def parse_get_history_response(data: dict) -> list[HistoryEntry]:
    return [HistoryEntry.from_dict(e) for e in data.get("entries", [])]


def build_save_history_request(
    user_id: str,
    question: str,
    raw_value: Optional[float] = None,
    verified_value: Optional[float] = None,
    trust: str = "HIGH",
    display_value: str = "",
    correction_log: Optional[list] = None,
) -> tuple[str, str, dict, None]:
    user_id = require_str(user_id, "user_id")
    body = {
        "user_id": user_id,
        "question": question,
        "raw_value": raw_value,
        "verified_value": verified_value,
        "trust": trust,
        "display_value": display_value,
        "correction_log": correction_log or [],
    }
    return "POST", "/v1/history", body, None


def build_delete_history_request(user_id: str) -> tuple[str, str, None, None]:
    user_id = require_str(user_id, "user_id")
    return "DELETE", f"/v1/history/{user_id}", None, None


__all__ = [
    "build_get_history_request",
    "parse_get_history_response",
    "build_save_history_request",
    "build_delete_history_request",
]
