"""Provider interface and registry."""

import logging
from typing import Any, Protocol

from core.models import Claim, Evidence, EvidenceTier

logger = logging.getLogger(__name__)


def resolve_provider_tier(
    provider_name: str | None,
    provider_metadata: dict[str, Any] | None = None,
) -> EvidenceTier:
    """Resolve provider tier from structured metadata first, then name fallback."""
    metadata = provider_metadata or {}
    tier = metadata.get("tier")
    if isinstance(tier, str):
        normalized_tier = tier.strip().lower()
        for candidate in EvidenceTier:
            if candidate.value == normalized_tier:
                return candidate

    normalized_name = (provider_name or "").strip().lower()
    if "sec" in normalized_name:
        return EvidenceTier.PRIMARY
    if any(token in normalized_name for token in ("fred", "dbnomics")):
        return EvidenceTier.SECONDARY
    if "model" in normalized_name:
        return EvidenceTier.MODEL
    return EvidenceTier.USER


class Provider(Protocol):
    name: str
    metadata: dict[str, Any]

    def can_handle(self, claim: Claim) -> bool: ...
    def retrieve(self, claim: Claim) -> list[Evidence]: ...


class ProviderRegistry:
    def __init__(self, providers: list[Provider] | None = None):
        self._providers: list[Provider] = providers or []

    def register(self, provider: Provider) -> None:
        if provider not in self._providers:
            self._providers.append(provider)

    def resolve(self, claim: Claim) -> Provider | None:
        for provider in self._providers:
            try:
                if provider.can_handle(claim):
                    return provider
            except Exception as exc:
                logger.warning("Provider %s failed for claim %r: %s", provider.name, claim.question, exc)
        return None

    def get_provider_metadata(self, provider_name: str | None) -> dict[str, Any]:
        normalized_name = (provider_name or "").strip().lower()
        for provider in self._providers:
            provider_aliases = {
                provider.name.strip().lower(),
                getattr(provider, "name", "").strip().lower().replace("_", " "),
            }
            if normalized_name in provider_aliases:
                return dict(getattr(provider, "metadata", {}) or {})
        return {}

    def resolve_evidence_tier(
        self,
        provider_name: str | None,
        provider_metadata: dict[str, Any] | None = None,
    ) -> EvidenceTier:
        metadata = dict(self.get_provider_metadata(provider_name))
        if provider_metadata:
            metadata.update(provider_metadata)
        return resolve_provider_tier(provider_name, metadata)

    def retrieve(self, claim: Claim) -> list[Evidence]:
        provider = self.resolve(claim)
        if provider is not None:
            try:
                return provider.retrieve(claim)
            except Exception as exc:
                logger.warning("Provider %s failed for claim %r: %s", provider.name, claim.question, exc)
        return []
