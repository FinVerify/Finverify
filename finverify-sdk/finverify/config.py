"""
finverify.config — Configuration resolution
=============================================
Centralizes how the SDK figures out the base URL, API key, timeout,
and retry policy. Precedence (highest to lowest):

    1. Explicit constructor argument (``FinVerify(api_key="...")``)
    2. Environment variable (``FINVERIFY_API_KEY``)
    3. Library default
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

#: Production API — the FinVerify DVL service on HuggingFace Spaces.
DEFAULT_BASE_URL = "https://aadi2026-finverify-api.hf.space"
DEFAULT_TIMEOUT = 15.0
DEFAULT_MAX_RETRIES = 2
#: Backoff schedule (seconds) applied between retryable failures.
DEFAULT_BACKOFF_BASE = 0.5
DEFAULT_BACKOFF_MAX = 8.0

ENV_API_KEY = "FINVERIFY_API_KEY"
ENV_BASE_URL = "FINVERIFY_BASE_URL"
ENV_TIMEOUT = "FINVERIFY_TIMEOUT"
ENV_MAX_RETRIES = "FINVERIFY_MAX_RETRIES"


@dataclass(frozen=True)
class ClientConfig:
    """Resolved configuration for a client instance."""

    base_url: str
    api_key: Optional[str]
    timeout: float
    max_retries: int
    backoff_base: float = DEFAULT_BACKOFF_BASE
    backoff_max: float = DEFAULT_BACKOFF_MAX
    user_agent: str = "finverify-python"

    @classmethod
    def resolve(
        cls,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> "ClientConfig":
        resolved_base_url = (
            base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL
        ).rstrip("/")
        resolved_api_key = api_key or os.environ.get(ENV_API_KEY)

        resolved_timeout = timeout
        if resolved_timeout is None:
            env_timeout = os.environ.get(ENV_TIMEOUT)
            resolved_timeout = float(env_timeout) if env_timeout else DEFAULT_TIMEOUT

        resolved_max_retries = max_retries
        if resolved_max_retries is None:
            env_retries = os.environ.get(ENV_MAX_RETRIES)
            resolved_max_retries = int(env_retries) if env_retries else DEFAULT_MAX_RETRIES

        return cls(
            base_url=resolved_base_url,
            api_key=resolved_api_key,
            timeout=resolved_timeout,
            max_retries=resolved_max_retries,
        )


__all__ = ["ClientConfig", "DEFAULT_BASE_URL", "DEFAULT_TIMEOUT", "DEFAULT_MAX_RETRIES"]
