"""Tests for scripts/verify_sec_filing.py.

These tests monkeypatch FinancialDocumentService.load_document with a
fixture document rather than hitting the real SEC EDGAR API, since network
access to data.sec.gov is not available in every environment (including this
sandbox). The rest of the pipeline (extract_claims -> verify_document ->
report building -> JSON export) runs for real, unmocked.
"""

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
from scripts import verify_sec_filing


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


def make_aapl_facts() -> dict:
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
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            _annual_entry("2023-10-01", "2024-09-30", "2024-11-01", 93_736_000_000.0, "0000320193-24-000123", 2024),
                        ]
                    }
                },
            }
        },
    }


def make_aapl_document():
    registry = ConceptRegistry(CONFIG_PATH)
    mapper = StatementMapper(registry)
    return mapper.map_xbrl_to_document(
        make_aapl_facts(),
        {
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "cik": "0000320193",
            "filing_type": "10-K",
            "filing_date": "2024-11-01",
            "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/",
        },
        max_periods=1,
    )


@pytest.fixture
def stub_load_document(monkeypatch):
    document = make_aapl_document()

    def _load_document(self, ticker, *, max_periods: int = 2):
        assert ticker == "AAPL"
        return document

    monkeypatch.setattr(FinancialDocumentService, "load_document", _load_document)
    return document


def test_run_prints_report_and_writes_json(stub_load_document, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(verify_sec_filing, "REPORTS_DIR", tmp_path)

    output_path = verify_sec_filing.run("AAPL")

    captured = capsys.readouterr()
    assert "FinVerify — SEC Filing Verification Report" in captured.out
    assert "Ticker:       AAPL" in captured.out
    assert "Company:      Apple Inc." in captured.out
    assert "Claims extracted: 3" in captured.out
    assert "Claims verified:  3" in captured.out
    assert "Claims skipped:   0" in captured.out

    assert output_path == tmp_path / "AAPL_2024-11-01.json"
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["ticker"] == "AAPL"
    assert payload["company_name"] == "Apple Inc."
    assert payload["filing_type"] == "10-K"
    assert payload["total_claims_extracted"] == 3
    assert payload["verified_claims_count"] == 3
    assert payload["skipped_claims"]["count"] == 0
    assert payload["consistent"] is True
    assert payload["violations"] == []
    assert len(payload["claims"]) == 3
    assert "generated_at" in payload
    assert isinstance(payload["trust_summary"], dict)

    # Regression: metric/entity must be plain strings, not repr()'d Metric/Entity objects.
    metric_names = {claim["metric"] for claim in payload["claims"]}
    assert metric_names == {"Revenue", "NetIncome", "CostOfGoodsSold"}
    assert all(claim["entity"] == "Apple Inc." for claim in payload["claims"])


def test_run_exits_on_load_document_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(verify_sec_filing, "REPORTS_DIR", tmp_path)

    def _load_document(self, ticker, *, max_periods: int = 2):
        raise RuntimeError(f"Could not fetch SEC CompanyFacts for {ticker}")

    monkeypatch.setattr(FinancialDocumentService, "load_document", _load_document)

    with pytest.raises(SystemExit) as exc_info:
        verify_sec_filing.run("BADTICKER")

    assert exc_info.value.code == 1
    assert not any(tmp_path.iterdir())


def test_run_exits_on_verify_document_failure(stub_load_document, monkeypatch, tmp_path):
    monkeypatch.setattr(verify_sec_filing, "REPORTS_DIR", tmp_path)

    def _boom(_document, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(verify_sec_filing, "verify_document", _boom)

    with pytest.raises(SystemExit) as exc_info:
        verify_sec_filing.run("AAPL")

    assert exc_info.value.code == 1
    assert not any(tmp_path.iterdir())


def test_build_report_reports_skipped_claims(stub_load_document, monkeypatch):
    document = stub_load_document
    # Simulate a mix where verify_document dropped one claim (no raw_value).
    from core.financial.document_verifier import verify_document

    response = verify_document(document)
    report = verify_sec_filing.build_report("AAPL", document, total_extracted=4, response=response)

    assert report["total_claims_extracted"] == 4
    assert report["verified_claims_count"] == len(response.results)
    assert report["skipped_claims"]["count"] == 4 - len(response.results)
    assert report["skipped_claims"]["reason"] is not None
