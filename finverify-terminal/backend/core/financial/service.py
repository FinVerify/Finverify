"""Shared SEC-backed document loading for financial reasoning."""

from pathlib import Path

from ingestion.sec_edgar import (
    TICKER_TO_CIK,
    extract_latest_10k_info,
    fetch_company_facts,
    fetch_submissions,
)

from .concepts import ConceptRegistry
from .document import FinancialDocument
from .mapper import StatementMapper


class FinancialDocumentService:
    def __init__(self, config_path: str | Path | None = None):
        resolved_config = Path(config_path) if config_path is not None else Path(__file__).resolve().parents[2] / "config" / "concepts.yaml"
        self.registry = ConceptRegistry(resolved_config)
        self.mapper = StatementMapper(self.registry)
        self._cache: dict[str, FinancialDocument] = {}

    def load_document(self, ticker: str, *, max_periods: int = 2) -> FinancialDocument:
        normalized_ticker = ticker.upper()
        cached = self._cache.get(normalized_ticker)
        if cached is not None:
            return cached

        facts = fetch_company_facts(normalized_ticker)
        if not facts:
            raise RuntimeError(f"Could not fetch SEC CompanyFacts for {normalized_ticker}")

        submissions = fetch_submissions(normalized_ticker)
        filing = extract_latest_10k_info(submissions) if submissions else {}
        accession = (filing or {}).get("accession_number", "")
        cik = TICKER_TO_CIK.get(normalized_ticker, "")
        source_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession.replace('-', '')}/"
            if accession
            else f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        )

        metadata = {
            "company_name": facts.get("entityName", normalized_ticker),
            "ticker": normalized_ticker,
            "cik": cik,
            "filing_type": (filing or {}).get("form_type", "10-K"),
            "filing_date": (filing or {}).get("filing_date"),
            "source_url": source_url,
        }
        document = self.mapper.map_xbrl_to_document(facts, metadata, max_periods=max_periods)
        self._cache[normalized_ticker] = document
        return document
