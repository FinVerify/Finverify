from core.models import EvidenceTier
from providers.base import resolve_provider_tier

def test_sec_name_returns_primary_tier():
    result = resolve_provider_tier("sec_edgar")
    assert result == EvidenceTier.PRIMARY

def test_fred_name_returns_secondary_tier():
    result = resolve_provider_tier("fred_api")
    assert result == EvidenceTier.SECONDARY

def test_metadata_tier_overrides_name():
    result = resolve_provider_tier(
        "fred_api",
        {"tier": "primary"}
    )
    assert result == EvidenceTier.PRIMARY

def test_unknown_provider_defaults_to_user():
    result = resolve_provider_tier("unknown_provider")
    assert result == EvidenceTier.USER

def test_model_name_returns_model_tier():
    result = resolve_provider_tier("model_provider")

    assert result == EvidenceTier.MODEL

def test_valid_metadata_tier_id_used():
    result = resolve_provider_tier(
        "unknown_provider",
        {"tier":"secondary"},
    )

    assert result == EvidenceTier.SECONDARY

def test_invalid_metadata_falls_back_to_provider_name():
    result = resolve_provider_tier(
        "sec_edgar",
        {"tier":"invalid"},
    )

    assert result == EvidenceTier.PRIMARY

