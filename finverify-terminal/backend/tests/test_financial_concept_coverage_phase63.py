"""Phase 6.3 tests for SEC concept coverage expansion."""

from __future__ import annotations

import json
from pathlib import Path

from core.evidence import EvidenceRetriever
from core.financial.concepts import ConceptRegistry
from core.financial.constraints.models import ConstraintStatus
from core.financial.document import FinancialStatementItem
from core.financial.document_verifier import verify_document
from core.financial.mapper import StatementMapper


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


def make_phase63_company_facts() -> dict:
    return {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 391_035_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "CostOfGoodsAndServicesSold": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 210_352_000_000.0, "0000320193-24-000123", 2024),
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
                "Assets": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 364_980_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "Liabilities": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 308_030_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "LiabilitiesAndStockholdersEquity": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 364_980_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "StockholdersEquity": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 56_950_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "CashAndCashEquivalentsAtCarryingValue": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 29_943_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "EarningsPerShareBasic": {
                    "units": {
                        "USD/shares": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 6.15, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "EarningsPerShareDiluted": {
                    "units": {
                        "USD/shares": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 6.11, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "WeightedAverageNumberOfDilutedSharesOutstanding": {
                    "units": {
                        "shares": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 15_356_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
            }
        },
    }


def _items_by_concept(document) -> dict[str, FinancialStatementItem]:
    return {
        item.concept: item
        for statement in document.statements.values()
        for item in statement.items
    }


def test_existing_xbrl_tag_mappings_remain_stable():
    registry = ConceptRegistry(CONFIG_PATH)

    expected_mappings = {
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax": "Revenue",
        "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax": "Revenue",
        "us-gaap:Revenues": "Revenue",
        "us-gaap:CostOfGoodsSold": "CostOfGoodsSold",
        "us-gaap:CostOfGoodsAndServicesSold": "CostOfGoodsSold",
        "us-gaap:CostOfSales": "CostOfGoodsSold",
        "us-gaap:GrossProfit": "GrossProfit",
        "us-gaap:OperatingIncomeLoss": "OperatingIncome",
        "us-gaap:NetIncomeLoss": "NetIncome",
        "us-gaap:ProfitLoss": "NetIncome",
        "us-gaap:NetCashProvidedByUsedInOperatingActivities": "OperatingCashFlow",
    }

    for tag, concept in expected_mappings.items():
        assert registry.resolve_xbrl_tag(tag) == concept


def test_new_xbrl_tag_mappings_resolve_correctly():
    registry = ConceptRegistry(CONFIG_PATH)

    expected_mappings = {
        "us-gaap:Assets": "Assets",
        "us-gaap:Liabilities": "Liabilities",
        "us-gaap:LiabilitiesAndStockholdersEquity": "LiabilitiesAndStockholdersEquity",
        "us-gaap:StockholdersEquity": "StockholdersEquity",
        "us-gaap:CashAndCashEquivalentsAtCarryingValue": "CashAndCashEquivalents",
        "us-gaap:EarningsPerShareBasic": "EarningsPerShareBasic",
        "us-gaap:EarningsPerShareDiluted": "EarningsPerShareDiluted",
        "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding": "SharesOutstanding",
    }

    for tag, concept in expected_mappings.items():
        assert registry.resolve_xbrl_tag(tag) == concept


def test_registry_contains_fourteen_xbrl_backed_concepts():
    registry = ConceptRegistry(CONFIG_PATH)

    xbrl_backed_concepts = [name for name, spec in registry.concepts.items() if spec.get("xbrl_tags")]

    assert len(xbrl_backed_concepts) == 14


def test_statement_mapper_maps_new_concepts_with_expected_statements_and_units():
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)

    document = mapper.map_xbrl_to_document(
        make_phase63_company_facts(),
        {
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "cik": "0000320193",
            "filing_type": "10-K",
            "filing_date": "2024-11-01",
        },
        max_periods=1,
    )

    assert set(document.statements) == {"BalanceSheet", "IncomeStatement"}

    items = _items_by_concept(document)
    expected_specs = {
        "Assets": ("BalanceSheet", "USD", "currency", "us-gaap:Assets"),
        "Liabilities": ("BalanceSheet", "USD", "currency", "us-gaap:Liabilities"),
        "LiabilitiesAndStockholdersEquity": ("BalanceSheet", "USD", "currency", "us-gaap:LiabilitiesAndStockholdersEquity"),
        "StockholdersEquity": ("BalanceSheet", "USD", "currency", "us-gaap:StockholdersEquity"),
        "CashAndCashEquivalents": ("BalanceSheet", "USD", "currency", "us-gaap:CashAndCashEquivalentsAtCarryingValue"),
        "EarningsPerShareBasic": ("IncomeStatement", "USD/shares", "per_share", "us-gaap:EarningsPerShareBasic"),
        "EarningsPerShareDiluted": ("IncomeStatement", "USD/shares", "per_share", "us-gaap:EarningsPerShareDiluted"),
        "SharesOutstanding": ("IncomeStatement", "shares", "count", "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"),
    }

    for concept, (statement_name, unit, dimension, xbrl_tag) in expected_specs.items():
        assert concept in items
        assert items[concept].unit == unit
        assert items[concept].xbrl_tag == xbrl_tag
        assert concept in {item.concept for item in document.statements[statement_name].items}
        assert registry.get_concept(concept)["dimension"] == dimension


def test_balance_sheet_contains_assets_liabilities_and_equity_total():
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)

    document = mapper.map_xbrl_to_document(
        make_phase63_company_facts(),
        {
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "cik": "0000320193",
            "filing_type": "10-K",
            "filing_date": "2024-11-01",
        },
        max_periods=1,
    )

    balance_sheet = document.statements["BalanceSheet"]
    concepts = {item.concept for item in balance_sheet.items}

    assert {"Assets", "Liabilities", "LiabilitiesAndStockholdersEquity", "StockholdersEquity"}.issubset(concepts)


def test_real_concepts_yaml_has_no_duplicate_xbrl_tags():
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    owners: dict[str, str] = {}
    duplicates: list[tuple[str, str, str]] = []
    for concept_name, spec in payload["concepts"].items():
        for tag in spec.get("xbrl_tags", []):
            normalized_tag = tag.lower()
            prior_owner = owners.get(normalized_tag)
            if prior_owner is not None:
                duplicates.append((normalized_tag, prior_owner, concept_name))
            owners[normalized_tag] = concept_name

    assert duplicates == []


def test_concept_expansion_does_not_change_constraint_semantics():
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)

    document = mapper.map_xbrl_to_document(
        make_phase63_company_facts(),
        {
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "cik": "0000320193",
            "filing_type": "10-K",
            "filing_date": "2024-11-01",
        },
        max_periods=1,
    )

    response = verify_document(document, evidence_retriever=EvidenceRetriever())

    assert response.constraint_result is not None
    assert response.constraint_result.status == ConstraintStatus.CONSISTENT
    assert response.constraint_result.consistent is True
    assert response.constraint_result.coverage.loaded == 4
    assert response.constraint_result.coverage.verified == 1
    assert response.constraint_result.coverage.violated == 0
    assert response.constraint_result.coverage.indeterminate == 0
    assert response.constraint_result.coverage.derivable == 2
    assert response.constraint_result.coverage.not_applicable == 1
