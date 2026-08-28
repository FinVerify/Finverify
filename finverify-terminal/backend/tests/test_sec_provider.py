from core.financial.document import FinancialPeriod
from core.models import Claim, Entity, Metric
from providers.sec import SECProvider

def test_can_handle_claim_with_ticker():
    claim = Claim(
        question="What is Microsoft's revenue?",
        entity=Entity(
            name="Microsoft Corporation",
            ticker="MSFT",
        ),
    )

    assert SECProvider().can_handle(claim) is True

def test_can_handle_claim_without_entity():
    claim = Claim(
        question="What is the revenue?"
    )

    assert SECProvider().can_handle(claim) is False

def test_can_handle_claim_with_cik():
    claim = Claim(
        question="What is the revenue?",
        entity=Entity(
            name="Microsoft Corporation",
            cik="0000789019",
        ),
    )

    assert SECProvider().can_handle(claim) is True

def test_can_handle_claim_with_entity_but_no_identifier():
    claim = Claim(
        question="What is the revenue?",
        entity=Entity(
            name="Microsoft Corporation",
        ),
    )

    assert SECProvider().can_handle(claim) is False

def test_retrieve_returns_empty_when_claim_has_no_ticker():
    claim = Claim(
        question="What is the revenue?",
        entity=Entity(name="Microsoft Corporation"),
    )

    assert SECProvider().retrieve(claim) == []

def test_retrieve_uses_cached_evidence_when_metric_and_period_are_missing(monkeypatch):
    claim = Claim(
        question="What is the revenue?",
        entity=Entity(
            name="Microsoft Corporation",
            ticker="MSFT",
        ),
    )

    monkeypatch.setattr(
        "ingestion.db.get_fundamentals",
        lambda ticker: [
            {
                "metric_name": "revenue",
                "verified_value": 100.0,
                "period": "FY2025",
                "source_url": "https://example.com",
            }
        ],
    )

    evidence = SECProvider().retrieve(claim)

    assert len(evidence) == 1
    assert evidence[0].value == 100.0
    assert evidence[0].period == "FY2025"
    assert evidence[0].entity == "MSFT"

def test_retrieve_refreshes_from_sec_when_cache_has_no_matching_period(monkeypatch):
    claim = Claim(
        question="What was Apple's revenue in Q3 FY2026?",
        entity=Entity(
            name="Apple",
            ticker="AAPL",
            cik="0000320193",
        ),
        metric=Metric(
            name="revenue",
            canonical_name="revenue",
        ),
        period="Q3 FY2026",
        period_struct=FinancialPeriod(
            kind="quarterly",
            fiscal_year=2026,
            fiscal_quarter=3,
        ),
    )

    monkeypatch.setattr(
        "ingestion.db.get_fundamentals",
        lambda ticker: [
            {
                "ticker": "AAPL",
                "metric_name": "revenue",
                "verified_value": 416_161_000_000,
                "period": "FY2025",
                "source_url": "old",
            }
        ],
    )

    monkeypatch.setattr(
        "ingestion.sec_edgar.fetch_company_facts",
        lambda ticker: {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {
                                    "start": "2026-04-01",
                                    "end": "2026-06-30",
                                    "val": 94_040_000_000,
                                    "accn": "0000320193-26-000013",
                                    "fy": 2026,
                                    "fp": "Q3",
                                    "form": "10-Q",
                                    "filed": "2026-07-30",
                                }
                            ]
                        }
                    }
                }
            }
        },
    )

    evidence = SECProvider().retrieve(claim)

    assert len(evidence) == 1
    assert evidence[0].value == 94_040_000_000
    assert evidence[0].period == "Q3 FY2026"
    assert evidence[0].entity == "AAPL"
    assert evidence[0].source.kind == "primary_filing"

def test_retrieve_uses_matching_cached_evidence(monkeypatch):
    claim = Claim(
        question="What was Apple's revenue in Q3 FY2026?",
        entity=Entity(name="Apple", ticker="AAPL"),
        metric=Metric(name="revenue", canonical_name="revenue"),
        period="Q3 FY2026",
        period_struct=FinancialPeriod(
            kind="quarterly",
            fiscal_year=2026,
            fiscal_quarter=3,
        ),
    )

    monkeypatch.setattr(
        "ingestion.db.get_fundamentals",
        lambda ticker: [
            {
                "ticker": "AAPL",
                "metric_name": "revenue",
                "verified_value": 94_040_000_000,
                "period": "Q3 FY2026",
                "source_url": "cached",
            }
        ],
    )

    evidence = SECProvider().retrieve(claim)

    assert len(evidence) == 1
    assert evidence[0].value == 94_040_000_000
    assert evidence[0].period == "Q3 FY2026"
    assert evidence[0].entity == "AAPL"

def test_retrieve_returns_empty_when_sec_refresh_fails(monkeypatch):
    claim = Claim(
        question="What was Apple's revenue in Q3 FY2026?",
        entity=Entity(name="Apple", ticker="AAPL"),
        metric=Metric(name="revenue", canonical_name="revenue"),
        period="Q3 FY2026",
        period_struct=FinancialPeriod(
            kind="quarterly",
            fiscal_year=2026,
            fiscal_quarter=3,
        ),
    )

    monkeypatch.setattr(
        "ingestion.db.get_fundamentals",
        lambda ticker: [],
    )

    monkeypatch.setattr(
        "ingestion.sec_edgar.fetch_company_facts",
        lambda ticker: None,
    )

    assert SECProvider().retrieve(claim) == []
