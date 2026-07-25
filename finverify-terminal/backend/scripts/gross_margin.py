#!/usr/bin/env python3
"""
FinVerify Demo – Gross Margin

Usage:
    python -m scripts.gross_margin AAPL
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.financial import FinancialDocumentService, ReasoningEngine, TaskParser


def main(ticker: str):
    document_service = FinancialDocumentService(Path(__file__).parent.parent / "config" / "concepts.yaml")
    document = document_service.load_document(ticker)
    question = f"What is the gross margin for {ticker}'s filing?"
    task = TaskParser.parse(question)

    engine = ReasoningEngine(document_service.registry)
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
