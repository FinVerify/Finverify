from finverify.models import (
    Constraint,
    FundamentalsResult,
    HealthStatus,
    HistoryEntry,
    VerifyResult,
)


def test_verify_result_from_dict_v1_shape():
    r = VerifyResult.from_dict(
        {
            "question": "q",
            "raw_value": 1.0,
            "verified_value": 2.0,
            "trust_score": "HIGH",
            "trust_color": "#00ff88",
            "delta_pct": 100.0,
        }
    )
    assert r.was_corrected is False
    assert r.is_high_trust is True


def test_verify_result_from_dict_legacy_verify_shape():
    # /verify (no LLM call) uses raw_number/verified_number, not raw_value
    r = VerifyResult.from_dict(
        {
            "question": "q",
            "raw_number": 1.0,
            "verified_number": 2.0,
            "trust_score": "MEDIUM",
            "trust_color": "#fbbf24",
            "correction_applied": "scale_mul100",
        }
    )
    assert r.raw_value == 1.0
    assert r.verified_value == 2.0
    assert r.was_corrected is True


def test_health_status_is_healthy():
    h = HealthStatus.from_dict({"status": "ok", "dvl": "online", "llm": "offline", "model": "x"})
    assert h.is_healthy is True
    h2 = HealthStatus.from_dict({"status": "degraded", "dvl": "online", "llm": "offline", "model": "x"})
    assert h2.is_healthy is False


def test_fundamentals_result_defaults():
    f = FundamentalsResult.from_dict({"ticker": "MSFT"})
    assert f.metrics == {}
    assert f.metrics_count == 0


def test_history_entry_optional_fields():
    e = HistoryEntry.from_dict({"user_id": "u1", "question": "q"})
    assert e.id is None
    assert e.trust == "HIGH"
    assert e.correction_log == []


def test_constraint_from_dict():
    c = Constraint.from_dict(
        {
            "id": "gross_margin",
            "name": "Gross Margin Check",
            "description": "d",
            "requires": ["revenue", "cogs"],
            "tolerance_pct": 5.0,
            "severity": "HARD",
        }
    )
    assert c.severity == "HARD"
    assert "revenue" in c.requires
