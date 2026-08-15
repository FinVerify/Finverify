"""Phase 3C regression tests for live SEC evidence retrieval."""

from datetime import date

from core.models import Claim, Entity, Metric
from core.financial.document import FinancialPeriod
from ingestion.sec_edgar import extract_xbrl_metrics
from providers.sec import SECProvider


def _facts_with_quarterly_revenue():
    return {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "start": "2026-01-01",
                                "end": "2026-06-30",
                                "val": 180_000_000_000,
                                "accn": "0000320193-26-000013",
                                "fy": 2026, "fp": "Q3", "form": "10-Q",
                                "filed": "2026-07-30",
                            },
                            {
                                "start": "2026-04-01",
                                "end": "2026-06-30",
                                "val": 94_040_000_000,
                                "accn": "0000320193-26-000013",
                                "fy": 2026, "fp": "Q3", "form": "10-Q",
                                "filed": "2026-07-30",
                            },
                        ]
                    }
                }
            }
        }
    }


def test_quarterly_extractor_prefers_three_month_value():
    period = FinancialPeriod(kind="quarterly", fiscal_year=2026, fiscal_quarter=3)
    rows = extract_xbrl_metrics(
        _facts_with_quarterly_revenue(),
        "AAPL",
        target_metric="revenue",
        target_period=period,
    )
    assert len(rows) == 1
    assert rows[0]["raw_value"] == 94_040_000_000
    assert rows[0]["period"] == "Q3 FY2026"


def test_sec_provider_refreshes_when_cache_has_no_compatible_period(monkeypatch):
    claim = Claim(
        question="What was Apple revenue in Q3 FY2026?",
        raw_value=94_040_000_000,
        entity=Entity(name="apple", ticker="AAPL", cik="0000320193"),
        metric=Metric(name="revenue", canonical_name="revenue"),
        period="Q3 FY2026",
        period_struct=FinancialPeriod(kind="quarterly", fiscal_year=2026, fiscal_quarter=3),
    )

    monkeypatch.setattr(
        "ingestion.db.get_fundamentals",
        lambda ticker: [{
            "ticker": "AAPL", "metric_name": "revenue", "verified_value": 416_161_000_000,
            "period": "FY2025", "source_url": "old",
        }],
    )
    monkeypatch.setattr(
        "ingestion.sec_edgar.fetch_company_facts",
        lambda ticker: _facts_with_quarterly_revenue(),
    )

    evidence = SECProvider().retrieve(claim)
    assert len(evidence) == 1
    assert evidence[0].value == 94_040_000_000
    assert evidence[0].period == "Q3 FY2026"
    assert evidence[0].entity == "AAPL"
    assert evidence[0].source.kind == "primary_filing"


def test_sec_provider_does_not_use_stale_period_as_current_evidence(monkeypatch):
    claim = Claim(
        question="What was Apple revenue in Q3 FY2026?",
        raw_value=94_040_000_000,
        entity=Entity(name="apple", ticker="AAPL", cik="0000320193"),
        metric=Metric(name="revenue", canonical_name="revenue"),
        period="Q3 FY2026",
        period_struct=FinancialPeriod(kind="quarterly", fiscal_year=2026, fiscal_quarter=3),
    )
    monkeypatch.setattr(
        "ingestion.db.get_fundamentals",
        lambda ticker: [{
            "ticker": "AAPL", "metric_name": "revenue", "verified_value": 416_161_000_000,
            "period": "FY2025", "source_url": "old",
        }],
    )
    monkeypatch.setattr("ingestion.sec_edgar.fetch_company_facts", lambda ticker: None)

    assert SECProvider().retrieve(claim) == []
