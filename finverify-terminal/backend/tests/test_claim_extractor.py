"""Tests for core.financial.claim_extractor.extract_claims."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.financial.claim_extractor import extract_claims
from core.financial.concepts import ConceptRegistry
from core.financial.mapper import StatementMapper
from core.models import Claim


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "concepts.yaml"


def _annual_entry(start: str, end: str, filed: str, value: float, accn: str, fy: int) -> dict:
    return {
        "start": start,
        "end": end,
        "val": value,
        "accn": accn,
        "fy": fy,
        "fp": "FY",
        "form": "10-K",
        "filed": filed,
    }


def make_company_facts() -> dict:
    """Two fiscal years of AAPL-like facts across two statements/concepts."""
    return {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 391_035_000_000.0, "0000320193-24-000123", 2024),
                            _annual_entry("2022-10-01", "2023-09-30", "2023-11-02", 383_285_000_000.0, "0000320193-23-000106", 2023),
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 93_736_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 118_658_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 118_254_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
            }
        },
    }


def make_document(max_periods: int = 1):
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)
    document = mapper.map_xbrl_to_document(
        make_company_facts(),
        {
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "cik": "0000320193",
            "filing_type": "10-K",
            "filing_date": "2024-11-01",
            "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/",
        },
        max_periods=max_periods,
    )
    return document


def test_extract_claims_returns_one_claim_per_statement_item():
    document = make_document(max_periods=1)

    claims = extract_claims(document)

    total_items = sum(len(statement.items) for statement in document.statements.values())
    assert len(claims) == total_items
    assert all(isinstance(claim, Claim) for claim in claims)


def test_extract_claims_uses_canonical_concept_names_not_sec_names():
    document = make_document(max_periods=1)

    claims = extract_claims(document)
    metric_names = {claim.metric.name for claim in claims}

    # Canonical names from config/concepts.yaml, never raw XBRL/SEC-style names.
    assert "Revenue" in metric_names
    assert "NetIncome" in metric_names
    assert "OperatingIncome" in metric_names
    assert "OperatingCashFlow" in metric_names
    assert "Revenues" not in metric_names
    assert "net_income" not in metric_names
    assert "NetIncomeLoss" not in metric_names


def test_extract_claims_populates_entity_from_document():
    document = make_document(max_periods=1)

    claims = extract_claims(document)

    assert all(claim.entity is not None for claim in claims)
    assert all(claim.entity.name == "Apple Inc." for claim in claims)
    assert all(claim.entity.ticker == "AAPL" for claim in claims)
    assert all(claim.entity.cik == "0000320193" for claim in claims)


def test_extract_claims_sets_raw_value_and_metric_unit():
    document = make_document(max_periods=1)

    claims = extract_claims(document)
    revenue_claim = next(claim for claim in claims if claim.metric.name == "Revenue")

    assert revenue_claim.raw_value == pytest.approx(391_035_000_000.0)
    assert revenue_claim.metric.unit == "USD"


def test_extract_claims_sets_period_string():
    document = make_document(max_periods=1)

    claims = extract_claims(document)

    assert all(claim.period is not None for claim in claims)
    assert all(claim.period == "2024" for claim in claims)


def test_extract_claims_multi_period_produces_distinct_periods():
    document = make_document(max_periods=2)

    claims = extract_claims(document)
    revenue_claims = [claim for claim in claims if claim.metric.name == "Revenue"]

    assert len(revenue_claims) == 2
    periods = {claim.period for claim in revenue_claims}
    assert periods == {"2024", "2023"}
    values_by_period = {claim.period: claim.raw_value for claim in revenue_claims}
    assert values_by_period["2024"] == pytest.approx(391_035_000_000.0)
    assert values_by_period["2023"] == pytest.approx(383_285_000_000.0)


def test_extract_claims_metadata_contains_source_statement_filing_type_and_date():
    document = make_document(max_periods=1)

    claims = extract_claims(document)
    revenue_claim = next(claim for claim in claims if claim.metric.name == "Revenue")

    assert revenue_claim.metadata["statement"] == "IncomeStatement"
    assert revenue_claim.metadata["filing_type"] == "10-K"
    assert revenue_claim.metadata["filing_date"] == "2024-11-01"
    assert "source" in revenue_claim.metadata
    assert "10-K" in revenue_claim.metadata["source"]
    assert revenue_claim.metadata["xbrl_tag"] == "us-gaap:Revenues"
    assert revenue_claim.metadata["source_url"] == (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/"
    )


def test_extract_claims_question_is_human_readable():
    document = make_document(max_periods=1)

    claims = extract_claims(document)
    revenue_claim = next(claim for claim in claims if claim.metric.name == "Revenue")

    assert revenue_claim.question == "What is Revenue for Apple Inc. (FY2024)?"


def test_extract_claims_empty_document_returns_empty_list():
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)
    document = mapper.map_xbrl_to_document({"facts": {"us-gaap": {}}}, {"company_name": "Empty Co"})

    claims = extract_claims(document)

    assert claims == []
