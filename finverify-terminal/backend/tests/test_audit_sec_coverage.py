"""Tests for scripts/audit_sec_coverage.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from core.financial.concepts import ConceptRegistry
from core.financial.mapper import StatementMapper
from core.financial.service import FinancialDocumentService
from scripts import audit_sec_coverage


CONFIG_PATH = BACKEND_ROOT / "config" / "concepts.yaml"


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


def make_test_facts() -> dict:
    return {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {
            "dei": {
                "EntityCommonStockSharesOutstanding": {
                    "units": {"shares": [{"val": 1}]}
                }
            },
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 391_035_000_000.0, "0000320193-24-000123", 2024),
                            _annual_entry("2022-10-01", "2023-09-30", "2024-11-01", 383_285_000_000.0, "0000320193-24-000123", 2023),
                        ]
                    }
                },
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-12-15", 391_035_000_000.0, "0000320193-24-000456", 2024),
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
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 93_736_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
                "Assets": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 364_980_000_000.0, "0000320193-24-000123", 2024),
                            _annual_entry("2023-10-01", "2024-09-30", "2024-12-15", 364_980_000_000.0, "0000320193-24-000456", 2024),
                            _annual_entry("2022-10-01", "2023-09-30", "2024-11-01", 352_583_000_000.0, "0000320193-24-000123", 2023),
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
            },
        },
    }


def make_test_document():
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)
    return mapper.map_xbrl_to_document(
        make_test_facts(),
        {
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "cik": "0000320193",
            "filing_type": "10-K",
            "filing_date": "2024-11-01",
            "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/",
        },
        max_periods=2,
    )


@pytest.fixture
def stub_sec_boundaries(monkeypatch):
    facts = make_test_facts()
    document = make_test_document()

    monkeypatch.setattr(audit_sec_coverage, "fetch_company_facts", lambda ticker: facts)

    def _load_document(self, ticker, *, max_periods: int = 2):
        assert ticker == "AAPL"
        return document

    monkeypatch.setattr(FinancialDocumentService, "load_document", _load_document)
    return facts, document


def test_audit_ticker_reports_coverage_funnel(stub_sec_boundaries):
    result = audit_sec_coverage.audit_ticker("AAPL")

    assert result["ticker"] == "AAPL"
    assert result["raw_xbrl"] == {
        "total_tags": 9,
        "unique_tags": 6,
        "other_taxonomies": ["dei"],
    }

    resolution = result["concept_resolution"]
    assert resolution["resolved"] == 6
    assert resolution["unresolved"] == 0
    assert resolution["resolution_percent"] == 100.0
    assert resolution["top_unresolved_tags"] == []

    revenue_mapping = result["concept_mappings"]["Revenue"]
    assert revenue_mapping["found"] is True
    assert revenue_mapping["xbrl_tags"] == [
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:Revenues",
    ]
    assert revenue_mapping["selected_item_count"] == 3
    assert revenue_mapping["selected_xbrl_tags"] == [
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:Revenues",
    ]

    statement_items = result["statement_items"]
    assert statement_items["statements"]["IncomeStatement"] == 5
    assert statement_items["statements"]["BalanceSheet"] == 4
    assert statement_items["total"] == 9
    assert statement_items["duplicate_concept_periods"] == 2
    assert statement_items["duplicates_list"][0]["concept"] == "Assets"
    assert statement_items["duplicates_list"][0]["count"] == 2

    claims = result["claims"]
    assert claims["total"] == 9
    assert {item["metric"] for item in claims["items"]} == {
        "Assets",
        "CostOfGoodsSold",
        "Liabilities",
        "NetIncome",
        "Revenue",
    }

    constraints = result["constraints"]
    assert constraints["equations_loaded"] == 4
    assert constraints["equations_target_present"] == 1
    assert constraints["equations_indeterminate"] == 1
    assert constraints["equations_evaluated"].startswith("NOT OBSERVABLE")

    constraint_result = result["constraint_result"]
    assert constraint_result["consistent"] is None
    assert constraint_result["violations_count"] == 0
    assert constraint_result["indeterminate_count"] == 1
    assert constraint_result["indeterminate"] == ["Assets"]

    trust = result["trust"]
    assert trust["HIGH"] == 0
    assert trust["MEDIUM"] == 0
    assert trust["LOW"] == 9
    assert trust["evidence_tier"] == "NOT OBSERVABLE"
    assert trust["provider"] == "NOT OBSERVABLE"

    duplicate_analysis = result["duplicate_analysis"]
    assert duplicate_analysis["possible_multi_filing_duplicates"] >= 2
    assert duplicate_analysis["findings"][0]["concept"] == "Assets"
    assert "0000320193-24-000123" in duplicate_analysis["findings"][0]["accession_numbers"]
    assert "0000320193-24-000456" in duplicate_analysis["findings"][0]["accession_numbers"]

    rendered = audit_sec_coverage.render_text_report([result])
    assert "equations evaluated:          NOT OBSERVABLE" in rendered
    assert "provider:                     NOT OBSERVABLE" in rendered


def test_main_writes_json_output(tmp_path, monkeypatch, capsys):
    sample_results = [
        {
            "ticker": "AAPL",
            "timestamp": "2026-08-01T00:00:00+00:00",
            "raw_xbrl": {"total_tags": 1, "unique_tags": 1, "other_taxonomies": []},
            "concept_resolution": {
                "resolved": 1,
                "unresolved": 0,
                "resolution_percent": 100.0,
                "top_unresolved_tags": [],
            },
            "concept_mappings": {concept: {"xbrl_tags": [], "found": False, "selected_xbrl_tags": [], "selected_item_count": 0} for concept in audit_sec_coverage.AUDITABLE_CONCEPTS},
            "statement_items": {"statements": {}, "total": 0, "duplicate_concept_periods": 0, "duplicates_list": []},
            "claims": {"total": 0, "items": []},
            "constraints": {
                "equations_loaded": 0,
                "equations_target_present": 0,
                "equations_indeterminate": 0,
                "equations_violated": 0,
                "equations_evaluated": audit_sec_coverage.NOT_OBSERVABLE_EQUATIONS,
            },
            "constraint_result": {
                "consistent": None,
                "violations_count": 0,
                "indeterminate_count": 0,
                "violations": [],
                "indeterminate": [],
                "indeterminate_reasons": {},
            },
            "trust": {
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
                "evidence_tier": "NOT OBSERVABLE",
                "provider": "NOT OBSERVABLE",
            },
            "duplicate_analysis": {"possible_multi_filing_duplicates": 0, "findings": []},
        },
        {
            "ticker": "MSFT",
            "timestamp": "2026-08-01T00:00:01+00:00",
            "error": "boom",
        },
    ]

    monkeypatch.setattr(audit_sec_coverage, "audit_tickers", lambda tickers: sample_results)
    output_path = tmp_path / "coverage.json"

    exit_code = audit_sec_coverage.main(["AAPL", "MSFT", "--json", "--output", str(output_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    payload = json.loads(captured.out)
    assert [result["ticker"] for result in payload["results"]] == ["AAPL", "MSFT"]
    assert output_path.exists()

    written_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert written_payload == payload
