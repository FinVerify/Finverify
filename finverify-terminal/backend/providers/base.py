"""Provider interface and registry."""

import logging
from typing import Protocol

from core.models import Claim, Evidence

logger = logging.getLogger(__name__)


class Provider(Protocol):
    name: str

    def can_handle(self, claim: Claim) -> bool: ...
    def retrieve(self, claim: Claim) -> list[Evidence]: ...


class ProviderRegistry:
    def __init__(self, providers: list[Provider] | None = None):
        self._providers: list[Provider] = providers or []

    def register(self, provider: Provider) -> None:
        if provider not in self._providers:
            self._providers.append(provider)

    def retrieve(self, claim: Claim) -> list[Evidence]:
        for provider in self._providers:
            try:
                if provider.can_handle(claim):
                    return provider.retrieve(claim)
            except Exception as exc:
                logger.warning("Provider %s failed for claim %r: %s", provider.name, claim.question, exc)
        return []
