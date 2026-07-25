#!/usr/bin/env python3
"""
FinVerify Demo – Gross Margin

Usage:
    python -m scripts.gross_margin AAPL
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.financial.concepts import ConceptRegistry
from core.financial.mapper import StatementMapper
from core.financial.parser import TaskParser
from core.financial.reasoning import ReasoningEngine
from ingestion.sec_edgar import (
    TICKER_TO_CIK,
    extract_latest_10k_info,
    fetch_company_facts,
    fetch_submissions,
)


def load_sec_document(ticker: str):
    facts = fetch_company_facts(ticker)
    if not facts:
        raise RuntimeError(f"Could not fetch SEC CompanyFacts for {ticker}")

    submissions = fetch_submissions(ticker)
    filing = extract_latest_10k_info(submissions) if submissions else {}
    accession = (filing or {}).get("accession_number", "")
    cik = TICKER_TO_CIK.get(ticker.upper(), "")
    source_url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession.replace('-', '')}/"
        if accession
        else f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    )

    metadata = {
        "company_name": facts.get("entityName", ticker.upper()),
        "ticker": ticker.upper(),
        "cik": cik,
        "filing_type": (filing or {}).get("form_type", "10-K"),
        "filing_date": (filing or {}).get("filing_date"),
        "source_url": source_url,
    }

    registry = ConceptRegistry(Path(__file__).parent.parent / "config" / "concepts.yaml")
    mapper = StatementMapper(registry)
    return registry, mapper.map_xbrl_to_document(facts, metadata)


def main(ticker: str):
    registry, document = load_sec_document(ticker)
    question = f"What is the gross margin for {ticker}'s filing?"
    task = TaskParser.parse(question)

    engine = ReasoningEngine(registry)
    result = engine.answer(task, document)

    print("=" * 50)
    print("FinVerify – Gross Margin")
    print("=" * 50)
    print(f"Question: {question}")
    print(f"Company: {document.company_name}")
    print(f"Filing: {document.filing_type} filed {document.filing_date.isoformat()}")
    if result["status"] == "incomplete":
        print("Cannot compute: missing evidence")
        print(f"Missing: {result['missing']}")
    else:
        print(f"Computed Gross Margin: {result['computed_value']:.2%}")
        print(f"Formula: {result['formula']}")
        print(f"Trust: {result['trust'].label}")
        print(f"Explanation: {result['explanation']}")
        print("Evidence:")
        for item in result["evidence_contract"].provided:
            print(f"  - {item.concept}: {item.value} ({item.statement}; {item.source_ref})")
        print("Citations:")
        for citation in result["citations"]:
            print(
                "  - "
                f"{citation['concept']}={citation['value']} "
                f"[{citation['statement']}, {citation['xbrl_tag']}, {citation['source_ref']}]"
            )
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.gross_margin AAPL")
        sys.exit(1)
    main(sys.argv[1])
