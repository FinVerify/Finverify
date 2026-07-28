"""
finverify.auth — Request authentication headers
=================================================
The FinVerify API's ``/v1/verify`` endpoint accepts an optional
``X-FinVerify-Key`` header for request tracking (it is not currently
enforced server-side, but the header contract is stable and future
versions of the API are expected to authenticate against it).
"""

from __future__ import annotations

from typing import Optional


def build_headers(api_key: Optional[str], user_agent: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": user_agent,
    }
    if api_key:
        headers["X-FinVerify-Key"] = api_key
    return headers


__all__ = ["build_headers"]
