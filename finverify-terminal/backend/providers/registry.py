"""Default provider registry."""

from .base import ProviderRegistry
from .sec import SECProvider


def default_registry() -> ProviderRegistry:
    return ProviderRegistry([SECProvider()])
