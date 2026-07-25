"""Tests for financial reasoning integration through the shared /query flow."""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app import main as app_main
from core.financial.company import resolve_company
from core.financial.concepts import ConceptRegistry
from core.financial.mapper import StatementMapper
from core.financial.parser import TaskParser
from core.financial.reasoning import ReasoningEngine


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
    return {
        "cik": 789019,
        "entityName": "Microsoft Corporation",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-07-01", "2024-06-30", "2024-07-30", 2_000_000.0, "0000789019-24-000001", 2024),
                            _annual_entry("2022-07-01", "2023-06-30", "2023-07-27", 1_500_000.0, "0000789019-23-000001", 2023),
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-07-01", "2024-06-30", "2024-07-30", 500_000.0, "0000789019-24-000001", 2024),
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-07-01", "2024-06-30", "2024-07-30", 420_000.0, "0000789019-24-000001", 2024),
                        ]
                    }
                },
                "GrossProfit": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-07-01", "2024-06-30", "2024-07-30", 1_200_000.0, "0000789019-24-000001", 2024),
                        ]
                    }
                },
                "CostOfGoodsAndServicesSold": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-07-01", "2024-06-30", "2024-07-30", 800_000.0, "0000789019-24-000001", 2024),
                        ]
                    }
                },
            }
        },
    }


def make_document():
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)
    document = mapper.map_xbrl_to_document(
        make_company_facts(),
        {
            "company_name": "Microsoft Corporation",
            "ticker": "MSFT",
            "cik": "0000789019",
            "filing_type": "10-K",
            "filing_date": "2024-07-30",
            "source_url": "https://www.sec.gov/Archives/edgar/data/789019/000078901924000001/",
        },
        max_periods=2,
    )
    return registry, document


def test_resolve_company_supports_aliases_and_tickers():
    assert resolve_company("What was Microsoft's revenue?").ticker == "MSFT"
    assert resolve_company("What is AAPL's gross margin?").ticker == "AAPL"


def test_reasoning_engine_answers_direct_revenue_metric():
    registry, document = make_document()
    engine = ReasoningEngine(registry)

    result = engine.answer(TaskParser.parse("What was Microsoft's revenue?"), document)

    assert result["status"] == "complete"
    assert result["computed_value"] == pytest.approx(2_000_000.0)
    assert result["reported_value"] == pytest.approx(2_000_000.0)


def test_reasoning_engine_computes_operating_margin():
    registry, document = make_document()
    engine = ReasoningEngine(registry)

    result = engine.answer(TaskParser.parse("What is Microsoft's operating margin?"), document)

    assert result["status"] == "complete"
    assert result["computed_value"] == pytest.approx(0.25)


def test_reasoning_engine_computes_revenue_yoy_growth():
    registry, document = make_document()
    engine = ReasoningEngine(registry)

    result = engine.answer(TaskParser.parse("Compare revenue YoY for Microsoft"), document)

    assert result["status"] == "complete"
    assert result["computed_value"] == pytest.approx((2_000_000.0 - 1_500_000.0) / 1_500_000.0)


def test_query_endpoint_routes_financial_reasoning(monkeypatch):
    _registry, document = make_document()

    def _load_document(ticker: str, *, max_periods: int = 2):
        assert ticker == "MSFT"
        assert max_periods == 2
        return document

    monkeypatch.setattr(app_main.financial_document_service, "load_document", _load_document)
    client = TestClient(app_main.app)

    response = client.post("/query", json={"question": "What was Microsoft's revenue?"})

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "financial_reasoning"
    assert data["verified"] is True
    assert data["verified_number"] == pytest.approx(2_000_000.0)
    assert data["trust_score"] == "HIGH"
