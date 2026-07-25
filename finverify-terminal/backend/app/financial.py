"""Financial reasoning query handling for the shared /query endpoint."""

import logging

from fastapi import HTTPException

from app.models import QueryResponse
from app.parser import format_number_display
from core.financial import FinancialDocumentService, ReasoningEngine, TaskParser, resolve_company

logger = logging.getLogger(__name__)


def handle_financial_reasoning(question: str, document_service: FinancialDocumentService) -> QueryResponse:
    company = resolve_company(question)
    if company is None:
        raise HTTPException(
            status_code=400,
            detail="Financial reasoning requires a supported company or ticker in the question.",
        )

    task = TaskParser.parse(question)
    if task.metric is None:
        raise HTTPException(
            status_code=422,
            detail="The financial reasoning engine could not determine which supported metric to answer.",
        )

    try:
        document = document_service.load_document(company.ticker)
    except Exception as exc:
        logger.exception(
            "Financial reasoning document load failed for question='%s' ticker='%s'",
            question[:120],
            company.ticker,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Unable to load SEC filing data for {company.ticker}: {exc}",
        ) from exc

    try:
        engine = ReasoningEngine(document_service.registry)
        result = engine.answer(task, document)
    except Exception as exc:
        logger.exception(
            "Financial reasoning execution failed for question='%s' ticker='%s' metric='%s'",
            question[:120],
            company.ticker,
            task.metric,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Financial reasoning execution failed for {company.ticker}.",
        ) from exc

    if result["status"] != "complete" or result["computed_value"] is None or result["trust"] is None:
        missing = ", ".join(result.get("missing", []))
        detail = result["explanation"]
        if missing:
            detail = f"{detail} Missing evidence: {missing}."
        raise HTTPException(
            status_code=422,
            detail=detail,
        )

    citations = result.get("citations", [])
    citation_text = "; ".join(
        f"{citation['concept']} [{citation['source_ref']}]"
        for citation in citations[:3]
    )
    raw_number = result.get("reported_value")
    computed_value = result["computed_value"]
    explanation = result["explanation"]
    if citation_text:
        explanation = f"{explanation} Sources: {citation_text}."

    return QueryResponse(
        question=question,
        raw_text=explanation,
        raw_number=raw_number if raw_number is not None else computed_value,
        verified_number=computed_value,
        correction_log=[],
        trust_score=result["trust"].label,
        trust_color=result["trust"].color,
        display_value=format_number_display(computed_value, question),
        mode="financial_reasoning",
        verified=True,
    )


build_financial_query_response = handle_financial_reasoning
